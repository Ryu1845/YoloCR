FichierSource='Vidéo_Source.mkv'
DimensionCropBox=[1344,150] # Taille en largeur et hauteur de la CropBox délimitant les sous-titres à OCR.
HauteurCropBox=196 # Hauteur de la CropBox délimitant les sous-titres à OCR.


import vapoursynth as vs
core=vs.get_core()

Clip=core.ffms2.Source(source=FichierSource)
Crop=core.std.CropAbs(clip=Clip,width=DimensionCropBox[0]+20,height=DimensionCropBoxes[1]+20,left=int((clip.width-DimensionCropBox[0])/2-10),top=clip.height-HauteurCropBox-10)
Rect=core.std.AddBorders(clip=Crop,left=int(10),right=int(10),top=int(10),bottom=int(10),color=255)
Rect.set_output()