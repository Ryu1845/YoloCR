import toml
import vapoursynth as vs

core = vs.get_core()
config_path = "../config.toml"
config = toml.load(config_path)
SOURCE_FILE = config["source_file"]
CROP_BOX_DIMENSION = config["crop"]["crop_box_dimension"]
HEIGHT_CROP_BOX = config["crop"]["crop_box_height"]
SS_FACTOR = config["upscale"]["supersampling_factor"]
UPSCALE_MODE = config["upscale"]["upscale_mode"]
THRESHOLD_MODE = config["threshold"]["threshold_mode"]
THRESHOLD = config["threshold"]["threshold"]
if UPSCALE_MODE == "znedi3":
    import edi_rpow2 as edi


def resize(clip, factor, factor_bis):
    if UPSCALE_MODE == "znedi3":
        clip = edi.znedi3_rpow2(clip=clip, rfactor=factor)
    elif UPSCALE_MODE == "waifu2x":
        clip = core.fmtc.bitdepth(clip=clip, bits=32)
        clip = core.w2xc.Waifu2x(clip=clip, scale=factor)
        if factor_bis != 1:
            clip = core.fmtc.bitdepth(clip=clip, bits=16)
        else:
            clip = core.fmtc.bitdepth(clip=clip, bits=8)
    else:
        clip = core.fmtc.resample(clip=clip, scale=factor, kernel="sinc", taps=2)
        clip = core.fmtc.bitdepth(clip=clip, bits=8)
    if factor_bis != 1:
        clip = core.fmtc.resample(clip=clip, scale=factor_bis, kernel="sinc", taps=2)
        clip = core.fmtc.bitdepth(clip=clip, bits=8)
    return clip


def resample(clip):
    if THRESHOLD_MODE == "L":
        clip = core.std.ShufflePlanes(clips=clip, planes=0, colorfamily=vs.GRAY)
    elif THRESHOLD_MODE in ("R", "G", "B"):
        clip = core.fmtc.resample(clip=clip, css="444")
        clip = core.fmtc.matrix(clip=clip, mat="709", col_fam=vs.RGB)
        clip = core.fmtc.bitdepth(clip=clip, bits=8)
        if THRESHOLD_MODE == "R":
            clip = core.std.ShufflePlanes(clips=clip, planes=0, colorfamily=vs.GRAY)
        elif THRESHOLD_MODE == "G":
            clip = core.std.ShufflePlanes(clips=clip, planes=1, colorfamily=vs.GRAY)
        else:
            clip = core.std.ShufflePlanes(clips=clip, planes=2, colorfamily=vs.GRAY)

        def remove_matrix(_, f):
            fout = f.copy()
            del fout.props._Matrix
            return fout

        clip = core.std.ModifyFrame(clip=clip, clips=clip, selector=remove_matrix)
    if THRESHOLD >= 0:
        clip = core.std.Binarize(clip=clip, threshold=THRESHOLD)
    return clip


def main():
    clip = core.ffms2.Source(source=SOURCE_FILE)
    clip = core.std.CropAbs(
        clip=clip,
        width=CROP_BOX_DIMENSION[0],
        height=CROP_BOX_DIMENSION[1],
        left=int((clip.width - CROP_BOX_DIMENSION[0]) / 2),
        top=clip.height - HEIGHT_CROP_BOX - CROP_BOX_DIMENSION[1],
    )

    if SS_FACTOR < 0:
        if clip.width / clip.height > 16 / 9:
            target_res = 1920
            current_res = clip.width
        else:
            target_res = 1080
            current_res = clip.height
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

    if ss != 1:
        clip = resize(clip, ss, ssbis)
    elif clip.format.bits_per_sample != 8:
        clip = core.fmtc.bitdepth(clip=clip, bits=8)

    clip = resample(clip)

    crop = core.std.CropAbs(
        clip=clip, width=clip.width - 20, height=clip.height - 20, left=10, top=10
    )
    rect = core.std.AddBorders(
        clip=crop, left=10, right=10, top=10, bottom=10, color=255
    )
    rect.set_output()


if __name__ == "__vapoursynth__":
    main()
