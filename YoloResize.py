# TODO fix the position of the crop box

import toml
import vapoursynth as vs

core = vs.get_core()
config_path = "config.toml"
config = toml.load(config_path)
SOURCE_FILE = config["source_file"]
CROP_BOX_DIMENSIONS = config["crop"]["crop_box_dimension"]
HEIGHT_CROP_BOX = config["crop"]["crop_box_height"]
SS_FACTOR = config["upscale"]["supersampling_factor"]
UPSCALE_MODE = config["upscale"]["upscale_mode"]
if UPSCALE_MODE == "znedi3":
    import edi_rpow2 as edi


def supersampling(clip, factor, factor_bis):
    if factor != 1:
        if UPSCALE_MODE in ("znedi3", "waifu2x"):
            if UPSCALE_MODE == "znedi3":
                clip = edi.znedi3_rpow2(clip=clip, rfactor=factor)
            else:
                clip = core.fmtc.bitdepth(clip=clip, bits=32)
                clip = core.w2xc.Waifu2x(clip=clip, scale=factor)
            if factor_bis != 1:
                clip = core.fmtc.resample(
                    clip=clip, scale=factor_bis, kernel="sinc", taps=2
                )
        else:
            clip = core.fmtc.resample(clip=clip, scale=factor, kernel="sinc", taps=2)
    clip = core.fmtc.resample(clip=clip, css="444")
    clip = core.fmtc.bitdepth(clip=clip, bits=8)
    return clip


def main():
    source_clip = core.ffms2.Source(source=SOURCE_FILE)
    crop_box = core.std.CropAbs(
        clip=source_clip,
        width=CROP_BOX_DIMENSIONS[0],
        height=CROP_BOX_DIMENSIONS[1],
        left=int((source_clip.width - CROP_BOX_DIMENSIONS[0]) / 2),
        top=source_clip.height - HEIGHT_CROP_BOX - CROP_BOX_DIMENSIONS[1],
    )
    clip_gray = core.std.Lut(clip=source_clip, planes=[1, 2], function=lambda x: 128)

    if SS_FACTOR < 0:
        if source_clip.width / source_clip.height > 16 / 9:
            target_res = 1920
            current_res = source_clip.width
        else:
            target_res = 1080
            current_res = source_clip.height
        if UPSCALE_MODE == "znedi3":
            ss = target_res / current_res / 1.125
        else:
            ss = target_res / current_res
    elif SS_FACTOR == 0:
        ss = 1
    else:
        ss = SS_FACTOR

    if UPSCALE_MODE == "znedi3" and ss != 1:
        if ss - int(ss) > 0:
            ss = int(ss / 2) * 2 + 2
        else:
            ss = int(ss / 2) * 2
        if SS_FACTOR < 0:
            ssbis = target_res / (current_res * ss)
        else:
            ssbis = SS_FACTOR / ss

    crop_box = supersampling(crop_box, ss, ssbis)
    clip_gray = supersampling(clip_gray, ss, ssbis)

    clip_left = core.std.Crop(
        clip=clip_gray, right=int((crop_box.width + clip_gray.width) / 2)
    )
    clip_right = core.std.Crop(clip=clip_gray, left=clip_left.width + crop_box.width)
    clip = core.std.CropAbs(
        clip=clip_gray,
        width=crop_box.width,
        height=clip_gray.height,
        left=int((clip_gray.width - crop_box.width) / 2),
    )
    clip_top = core.std.Crop(
        clip=clip, bottom=int((HEIGHT_CROP_BOX - 25) * ss) + crop_box.height
    )
    clip_bottom = core.std.Crop(clip=clip, top=clip_top.height + crop_box.height)

    edge = int(5 * ss)
    crop = core.std.Crop(clip=crop_box, left=edge, right=edge, top=edge, bottom=edge)
    rect = core.std.AddBorders(
        clip=crop, left=edge, right=edge, top=edge, bottom=edge, color=[255, 128, 128]
    )
    clip = core.std.StackVertical([clip_top, rect, clip_bottom])
    clip = core.std.StackHorizontal([clip_left, clip, clip_right])
    clip.set_output()


if __name__ == "__vapoursynth__":
    main()
