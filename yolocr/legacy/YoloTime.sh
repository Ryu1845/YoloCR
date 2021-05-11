#!/bin/bash
##

if [ $(echo $LANG | cut -d= -f2 | cut -d_ -f1) = fr ]; then lang=fra; fi
if [ -z "$1" ]; then echo -e "N'oubliez pas de mettre le nom de la Vidéo Filtrée en argument.\nExemple : ./YoloCR.sh Vidéo_Filtrée.mp4"; exit
elif [ ! -z $3 ]; then echo -e "Mettez le nom de la Vidéo Filtrée entre guillemets.\nExemple : ./YoloCR.sh \"Vidéo Filtrée.mp4\""; exit
elif ! echo $BASH | grep -q bash; then echo -e "Ce script doit être lancé avec bash.\nExemple : bash YoloCR.sh Vidéo_Filtrée.mp4"; exit; fi

if ! awk -W version 2>&1 | grep -q GNU; then echo "Ce script nécessite gawk."; exit; fi

## Prélude
FilteredVideo=$1
if [[ "$OSTYPE" = "linux-gnu" || "$OSTYPE" = "cygwin" ]]
    then inplace="-i"
    else inplace="-i .bk"
fi
if [ -d ScreensFiltrés ]; then rm ScreensFiltrés/*.jpg 2>/dev/null; else mkdir ScreensFiltrés; fi
if [ -f SceneChangesAlt.log ]; then bAlt=true; else bAlt=false; rm TimecodesAlt.txt 2>/dev/null; fi
FPS=$(ffprobe "$FilteredVideo" -v 0 -select_streams v -print_format flat -show_entries stream=r_frame_rate | cut -d'"' -f2 | bc -l)
awk -v fps=$FPS '{if ($3 == 0) {var=sprintf ("%.4f", $1/fps); print substr(var, 0, length(var)-1)} else if ($2 == 0) {var=sprintf ("%.4f", ($1+1)/fps); print substr(var, 0, length(var)-1)}}' SceneChanges.log | sort -n > Timecodes.txt &
    if $bAlt; then awk -v fps=$FPS '{if ($3 == 0) {var=sprintf ("%.4f", $1/fps); print substr(var, 0, length(var)-1)} else if ($2 == 0) {var=sprintf ("%.4f", ($1+1)/fps); print substr(var, 0, length(var)-1)}}' SceneChangesAlt.log | sort -n > TimecodesAlt.txt; fi
        wait
if parallel --minversion 20131122 1>/dev/null; then popt="--no-notice --bar -j $(nproc)"; else popt="--no-notice --eta -j $(nproc)"; fi

## Utilisation des timecodes pour générer les images à OCR
if [ $lang = fra ]
    then echo "Génération des Screens à partir de la Vidéo Filtrée."
    else echo "Generate Screens using the Filtered Video."
fi
convertsecs() {
 secs=$(echo $1 | cut -d. -f1)
 ((h=${secs}/3600))
 ((m=(${secs}%3600)/60))
 ((s=${secs}%60))
 ms=$(echo $1 | cut -d. -f2 | bc)
 printf "%02dh%02dm%02ds%03d\n" $h $m $s $ms
}
export -f convertsecs
if $bAlt
    then Crop="-filter:v crop=h=ih/2:y=ih/2"
         if (( $(tail -1 SceneChangesAlt.log  | cut -d' ' -f1) > $(tail -1 SceneChanges.log | cut -d' ' -f1) )); then Alt=Alt; fi
fi
if file SceneChanges.log | grep CRLF 1>/dev/null; then CRLFtoLF="tr -d '\015' |"; fi
seq 1 2 $(($(wc -l < Timecodes.txt)-1)) | parallel $popt \
    'a=$(sed "{}q;d" Timecodes.txt); b=$(sed "$(({}+1))q;d" Timecodes.txt); ffmpeg -loglevel error -ss $(echo "if ($b-$a-0.003>2/'$FPS') x=($b+$a)/2 else x=$a; if (x<1) print 0; x" | bc -l) -i '\"$FilteredVideo\"' -vframes 1 '$Crop' ScreensFiltrés/$(convertsecs "$a")-$(convertsecs "$b").jpg' &
        if $bAlt; then
            for ((i=1;i<=$(wc -l < TimecodesAlt.txt)-1;i+=2)); do
                a=$(sed "${i}q;d" TimecodesAlt.txt); b=$(sed "$((${i}+1))q;d" TimecodesAlt.txt)
                ffmpeg -loglevel error -ss $(echo "if ($b-$a-0.003>2/$FPS) x=($b+$a)/2 else x=$a; if (x<1) print 0; x" | bc -l) -i "$FilteredVideo" -vframes 1 -filter:v crop=h=ih/2:y=0 ScreensFiltrés/$(convertsecs $a)-$(convertsecs $b)_Alt.jpg
            done
        fi &
            ffmpeg -loglevel error -ss $(echo "$(tail -1 Timecodes$Alt.txt) * 1/8 + $(ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 "$FilteredVideo") * 7/8" | bc) -i "$FilteredVideo" $Crop -vframes 1 ScreensFiltrés/BlackFrame.jpg
                wait
cd ScreensFiltrés; find ./ -name "*.jpg" -size $(ls -l BlackFrame.jpg | awk '{print $5}')c -delete

## Remplacement anticipé des guillemets droits doubles ("...") en guillemets français doubles (« ... »)
echo "Final."
cd ..
 
## Transformation du dossier OCR en srt (les timecodes seront reformatés plus tard)
Base="${FilteredVideo%.mp4}_Time"
rm "$Base.srt" "$Base_Alt.srt" 2>/dev/null
i=0; j=0; for file in ScreensFiltrés/*.jpg; do 
    if [[ $file != *_Alt.jpg ]];
        then i=$(($i + 1)); k=$i; Alt=""
        else j=$(($j + 1)); k=$j; Alt="_Alt"
    fi
    echo $k >> "$Base$Alt.srt"; echo "`basename $file $Alt.jpg | sed -e 's/[hm]/:/g' -e 's/s/,/g' -e 's/-/ --> /g'`" >> "$Base$Alt.srt"; echo "" >> "$Base$Alt".srt
done
