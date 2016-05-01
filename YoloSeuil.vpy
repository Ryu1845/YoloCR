FichierSource='Vidéo_Source.mkv'
DimensionCropBox=[1344,150] # Taille en largeur et hauteur de la CropBox délimitant les sous-titres à OCR.
HauteurCropBox=46 # Hauteur de la CropBox délimitant les sous-titres à OCR.
Supersampling=-1 # Facteur de supersampling (multiplication de la résolution de la vidéo). Mettre à -1 pour calculer le facteur automatiquement.
ModeU='sinc' # 'sinc' (2 taps, plus rapide), 'nnedi3' (plus lent) ou 'waifu2x' (beaucoup plus lent), contrôle la méthode d'Upscale.
ModeS='L' # 'L' pour Luma, 'R' pour Rouge, 'B' pour Bleu ou 'G' pour Vert. Seuil à analyser.
Seuil=-1 # Seuil délimitant les sous-titres. Mettre à -1 pour chercher le seuil à l'aide de VapourSynth Editor.


import vapoursynth as vs
if ModeU=='nnedi3':
	import edi_rpow2 as edi
core=vs.get_core()

Clip=core.ffms2.Source(source=FichierSource)
Clip=core.std.CropAbs(clip=Clip,width=DimensionCropBox[0],height=DimensionCropBox[1],left=int((Clip.width-DimensionCropBox[0])/2),top=Clip.height-HauteurCropBox-DimensionCropBox[1])

if ModeS=='L':
	Clip=core.std.ShufflePlanes(clips=Clip,planes=0,colorfamily=vs.GRAY)

if Supersampling<0:
	if Clip.width/Clip.height>16/9:	
		TargetRes=1920
		CurrentRes=Clip.width	
	else:
		TargetRes=1080
		CurrentRes=Clip.height
	if ModeU=='nnedi3':
		Ss=TargetRes/CurrentRes/1.125	
	else:
		Ss=TargetRes/CurrentRes
elif Supersampling==0:
	Ss=1
else:
	Ss=Supersampling

if ModeU=='nnedi3' and Ss!=1:
	if Ss-int(Ss)>0:
		Ss=int(Ss/2)*2+2
	else:
		Ss=int(Ss/2)*2
	if Supersampling<0:
		Ssbis=TargetRes/(CurrentRes*Ss)
	else:
		Ssbis=Supersampling/Ss

if Ss!=1:
	if ModeU=='nnedi3' or ModeU=='waifu2x':
		if ModeU=='nnedi3':
			Clip=edi.nnedi3_rpow2(clip=Clip,rfactor=Ss)
		else :
			Clip=core.fmtc.bitdepth(clip=Clip,bits=32)
			Clip=core.w2xc.Waifu2x(clip=Clip,scale=Ss)
			if Ssbis!=1:
				Clip=core.fmtc.bitdepth(clip=Clip,bits=16)
			else :
				Clip=core.fmtc.bitdepth(clip=Clip,bits=8)
		if Ssbis!=1:
			Clip=core.fmtc.resample(clip=Clip,scale=Ssbis,kernel="sinc",taps=2)
			Clip=core.fmtc.bitdepth(clip=Clip,bits=8)
	else:
		Clip=core.fmtc.resample(clip=Clip,scale=Ss,kernel="sinc",taps=2)
		Clip=core.fmtc.bitdepth(clip=Clip,bits=8)
elif Clip.format.bits_per_sample!=8:
	Clip=core.fmtc.bitdepth(clip=Clip,bits=8)

if ModeS=='R' or ModeS=='G' or ModeS=='B':
	Clip=core.fmtc.resample(clip=Clip,css="444")
	Clip=core.fmtc.matrix(clip=Clip,mat="709",col_fam=vs.RGB)
	Clip=core.fmtc.bitdepth(clip=Clip,bits=8)
	if ModeS=='R':
		Clip=core.std.ShufflePlanes(clips=Clip,planes=0,colorfamily=vs.GRAY)
	elif ModeS=='G':
		Clip=core.std.ShufflePlanes(clips=Clip,planes=1,colorfamily=vs.GRAY)
	else:
		Clip=core.std.ShufflePlanes(clips=Clip,planes=2,colorfamily=vs.GRAY)

if Seuil>=0:	
	Clip=core.std.Binarize(clip=Clip,threshold=Seuil)	
Crop=core.std.CropAbs(clip=Clip,width=Clip.width-20,height=Clip.height-20,left=10,top=10)
Rect=core.std.AddBorders(clip=Crop,left=10,right=10,top=10,bottom=10,color=255)
Rect.set_output()
