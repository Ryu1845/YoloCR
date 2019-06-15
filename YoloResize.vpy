FichierSource=r'Vidéo_Source.mkv'
DimensionCropBox=[1344,150] # Taille en largeur et hauteur de la CropBox délimitant les sous-titres à OCR.
HauteurCropBox=46 # Hauteur de la CropBox délimitant les sous-titres à OCR.
Supersampling=1 # Facteur de supersampling (multiplication de la résolution de la vidéo). Mettre à -1 pour calculer le facteur automatiquement.
ModeU='sinc' # 'sinc' (2 taps, plus rapide), 'znedi3' (plus lent) ou 'waifu2x' (beaucoup plus lent), contrôle la méthode d'Upscale.


import vapoursynth as vs
if ModeU=='znedi3':
	import edi_rpow2 as edi
core=vs.get_core()

def Grayuv(x):
	return 128

ClipSource=core.ffms2.Source(source=FichierSource)
CropBox=core.std.CropAbs(clip=ClipSource,width=DimensionCropBox[0],height=DimensionCropBox[1],left=int((ClipSource.width-DimensionCropBox[0])/2),top=ClipSource.height-HauteurCropBox-DimensionCropBox[1])
ClipGray=core.std.Lut(clip=ClipSource,planes=[1,2],function=Grayuv)

if Supersampling<0:
	if ClipSource.width/ClipSource.height>16/9:	
		TargetRes=1920
		CurrentRes=ClipSource.width	
	else:
		TargetRes=1080
		CurrentRes=ClipSource.height
	if ModeU=='znedi3':
		Ss=TargetRes/CurrentRes/1.125	
	else:
		Ss=TargetRes/CurrentRes
elif Supersampling==0:
	Ss=1
else:
	Ss=Supersampling

if ModeU=='znedi3' and Ss!=1:
	if Ss-int(Ss)>0:
		Ss=int(Ss/2)*2+2
	else:
		Ss=int(Ss/2)*2
	if Supersampling<0:
		Ssbis=TargetRes/(CurrentRes*Ss)
	else:
		Ssbis=Supersampling/Ss

def SuperSampling(clip):
	if Ss!=1:
		if ModeU=='znedi3' or ModeU=='waifu2x':
			if ModeU=='znedi3':
				clip=edi.znedi3_rpow2(clip=clip,rfactor=Ss)
			else :
				clip=core.fmtc.bitdepth(clip=clip,bits=32)
				clip=core.w2xc.Waifu2x(clip=clip,scale=Ss)
			if Ssbis!=1:
				clip=core.fmtc.resample(clip=clip,scale=Ssbis,kernel="sinc",taps=2)
		else:
			clip=core.fmtc.resample(clip=clip,scale=Ss,kernel="sinc",taps=2)
	clip=core.fmtc.resample(clip=clip,css="444")
	clip=core.fmtc.bitdepth(clip=clip,bits=8)
	return clip

CropBox=SuperSampling(clip=CropBox)
ClipGray=SuperSampling(clip=ClipGray)

ClipLeft=core.std.Crop(clip=ClipGray,right=int((CropBox.width+ClipGray.width)/2))
ClipRight=core.std.Crop(clip=ClipGray,left=ClipLeft.width+CropBox.width)
Clip=core.std.CropAbs(clip=ClipGray,width=CropBox.width,height=ClipGray.height,left=int((ClipGray.width-CropBox.width)/2))
ClipTop=core.std.Crop(clip=Clip,bottom=int(HauteurCropBox*Ss)+CropBox.height)
ClipBottom=core.std.Crop(clip=Clip,top=ClipTop.height+CropBox.height)

Bord=int(10*Ss)
Crop=core.std.Crop(clip=CropBox,left=Bord,right=Bord,top=Bord,bottom=Bord)
Rect=core.std.AddBorders(clip=Crop,left=Bord,right=Bord,top=Bord,bottom=Bord,color=[255,128,128])
Clip=core.std.StackVertical([ClipTop,Rect,ClipBottom])
Clip=core.std.StackHorizontal([ClipLeft,Clip,ClipRight])
Clip.set_output()
