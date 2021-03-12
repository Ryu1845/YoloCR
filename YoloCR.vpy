import functools
import os

import havsfunc as haf
import toml
import vapoursynth as vs

core = vs.get_core()
config_path = 'config.toml'
config = toml.load(config_path)
source_file = config['source_file']
crop_box_dimension = config['crop']['crop_box_dimension']
crop_box_height = config['crop']['crop_box_height']
crop_box_height_alt = config['crop']['crop_box_height_alt']
supersampling_factor = config['upscale']['supersampling_factor']
expand_ratio = config['upscale']['expand_ratio']
upscale_mode = config['upscale']['upscale_mode']
inline_threshold = config['threshold']['inline_threshold']
outline_threshold = config['threshold']['outline_threshold']
SCD_threshold = config['threshold']['SCD_threshold']
if upscale_mode == 'znedi3':
    import edi_rpow2 as edi


def resizing(clip, width, height, height2):
    clip = core.std.CropAbs(clip=clip, width=width, height=height, left=int(
        (clip.width-width)/2), top=clip.height-height2)
    if Ss != 1:
        if upscale_mode in ('znedi3', 'waifu2x'):
            if upscale_mode == 'znedi3':
                clip = edi.znedi3_rpow2(clip=clip, rfactor=Ss)
            else:
                clip = core.fmtc.bitdepth(clip=clip, bits=32)
                clip = core.w2xc.Waifu2x(clip=clip, scale=Ss)
                if Ssbis != 1:
                    clip = core.fmtc.bitdepth(clip=clip, bits=16)
                else:
                    clip = core.fmtc.bitdepth(clip=clip, bits=8)
            if Ssbis != 1:
                clip = core.fmtc.resample(
                    clip=clip, scale=Ssbis, kernel="sinc", taps=2)
                clip = core.fmtc.bitdepth(clip=clip, bits=8)
        else:
            clip = core.fmtc.resample(
                clip=clip, scale=Ss, kernel="sinc", taps=2)
            clip = core.fmtc.bitdepth(clip=clip, bits=8)
    elif clip.format.bits_per_sample != 8:
        clip = core.fmtc.bitdepth(clip=clip, bits=8)
    return clip


def binarize_RGB(clip, threshold):
    R = core.std.ShufflePlanes(clips=clip, planes=0, colorfamily=vs.GRAY)
    G = core.std.ShufflePlanes(clips=clip, planes=1, colorfamily=vs.GRAY)
    B = core.std.ShufflePlanes(clips=clip, planes=2, colorfamily=vs.GRAY)
    for i in range(0, int(len(threshold)/3)):
        i = i*3
        expr = [f"x {str(threshold[i])} >= y {str(threshold[i+1])} >= or z {str(threshold[i+2])} >= or 255 0 ?"]
        RGB = core.std.Expr(clips=[R, G, B], expr=expr)
        if i == 0:
            clipfin = RGB
        else:
            clipfin = core.std.Merge(clipfin, RGB)
    clipfin = core.std.Binarize(clip=clipfin, threshold=1)
    return clipfin


def cleaning(clip, e):
    if isinstance(inline_threshold, list) or isinstance(outline_threshold, list):
        clip_RGB = core.fmtc.resample(clip=clip, css="444")
        clip_RGB = core.fmtc.matrix(clip=clip_RGB, mat="709", col_fam=vs.RGB)
        clip_RGB = core.fmtc.bitdepth(clip=clip_RGB, bits=8)

    if isinstance(inline_threshold, int) and isinstance(outline_threshold, int):
        white_raw = core.std.Binarize(clip=clip, threshold=inline_threshold)
        bright_raw = core.std.Binarize(clip=clip, threshold=outline_threshold)
    elif isinstance(inline_threshold, int) and isinstance(outline_threshold, list):
        white_raw = core.std.ShufflePlanes(
            clips=clip, planes=0, colorfamily=vs.GRAY)
        white_raw = core.std.Binarize(
            clip=white_raw,
            threshold=inline_threshold
            )
        bright_raw = binarize_RGB(clip_RGB, outline_threshold)
    elif isinstance(inline_threshold, list) and isinstance(outline_threshold, int):
        white_raw = binarize_RGB(clip_RGB, inline_threshold)
        bright_raw = core.std.ShufflePlanes(
            clips=clip, planes=0, colorfamily=vs.GRAY)
        bright_raw = core.std.Binarize(
            clip=bright_raw,
            threshold=outline_threshold
            )
    else:
        white_raw = binarize_RGB(clip_RGB, inline_threshold)
        bright_raw = binarize_RGB(clip_RGB, outline_threshold)

    bright_out = core.std.Lut2(
        clipa=bright_raw,
        clipb=rect,
        function=min
        )

    bright_not = core.misc.Hysteresis(clipa=bright_out, clipb=bright_raw)
    bright_not = core.std.Invert(bright_not)

    white_txt = core.std.MaskedMerge(blank, white_raw, bright_not)

    white_lb = haf.mt_inpand_multi(
        src=white_txt, sw=int(e), sh=int(e), mode="ellipse")
    white_lb = haf.mt_expand_multi(
        src=white_lb, sw=int(e), sh=int(e), mode="ellipse")

    white_ub = haf.mt_inpand_multi(
        src=white_txt, sw=int(5*e), sh=int(5*e), mode="ellipse")
    white_ub = haf.mt_expand_multi(
        src=white_ub, sw=int(3*e), sh=int(3*e), mode="ellipse")
    white_ub = core.std.Invert(white_ub)

    white = core.std.MaskedMerge(blank, white_lb, white_ub)
    white = core.misc.Hysteresis(clipa=white, clipb=white_txt)

    clip_cleaning = core.std.MaskedMerge(blank, white_raw, white)
    clip_cleaning = core.std.Median(clip=clip_cleaning)

    return clip_cleaning


def scene_log(n, f, clip, log):
    if f.props._SceneChangeNext == 1 or f.props._SceneChangePrev == 1:
        open(log, "a").write(str(n)+" "+str(f.props._SceneChangePrev) +
                             " "+str(f.props._SceneChangeNext)+"\n")
    return clip


Clip = core.ffms2.Source(source=source_file)
if isinstance(inline_threshold, int) and isinstance(outline_threshold, int):
    Clip = core.std.ShufflePlanes(clips=Clip, planes=0, colorfamily=vs.GRAY)

if supersampling_factor < 0:
    if Clip.width/Clip.height > 16/9:
        target_res = 1920
        current_res = Clip.width
    else:
        target_res = 1080
        current_res = Clip.height
    if upscale_mode == 'znedi3':
        Ss = target_res/current_res/1.125
    else:
        Ss = target_res/current_res
elif supersampling_factor == 0:
    Ss = 1
else:
    Ss = supersampling_factor

if upscale_mode == 'znedi3' and Ss != 1:
    if Ss-int(Ss) > 0:
        Ss = int(Ss/2)*2+2
    else:
        Ss = int(Ss/2)*2
    if supersampling_factor < 0:
        Ssbis = target_res/(current_res*Ss)
    else:
        Ssbis = supersampling_factor/Ss

crop_box_height = crop_box_height+crop_box_dimension[1]
if crop_box_height_alt >= 0:
    crop_box_height_alt = crop_box_height_alt+crop_box_dimension[1]

clip_resized = resizing(
    Clip, crop_box_dimension[0], crop_box_dimension[1], crop_box_height)

black_clip = core.std.BlankClip(
    width=int(
        clip_resized.width-20), height=int(
            clip_resized.height-20
            ),
    format=vs.GRAY8,
    color=0
    )
rect = core.std.AddBorders(clip=black_clip, left=10,
                           right=10, top=10, bottom=10, color=255)
blank = core.std.BlankClip(clip_resized, format=vs.GRAY8)

clip_cleaned = cleaning(clip_resized, expand_ratio)

open("SceneChanges.log", "w").write("0 1 0\n")
clip_cleaned_sc = core.std.CropAbs(
    clip=clip_cleaned,
    width=int(clip_cleaned.width/2.7),
    height=int(clip_cleaned.height/2.7),
    left=int(clip_cleaned.width*(1-1/2.7)/2),
    top=int(clip_cleaned.height/2)
    )
clip_cleaned_sc = core.misc.SCDetect(
    clip=clip_cleaned_sc,
    threshold=SCD_threshold
    )
clip_cleaned = core.std.FrameEval(
    clip_cleaned,
    functools.partial(
        scene_log,
        clip=clip_cleaned,
        log="SceneChanges.log"
        ),
    prop_src=clip_cleaned_sc
    )

if crop_box_height_alt >= 0:
    clip_resized_alt = resizing(
        Clip,
        crop_box_dimension[0],
        crop_box_dimension[1],
        crop_box_height_alt
        )

    clip_cleaned_alt = cleaning(clip_resized_alt, expand_ratio)

    open("SceneChangesAlt.log", "w").write("0 1 0\n")
    clip_cleaned_alt_sc = core.std.CropAbs(
        clip=clip_cleaned_alt,
        width=int(clip_cleaned_alt.width/2.7),
        height=int(clip_cleaned_alt.height/2.7),
        left=int(clip_cleaned_alt.width*(1-1/2.7)/2),
        top=int(clip_cleaned_alt.height*(1/2-1/2.7))
        )
    clip_cleaned_alt_sc = core.misc.SCDetect(
        clip=clip_cleaned_alt_sc, threshold=SCD_threshold)
    clip_cleaned_alt = core.std.FrameEval(
        clip_cleaned_alt,
        functools.partial(
            scene_log,
            clip=clip_cleaned_alt,
            log="SceneChangesAlt.log"
            ),
        prop_src=clip_cleaned_alt_sc
        )

    Clip = core.std.StackVertical([clip_cleaned_alt, clip_cleaned])

else:
    if os.path.exists("SceneChangesAlt.log"):
        os.remove("SceneChangesAlt.log")
    Clip = clip_cleaned

Clip.set_output()
