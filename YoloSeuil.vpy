import toml
import vapoursynth as vs

core = vs.get_core()
config_path = 'config.toml'
config = toml.load(config_path)
source_file = config['source_file']
crop_box_dimension = config['crop']['crop_box_dimension']
crop_box_height = config['crop']['crop_box_height']
supersampling_factor = config['upscale']['supersampling_factor']
upscale_mode = config['upscale']['upscale_mode']
threshold_mode = config['threshold']['threshold_mode']
threshold = config['threshold']['threshold']
if upscale_mode == 'znedi3':
    import edi_rpow2 as edi

Clip = core.ffms2.Source(source=source_file)
Clip = core.std.CropAbs(
    clip=Clip,
    width=crop_box_dimension[0],
    height=crop_box_dimension[1],
    left=int((Clip.width-crop_box_dimension[0])/2),
    top=Clip.height-crop_box_height-crop_box_dimension[1]
    )

if threshold_mode == 'L':
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

if Ss != 1:
    if upscale_mode in ('znedi3', 'waifu2x'):
        if upscale_mode == 'znedi3':
            Clip = edi.znedi3_rpow2(clip=Clip, rfactor=Ss)
        else:
            Clip = core.fmtc.bitdepth(clip=Clip, bits=32)
            Clip = core.w2xc.Waifu2x(clip=Clip, scale=Ss)
            if Ssbis != 1:
                Clip = core.fmtc.bitdepth(clip=Clip, bits=16)
            else:
                Clip = core.fmtc.bitdepth(clip=Clip, bits=8)
        if Ssbis != 1:
            Clip = core.fmtc.resample(
                clip=Clip, scale=Ssbis, kernel="sinc", taps=2)
            Clip = core.fmtc.bitdepth(clip=Clip, bits=8)
    else:
        Clip = core.fmtc.resample(clip=Clip, scale=Ss, kernel="sinc", taps=2)
        Clip = core.fmtc.bitdepth(clip=Clip, bits=8)
elif Clip.format.bits_per_sample != 8:
    Clip = core.fmtc.bitdepth(clip=Clip, bits=8)

if threshold_mode in ('R', 'G', 'B'):
    Clip = core.fmtc.resample(clip=Clip, css="444")
    Clip = core.fmtc.matrix(clip=Clip, mat="709", col_fam=vs.RGB)
    Clip = core.fmtc.bitdepth(clip=Clip, bits=8)
    if threshold_mode == 'R':
        Clip = core.std.ShufflePlanes(
            clips=Clip, planes=0, colorfamily=vs.GRAY)
    elif threshold_mode == 'G':
        Clip = core.std.ShufflePlanes(
            clips=Clip, planes=1, colorfamily=vs.GRAY)
    else:
        Clip = core.std.ShufflePlanes(
            clips=Clip, planes=2, colorfamily=vs.GRAY)

    def remove_matrix(n, f):
        fout = f.copy()
        del fout.props._Matrix
        return fout
    Clip = core.std.ModifyFrame(clip=Clip, clips=Clip, selector=remove_matrix)

if threshold >= 0:
    Clip = core.std.Binarize(clip=Clip, threshold=threshold)
crop = core.std.CropAbs(clip=Clip, width=Clip.width-20,
                        height=Clip.height-20, left=10, top=10)
rect = core.std.AddBorders(
    clip=crop, left=10, right=10, top=10, bottom=10, color=255)
rect.set_output()
