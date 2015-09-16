FichierSource='Vidéo_Source.mkv'
DimensionCropBox=[1344,150] # Taille en largeur et hauteur de la CropBox délimitant les sous-titres à OCR.
HauteurCropBox=46 # Hauteur de la CropBox délimitant les sous-titres à OCR.
Supersampling=-1 # Facteur de supersampling (multiplication de la résolution de la vidéo). Mettre à -1 pour calculer le facteur automatiquement.
ModeU='sinc' # 'sinc' (2 taps, plus rapide) ou 'nnedi3' (plus lent), contrôle la méthode d'Upscale.
ModeS='L' # 'L' pour Luma, 'R' pour Rouge, 'B' pour Bleu ou 'G' pour Vert. Seuil à analyser.
Seuil=230 # Seuil délimitant les sous-titres.


import vapoursynth as vs
core=vs.get_core()

Clip=core.ffms2.Source(source=FichierSource)
Clip=core.std.CropAbs(clip=Clip,width=DimensionCropBox[0],height=DimensionCropBoxes[1],left=int((clip.width-DimensionCropBox[0])/2),top=clip.height-HauteurCropBox-DimensionCropBox[1])

if ModeS=='L':
	Clip=core.std.ShufflePlanes(clips=Clip,planes=0,colorfamily=vs.GRAY)
else:
	Clip=core.fmtc.resample(clip=Clip,css="444")
	Clip=core.fmtc.matrix(clip=Clip,mat="709",col_fam=vs.RGB)
	Clip=core.fmtc.bitdepth(clip=Clip,bits=8)
	if ModeS=='R':
		Clip=core.std.ShufflePlanes(clips=Clip,planes=0,colorfamily=vs.GRAY)
	elif ModeS=='G':
		Clip=core.std.ShufflePlanes(clips=Clip,planes=1,colorfamily=vs.GRAY)
	else:
		Clip=core.std.ShufflePlanes(clips=Clip,planes=2,colorfamily=vs.GRAY)

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
	if ModeU=='nnedi3':
		Clip=core.std.Transpose(Clip)
		for i in range(0,Ss):
			Clip=core.nnedi3.nnedi3(clip=Clip,field=1,dh=1,nsize=0,nns=3)
		Clip=core.std.Transpose(Clip)
		for i in range(0,Ss):
        	Clip=core.nnedi3.nnedi3(clip=Clip,field=1,dh=1,nsize=0,nns=3)
		if Ssbis!=1:
			Clip=core.fmtc.resample(clip=Clip,scale=Ssbis,kernel="sinc",taps=2)
			Clip=core.fmtc.bitdepth(clip=Clip,bits=8)
	else:
		Clip=core.fmtc.resample(clip=Clip,scale=Ss,kernel="sinc",taps=2)
		Clip=core.fmtc.bitdepth(clip=Clip,bits=8)
		
Clip=core.std.Binarize(clip=Clip,threshold=Seuil)
Crop=core.std.CropAbs(clip=Clip,width=Clip.width-20,height=Clip.height-20,left=10,top=10
Rect=core.std.AddBorders(clip=Crop,left=int(10),right=int(10),top=int(10),bottom=int(10),color=255)
Rect.set_output()