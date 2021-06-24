"""Output white on black video of the subtitles."""
import functools
import os

import havsfunc as haf
import toml
import vapoursynth as vs
import edi_rpow2 as edi

core = vs.get_core()
config_path = "config.toml"
config = toml.load(config_path)


class YoloCR:
    def __init__(self, config):
        self.source_file = config["source_file"]
        self.crop_box_dimensions = config["crop"]["crop_box_dimension"]
        self.height_crop_box = config["crop"]["crop_box_height"]
        self.height_crop_box_alt = config["crop"]["crop_box_height_alt"]
        self.ss_factor = config["upscale"]["supersampling_factor"]
        self.expand_ratio = config["upscale"]["expand_ratio"]
        self.upscale_mode = config["upscale"]["upscale_mode"]
        self.inline_threshold = config["threshold"]["inline_threshold"]
        self.outline_threshold = config["threshold"]["outline_threshold"]
        self.scd_threshold = config["threshold"]["SCD_threshold"]

    def resizing(
        self,
        clip: vs.VideoNode,
        crop_box_dimensions: list,
        height_crop_box: int,
        factor: int,
        factor_bis: int,
    ) -> vs.VideoNode:
        """
        Crop and supersample the crop box.

        Parameters
        ----------
        clip:
            The original video source
        crop_box_width:
            The crop box width
        crop_box_height:
            The crop box height
        factor:
            Supersampling factor
        factor_bis:
            Supersampling factor bis

        Returns
        -------
        vs.VideoNode
            The resized crop box
        """
        crop_box_height = crop_box_dimensions[1]
        crop_box_width = crop_box_dimensions[0]
        clip = core.std.CropAbs(
            clip=clip,
            width=crop_box_width,
            height=crop_box_height,
            left=int((clip.width - crop_box_width) / 2),
            top=clip.height - height_crop_box,
        )
        if factor != 1:
            if self.upscale_mode in ("znedi3", "waifu2x"):
                if self.upscale_mode == "znedi3":
                    clip = edi.znedi3_rpow2(clip=clip, rfactor=factor)
                else:
                    clip = core.fmtc.bitdepth(clip=clip, bits=32)
                    clip = core.w2xc.Waifu2x(clip=clip, scale=factor)
                    if factor_bis != 1:
                        clip = core.fmtc.bitdepth(clip=clip, bits=16)
                    else:
                        clip = core.fmtc.bitdepth(clip=clip, bits=8)
                if factor_bis != 1:
                    clip = core.fmtc.resample(
                        clip=clip, scale=factor_bis, kernel="sinc", taps=2
                    )
                    clip = core.fmtc.bitdepth(clip=clip, bits=8)
            else:
                clip = core.fmtc.resample(
                    clip=clip, scale=factor, kernel="sinc", taps=2
                )
                clip = core.fmtc.bitdepth(clip=clip, bits=8)
        elif clip.format.bits_per_sample != 8:
            clip = core.fmtc.bitdepth(clip=clip, bits=8)
        return clip

    def binarize_RGB(self, clip: vs.VideoNode, threshold: list) -> vs.VideoNode:
        """
        I don't know what this does.

        Notes
        -----
        If you're reading this and know exactly what this does
        make an issue on github please.

        Parameters
        ----------
        clip:
            The input clip
        threshold:
            The threshold color in [R,G,B]

        Returns
        -------
        vs.VideoNode
            The binarized clip
        """
        R = core.std.ShufflePlanes(clips=clip, planes=0, colorfamily=vs.GRAY)
        G = core.std.ShufflePlanes(clips=clip, planes=1, colorfamily=vs.GRAY)
        B = core.std.ShufflePlanes(clips=clip, planes=2, colorfamily=vs.GRAY)
        for i in range(0, int(len(threshold) / 3)):
            i = i * 3
            expr = [
                f"x {threshold[i]} >= y {threshold[i+1]} >= or z {threshold[i+2]} >= or 255 0 ?"
            ]
            RGB = core.std.Expr(clips=[R, G, B], expr=expr)
            if i == 0:
                clipfin = RGB
            else:
                clipfin = core.std.Merge(clipfin, RGB)
        clipfin = core.std.Binarize(clip=clipfin, threshold=1)
        return clipfin

    def cleaning(self, clip: vs.VideoNode, e: int) -> vs.VideoNode:
        """
        Clean the clip for OCR.

        Parameters
        ----------
        clip:
            The input clip cropped for the subtitles
        e:
            The expand ratio

        Returns
        -------
        vs.VideoNode
            The cleaned clip
        """
        black_clip = core.std.BlankClip(
            width=int(clip.width - 20),
            height=int(clip.height - 20),
            format=vs.GRAY8,
            color=0,
        )
        rect = core.std.AddBorders(
            clip=black_clip, left=10, right=10, top=10, bottom=10, color=255
        )
        blank = core.std.BlankClip(clip, format=vs.GRAY8)

        if isinstance(self.inline_threshold, list) or isinstance(
            self.outline_threshold, list
        ):
            clip_RGB = core.fmtc.resample(clip=clip, css="444")
            clip_RGB = core.fmtc.matrix(clip=clip_RGB, mat="709", col_fam=vs.RGB)
            clip_RGB = core.fmtc.bitdepth(clip=clip_RGB, bits=8)

        if isinstance(self.inline_threshold, int) and isinstance(
            self.outline_threshold, int
        ):
            white_raw = core.std.Binarize(clip=clip, threshold=self.inline_threshold)
            bright_raw = core.std.Binarize(clip=clip, threshold=self.outline_threshold)
        elif isinstance(self.inline_threshold, int) and isinstance(
            self.outline_threshold, list
        ):
            white_raw = core.std.ShufflePlanes(
                clips=clip, planes=0, colorfamily=vs.GRAY
            )
            white_raw = core.std.Binarize(
                clip=white_raw, threshold=self.inline_threshold
            )
            bright_raw = self.binarize_RGB(clip_RGB, self.outline_threshold)
        elif isinstance(self.inline_threshold, list) and isinstance(
            self.outline_threshold, int
        ):
            white_raw = self.binarize_RGB(clip_RGB, self.inline_threshold)
            bright_raw = core.std.ShufflePlanes(
                clips=clip, planes=0, colorfamily=vs.GRAY
            )
            bright_raw = core.std.Binarize(
                clip=bright_raw, threshold=self.outline_threshold
            )
        else:
            white_raw = self.binarize_RGB(clip_RGB, self.inline_threshold)
            bright_raw = self.binarize_RGB(clip_RGB, self.outline_threshold)

        bright_out = core.std.Lut2(
            clipa=bright_raw, clipb=rect, function=lambda x, y: min(x, y)
        )

        bright_not = core.misc.Hysteresis(clipa=bright_out, clipb=bright_raw)
        bright_not = core.std.Invert(bright_not)

        white_txt = core.std.MaskedMerge(blank, white_raw, bright_not)

        white_lb = haf.mt_inpand_multi(
            src=white_txt, sw=int(e), sh=int(e), mode="ellipse"
        )
        white_lb = haf.mt_expand_multi(
            src=white_lb, sw=int(e), sh=int(e), mode="ellipse"
        )

        white_ub = haf.mt_inpand_multi(
            src=white_txt, sw=int(5 * e), sh=int(5 * e), mode="ellipse"
        )
        white_ub = haf.mt_expand_multi(
            src=white_ub, sw=int(3 * e), sh=int(3 * e), mode="ellipse"
        )
        white_ub = core.std.Invert(white_ub)

        white = core.std.MaskedMerge(blank, white_lb, white_ub)
        white = core.misc.Hysteresis(clipa=white, clipb=white_txt)

        clip_cleaning = core.std.MaskedMerge(blank, white_raw, white)
        clip_cleaning = core.std.Median(clip=clip_cleaning)

        return clip_cleaning

    def scene_log(
        self, n: int, f: vs.VideoFrame, clip: vs.VideoNode, log: str
    ) -> vs.VideoNode:
        """
        Log scene changes to a file.

        Notes
        -----
        The file is formatted as <frame_number> 0 1
        if it's the last frame in the scene,
        1 0 if it's the first one

        Parameters
        ----------
        n:
            The frame number
        f:
            The frame properties
        clip:
            The input clip
        log:
            The log file

        Returns
        -------
        vs.VideoNode
            The same clip as the input
        """
        if f.props["_SceneChangeNext"] == 1 or f.props["_SceneChangePrev"] == 1:
            with open(log, "a") as log_io:
                scene_change_prev = f.props["_SceneChangePrev"]
                scene_change_next = f.props["_SceneChangeNext"]
                log_io.write(f"{n} {scene_change_prev} {scene_change_next}\n")
        return clip

    def main(self):
        """Do the thing."""
        clip = core.ffms2.Source(source=self.source_file)
        if isinstance(self.inline_threshold, int) and isinstance(
            self.outline_threshold, int
        ):
            clip = core.std.ShufflePlanes(clips=clip, planes=0, colorfamily=vs.GRAY)

        if self.ss_factor < 0:
            if clip.width / clip.height > 16 / 9:
                target_res = 1920
                current_res = clip.width
            else:
                target_res = 1080
                current_res = clip.height
            ss = (
                target_res / current_res / 1.125
                if self.upscale_mode == "znedi3"
                else target_res / current_res
            )
        elif self.ss_factor == 0:
            ss = 1
        else:
            ss = self.ss_factor

        if self.upscale_mode == "znedi3" and ss != 1:
            if ss - int(ss) > 0:
                ss = int(ss / 2) * 2 + 2
            else:
                ss = int(ss / 2) * 2
            ssbis = (
                target_res / (current_res * ss)
                if self.ss_factor < 0
                else self.ss_factor / ss
            )

        crop_box_height = self.height_crop_box + self.crop_box_dimensions[1]
        height_crop_box_alt = (
            self.height_crop_box_alt + self.crop_box_dimensions[1]
            if self.height_crop_box_alt >= 0
            else -1
        )

        clip_resized = self.resizing(
            clip, self.crop_box_dimensions, crop_box_height, ss, ssbis
        )

        clip_cleaned = self.cleaning(clip_resized, self.expand_ratio)

        with open("scene_changes.log", "w") as log_io:
            log_io.write("0 1 0\n")
        clip_cleaned_sc = core.std.CropAbs(
            clip=clip_cleaned,
            width=int(clip_cleaned.width / 2.7),
            height=int(clip_cleaned.height / 2.7),
            left=int(clip_cleaned.width * (1 - 1 / 2.7) / 2),
            top=int(clip_cleaned.height / 2),
        )
        clip_cleaned_sc = core.misc.SCDetect(
            clip=clip_cleaned_sc, threshold=self.scd_threshold
        )
        clip_cleaned = core.std.FrameEval(
            clip_cleaned,
            functools.partial(
                self.scene_log, clip=clip_cleaned, log="scene_changes.log"
            ),
            prop_src=clip_cleaned_sc,
        )

        if height_crop_box_alt >= 0:
            clip_resized_alt = self.resizing(
                clip, self.crop_box_dimensions, height_crop_box_alt, ss, ssbis
            )

            clip_cleaned_alt = self.cleaning(clip_resized_alt, self.expand_ratio)

            with open("scene_changes_alt.log", "w") as alt_log_io:
                alt_log_io.write("0 1 0\n")
            clip_cleaned_alt_sc = core.std.CropAbs(
                clip=clip_cleaned_alt,
                width=int(clip_cleaned_alt.width / 2.7),
                height=int(clip_cleaned_alt.height / 2.7),
                left=int(clip_cleaned_alt.width * (1 - 1 / 2.7) / 2),
                top=int(clip_cleaned_alt.height * (1 / 2 - 1 / 2.7)),
            )
            clip_cleaned_alt_sc = core.misc.SCDetect(
                clip=clip_cleaned_alt_sc, threshold=self.scd_threshold
            )
            clip_cleaned_alt = core.std.FrameEval(
                clip_cleaned_alt,
                functools.partial(
                    self.scene_log, clip=clip_cleaned_alt, log="scene_changes_alt.log"
                ),
                prop_src=clip_cleaned_alt_sc,
            )

            clip = core.std.StackVertical([clip_cleaned_alt, clip_cleaned])

        else:
            if os.path.exists("scene_changes_alt.log"):
                os.remove("scene_changes_alt.log")
            clip = clip_cleaned

        clip.set_output()


if __name__ == "__vapoursynth__":
    yolocr = YoloCR(config)
    yolocr.main()
