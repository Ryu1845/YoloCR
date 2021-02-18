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
if upscale_mode == 'znedi3':
    import edi_rpow2 as edi


def supersampling(clip):
    if Ss != 1:
        if upscale_mode in ('znedi3', 'waifu2x'):
            if upscale_mode == 'znedi3':
                clip = edi.znedi3_rpow2(clip=clip, rfactor=Ss)
            else:
                clip = core.fmtc.bitdepth(clip=clip, bits=32)
                clip = core.w2xc.Waifu2x(clip=clip, scale=Ss)
            if Ssbis != 1:
                clip = core.fmtc.resample(
                    clip=clip, scale=Ssbis, kernel="sinc", taps=2)
        else:
            clip = core.fmtc.resample(
                clip=clip, scale=Ss, kernel="sinc", taps=2)
    clip = core.fmtc.resample(clip=clip, css="444")
    clip = core.fmtc.bitdepth(clip=clip, bits=8)
    return clip


source_clip = core.ffms2.Source(source=source_file)
crop_box = core.std.CropAbs(
    clip=source_clip,
    width=crop_box_dimension[0],
    height=crop_box_dimension[1],
    left=int((source_clip.width-crop_box_dimension[0])/2),
    top=source_clip.height-crop_box_height-crop_box_dimension[1]
    )
clip_gray = core.std.Lut(
    clip=source_clip,
    planes=[1, 2],
    function=lambda x: 128
    )

if supersampling_factor < 0:
    if source_clip.width/source_clip.height > 16/9:
        target_res = 1920
        current_res = source_clip.width
    else:
        target_res = 1080
        current_res = source_clip.height
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

crop_box = supersampling(clip=crop_box)
clip_gray = supersampling(clip=clip_gray)

clip_left = core.std.Crop(clip=clip_gray, right=int(
    (crop_box.width+clip_gray.width)/2))
clip_right = core.std.Crop(clip=clip_gray, left=clip_left.width+crop_box.width)
Clip = core.std.CropAbs(
    clip=clip_gray,
    width=crop_box.width,
    height=clip_gray.height,
    left=int((clip_gray.width-crop_box.width)/2)
    )
clip_top = core.std.Crop(
    clip=Clip,
    bottom=int(crop_box_height*Ss)+crop_box.height
    )
clip_bottom = core.std.Crop(clip=Clip, top=clip_top.height+crop_box.height)

edge = int(5*Ss)
Crop = core.std.Crop(clip=crop_box, left=edge,
                     right=edge, top=edge, bottom=edge)
rect = core.std.AddBorders(
    clip=Crop,
    left=edge,
    right=edge,
    top=edge,
    bottom=edge,
    color=[255, 128, 128]
    )
Clip = core.std.StackVertical([clip_top, rect, clip_bottom])
Clip = core.std.StackHorizontal([clip_left, Clip, clip_right])
Clip.set_output()
