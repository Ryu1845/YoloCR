FichierSource='Vidéo_Source.mkv'
DimensionCropBoxes=[1344,150] # Taille en largeur et hauteur de la CropBox délimitant les sous-titres à OCR.
HauteurCropBox=196 # Hauteur de la CropBox délimitant les sous-titres à OCR.
HauteurCropBoxAlt=-1 # Hauteur de la CropBox Alternative, utile pour l'OCR des indications. Double le temps de traitement. Mettre à -1 pour désactiver.
Supersampling=-1 # Facteur de supersampling (multiplication de la résolution de la vidéo). Mettre à -1 pour calculer le facteur automatiquement.
ExpandRatio=1 # EXPERIMENTAL ! Facteur Expand/Inpand. La valeur 1 est adaptée pour un Supersampling automatique (1080p). Calcul typique de la valeur : ExpandRatio="RésolutionFinale"/1080.
ModeU='sinc' # 'sinc' (2 taps, plus rapide) ou 'nnedi3' (plus lent), contrôle la méthode d'Upscale. 
SeuilsST=[230,80] # Seuils délimitant les sous-titres. Ces valeurs sont la luminosité maximale de leur intérieur et extérieur respectivement.
SeuilSCD=6 # Un seuil trop bas augmente le nombre de faux positifs, un seuil trop haut ne permet pas de détecter tous les sous-titres.


import vapoursynth as vs
import havsfunc as haf
import functools
core=vs.get_core()

def minimum(x,y):
	return min(x,y)

def Identity(n,clip,f):
	return clip

Clip=core.ffms2.Source(source=FichierSource)
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

def Resizing(clip,largeur,hauteur,hauteur2):
	clip=core.std.CropAbs(clip=clip,width=largeur,height=hauteur,left=int((clip.width-largeur)/2),top=clip.height-hauteur2)
	if Ss!=1:
		if ModeU=='nnedi3':
			for i in range(0,Ss):
				clip=core.std.Transpose(clip)
				clip=core.nnedi3.nnedi3(clip=clip,field=1,dh=1,nsize=0,nns=3)
			if Ssbis!=1:
				clip=core.fmtc.resample(clip=clip,scale=Ssbis,kernel="sinc",taps=2)
				clip=core.fmtc.bitdepth(clip=clip,bits=8)
		else:
			clip=core.fmtc.resample(clip=clip,scale=Ss,kernel="sinc",taps=2)
			clip=core.fmtc.bitdepth(clip=clip,bits=8)
	return clip

def Cleaning(clip,seuili,seuilo,e):
	White_Raw=core.std.Binarize(clip=clip,threshold=seuili)
	Bright_Raw=core.std.Binarize(clip=clip,threshold=seuilo)

	Blank=core.std.BlankClip(clip)

	Bright_Out=core.std.Lut2(clipa=Bright_Raw,clipb=Rect,function=minimum)

	Bright_Not=core.generic.Hysteresis(base=Bright_Out,alt=Bright_Raw)
	Bright_Not=core.std.Invert(Bright_Not)

	White_Txt=core.std.MaskedMerge(Blank,White_Raw,Bright_Not)

	White_Lb=haf.mt_inpand_multi(src=White_Txt,sw=int(e),sh=int(e),mode="ellipse")
	White_Lb=haf.mt_expand_multi(src=White_Lb,sw=int(e),sh=int(e),mode="ellipse")

	White_Ub=haf.mt_inpand_multi(src=White_Txt,sw=int(5*e),sh=int(5*e),mode="ellipse")
	White_Ub=haf.mt_expand_multi(src=White_Ub,sw=int(3*e),sh=int(3*e),mode="ellipse")
	White_Ub=core.std.Invert(White_Ub)

	White=core.std.MaskedMerge(Blank,White_Lb,White_Ub)
	White=core.generic.Hysteresis(base=White,alt=White_Txt)

	ClipCleaning=core.std.MaskedMerge(Blank,White_Raw,White)
	ClipCleaning=core.std.Median(clip=ClipCleaning)
	
	return ClipCleaning

ClipResized=Resizing(Clip,DimensionCropBoxes[0],DimensionCropBoxes[1],HauteurCropBox)
Blackclip=core.std.BlankClip(width=int(ClipResized.width-20),height=int(ClipResized.height-20),format=vs.GRAY8,color=0)
Rect=core.std.AddBorders(clip=Blackclip,left=int(10),right=int(10),top=int(10),bottom=int(10),color=255)
ClipCleaned=Cleaning(ClipResized,SeuilsST[0],SeuilsST[1],ExpandRatio)
if Supersampling==-1:
	ClipCleanedSC=core.std.CropAbs(clip=ClipCleaned,width=500,height=56,left=int((ClipCleaned.width-500)/2),top=int(ClipCleaned.height/2))
else:
	ClipCleanedSC=core.std.CropAbs(clip=ClipCleaned,width=int(ClipCleaned.width/2.7),height=int(ClipCleaned.height/2.7),left=int(ClipCleaned.width*(1-1/2.7)/2),top=int(ClipCleaned.height/2))
ClipCleanedSC=core.scd.Detect(clip=ClipCleanedSC,thresh=SeuilSCD,log="SceneChanges.log")
ClipCleaned=core.std.FrameEval(ClipCleaned,functools.partial(Identity,clip=ClipCleaned),prop_src=ClipCleanedSC)

if HauteurCropBoxAlt>=0:
	ClipResizedAlt=Resizing(Clip,DimensionCropBoxes[0],DimensionCropBoxes[1],HauteurCropBoxAlt)
	ClipCleanedAlt=Cleaning(ClipResizedAlt,SeuilsST[0],SeuilsST[1])
	if Supersampling==-1:
		ClipCleanedAltSC=core.std.CropAbs(clip=ClipCleanedAlt,width=500,height=56,left=int((ClipCleanedAlt.width-500)/2),top=int(ClipCleanedAlt.height/2-56))
	else:
		ClipCleanedAltSC=core.std.CropAbs(clip=ClipCleanedAlt,width=int(ClipCleanedAlt.width/2.7),height=int(ClipCleanedAlt.height/2.7),left=int(ClipCleanedAlt.width*(1-1/2.7)/2),top=int(ClipCleanedAlt.height*(1/2-1/2.7)))
	ClipCleanedAltSC=core.scd.Detect(clip=ClipCleanedAltSC,thresh=SeuilSCD,log="SceneChangesAlt.log")
	ClipCleanedAlt=core.std.FrameEval(ClipCleanedAlt,functools.partial(Identity,clip=ClipCleanedAlt),prop_src=ClipCleanedAltSC)
	
	Clip=core.std.StackVertical([ClipCleanedAlt,ClipCleaned])

else:
	Clip=ClipCleaned

Clip=Clip+core.std.BlankClip(clip=Clip,length=255,color=0)
Clip.set_output()
