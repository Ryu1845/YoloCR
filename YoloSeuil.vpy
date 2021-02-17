import toml
import vapoursynth as vs

core = vs.get_core()
config = toml.load('config.toml')
FichierSource = config['FichierSource']
DimensionCropBox = config['crop']['DimensionCropBox']
HauteurCropBox = config['crop']['HauteurCropBox']
Supersampling = config['upscale']['Supersampling']
ModeU = config['upscale']['ModeU']
ModeS = config['seuil']['ModeS']
Seuil = config['seuil']['Seuil']
if ModeU == 'znedi3':
    import edi_rpow2 as edi

Clip = core.ffms2.Source(source=FichierSource)
Clip = core.std.CropAbs(clip=Clip, width=DimensionCropBox[0], height=DimensionCropBox[1], left=int(
    (Clip.width-DimensionCropBox[0])/2), top=Clip.height-HauteurCropBox-DimensionCropBox[1])

if ModeS == 'L':
    Clip = core.std.ShufflePlanes(clips=Clip, planes=0, colorfamily=vs.GRAY)

if Supersampling < 0:
    if Clip.width/Clip.height > 16/9:
        TargetRes = 1920
        CurrentRes = Clip.width
    else:
        TargetRes = 1080
        CurrentRes = Clip.height
    if ModeU == 'znedi3':
        Ss = TargetRes/CurrentRes/1.125
    else:
        Ss = TargetRes/CurrentRes
elif Supersampling == 0:
    Ss = 1
else:
    Ss = Supersampling

if ModeU == 'znedi3' and Ss != 1:
    if Ss-int(Ss) > 0:
        Ss = int(Ss/2)*2+2
    else:
        Ss = int(Ss/2)*2
    if Supersampling < 0:
        Ssbis = TargetRes/(CurrentRes*Ss)
    else:
        Ssbis = Supersampling/Ss

if Ss != 1:
    if ModeU == 'znedi3' or ModeU == 'waifu2x':
        if ModeU == 'znedi3':
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

if ModeS == 'R' or ModeS == 'G' or ModeS == 'B':
    Clip = core.fmtc.resample(clip=Clip, css="444")
    Clip = core.fmtc.matrix(clip=Clip, mat="709", col_fam=vs.RGB)
    Clip = core.fmtc.bitdepth(clip=Clip, bits=8)
    if ModeS == 'R':
        Clip = core.std.ShufflePlanes(
            clips=Clip, planes=0, colorfamily=vs.GRAY)
    elif ModeS == 'G':
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

if Seuil >= 0:
    Clip = core.std.Binarize(clip=Clip, threshold=Seuil)
Crop = core.std.CropAbs(clip=Clip, width=Clip.width-20,
                        height=Clip.height-20, left=10, top=10)
Rect = core.std.AddBorders(
    clip=Crop, left=10, right=10, top=10, bottom=10, color=255)
Rect.set_output()
