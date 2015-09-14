#!/bin/bash
##
while true; do
    if [ -z $1 ]; then echo -e "N'oubliez pas de mettre le nom de la Vidéo Filtrée en argument.\nExemple : ./YoloCR.sh Vidéo_Filtrée.mp4 <lang>"; exit=true; break; fi
    if [[ $2 = fre || $2 = fra || $2 = eng ]]; then if [ ! $(tesseract  --list-langs 2>&1 | grep $2) ]; then exit=true; else lang=$2; fi
    elif [ ! -z $2 ]; then echo -e "Mettez le nom de la Vidéo Filtrée entre guillemets.\nExemple : ./YoloCR.sh \"Vidéo Filtrée.mp4\" <lang>"; exit=true; break; fi
    if [[ ! $(ps -hp $$ | grep bash) ]]; then echo -e "Ce script doit être lancé avec bash.\nExemple : bash YoloCR.sh Vidéo_Filtrée.mp4 <lang>"; exit=true; fi
    break
done
if [ -z $lang ]; then lang=$(tesseract --list-langs 2>&1 | egrep 'fra|eng' | head -1); fi
if [[ $exit = true ]]; then tesseract --list-langs 2>&1 | sed "s/$lang/$lang \(default\)/"; exit; fi

## Prélude
if [[ $lang = fra ]]
    then echo "Prélude."
    else echo "Prelude."
fi
FilteredVideo=$1
if [[ "$OSTYPE" = "linux-gnu" ]]
    then Active=$(xdotool getactivewindow)
         inplace="-i"
    else inplace="-i .bk"
fi
if [ -d ScreensFiltrés ]; then rm ScreensFiltrés/*.jpg 2> /dev/null; else mkdir ScreensFiltrés; fi
if [ -d TessResult ]; then rm TessResult/*.hocr TessResult/*.txt 2> /dev/null; else mkdir TessResult; fi
if [ -f SceneChangesAlt.log ]; then bAlt=true; else bAlt=false; rm TimecodesAlt.txt 2> /dev/null; fi
if [[ $(head -3 SceneChanges.log | tail -1 | cut -d' ' -f2-) != $(head -4 SceneChanges.log | tail -1 | cut -d' ' -f2-) ]]; then tailnum=3; else tailnum=4; fi # Workaround bug SceneChangeDetection
FPS=$(ffprobe "$FilteredVideo" -v 0 -select_streams v -print_format flat -show_entries stream=r_frame_rate | cut -d'"' -f2 | bc -l)
tail -n +$tailnum SceneChanges.log | awk -v fps=$FPS '{if ($3 == 0) printf "%.3f\n", $1/fps; else if ($2 == 0) {var=sprintf ("%.4f", ($1+1)/fps); print substr(var, 0, length(var)-1)}}' | sort -n > Timecodes.txt &
    if $bAlt; then tail -n +$tailnum SceneChangesAlt.log | awk -v fps=$FPS '{if ($3 == 0) printf "%.3f\n", $1/fps; else if ($2 == 0) {var=sprintf ("%.4f", ($1+1)/fps); print substr(var, 0, length(var)-1)}}' | sort -n > TimecodesAlt.txt; fi
        wait
if parallel --minversion 20131122 1> /dev/null; then popt='--bar'; else popt='--eta'; fi
TessVersionNum=$(tesseract -v 2>&1 | head -1 | cut -d' ' -f2)
TessVersionNum2=$(echo $TessVersionNum | cut -d. -f2)

## Utilisation des timecodes pour générer les images à OCR
if [[ $lang = fra ]]
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
if $bAlt; then Crop="-filter:v crop=h=ih/2:y=ih/2"; fi
if file SceneChanges.log | grep CRLF 1> /dev/null; then CRLFtoLF="tr -d '\015' |"; fi
seq 1 2 $(($(wc -l < Timecodes.txt)-1)) | parallel $popt \
    'a=$(sed "{}q;d" Timecodes.txt); b=$(sed "$(({}+1))q;d" Timecodes.txt); ffmpeg -loglevel error -ss $(echo "if ($b-$a-0.003>2/'$FPS') x=($b+$a)/2 else x=$a; if (x<1) print 0; x" | bc -l) -i '$FilteredVideo' -vframes 1 '$Crop' ScreensFiltrés/$(convertsecs "$a")-$(convertsecs "$b").jpg' &
        if $bAlt; then
            for ((i=1;i<=$(wc -l < TimecodesAlt.txt)-1;i+=2)); do
                a=$(sed "${i}q;d" TimecodesAlt.txt); b=$(sed "$((${i}+1))q;d" TimecodesAlt.txt)
                ffmpeg -loglevel error -ss $(echo "if ($b-$a-0.003>2/$FPS) x=($b+$a)/2 else x=$a; if (x<1) print 0; x" | bc -l) -i "$FilteredVideo" -vframes 1 -filter:v crop=h=ih/2:y=0 ScreensFiltrés/$(convertsecs $a)-$(convertsecs $b)_Alt.jpg
            done
        fi &
            ffmpeg -loglevel error -ss $(echo "($(eval "head -2 SceneChanges.log | tail -1 | $CRLFtoLF cut -d' ' -f2") + 255/2) / $FPS" | bc -l) -i "$FilteredVideo" $Crop -vframes 1 ScreensFiltrés/BlackFrame.jpg
                wait
cd ScreensFiltrés; find ./ -name "*.jpg" -size $(ls -l BlackFrame.jpg | awk '{print $5}')c -delete

## OCR d'un dossier avec Tesseract
if [[ $lang = fra ]]
    then echo "OCR du dossier ScreensFiltrés avec Tesseract v${TessVersionNum}."
    else echo "OCR of the ScreensFiltrés directory with Tesseract v${TessVersionNum}."
fi
ls *.jpg | parallel $popt 'tesseract {} ../TessResult/{/.} -l '$lang' -psm 6 hocr 2> /dev/null'; cd ../TessResult
if (($TessVersionNum2 < 03)); then for file in *.html; do mv "$file" "${file%.html}.hocr"; done; fi
if [[ $lang = fra ]]
    then echo "Vérification de l'OCR italique."
    else echo "Verify the italics OCR."
fi
for file in *.hocr; do 
    if grep -q '<em>' $file; then
        if grep -q '\.\.\.' $file; then sxiv "../ScreensFiltrés/${file%.hocr}.jpg" & SXIVPID=$!
            if [[ "$OSTYPE" = "linux-gnu" ]]; then
                while [ $(xdotool getactivewindow) = $Active ]; do sleep 0.1; done
                xdotool windowactivate $Active
            fi
            while true; do read -p "Est-ce de l'italique ? (o/n)" on
                case $on in
                    [Oo]* ) sed -e 's/<em>/ItAlIk1/g' -e 's/<\/em>/ItAlIk2/g' $inplace $file; break;;
                    [Nn]* ) break;;
                    * ) echo "Répondre (o)ui ou (n)on.";;
                esac
            done; kill $SXIVPID; wait $SXIVPID 2>/dev/null
        else sed -e 's/<em>/ItAlIk1/g' -e 's/<\/em>/ItAlIk2/g' $inplace $file
        fi
    fi
    if grep -q '     </span>' $file; then sed $inplace 's/     <\/span>/     <\/span><br>/g' $file; fi
    links -dump -codepage UTF-8 -force-html -width 512 $file > ${file%.hocr}.txt
done

## Vérification de la confidence OCR si Tesseract >= 3.03, ajout des retours à la ligne si besoin, workaround bug "sous-titres vides" et suppresion de ceux restant
if [[ $lang = fra ]]
    then echo "Traitement des faux positifs et Suppression des sous-titres vides."
    else echo "Treat false positives and Delete empty subtitles."
fi
if (($TessVersionNum2 >= 03));
    then ls *.txt | parallel $popt \
        'if [ $(wc -c < {}) = 0 ]
            then tesseract ../ScreensFiltrés/{.}.jpg {.} -l '$lang' -psm 6 2> /dev/null
                if [ $(wc -c < {}) = 0 ]; then rm {}; fi
            else n=$(grep -o x_wconf {.}.hocr | wc -l); j=0; OCR=$(grep x_wconf {.}.hocr | tr "\n" " ")
                for ((i=2;i<$((2+$n));i++)); do j=$(($j + $(echo $OCR | awk -F"x_wconf" -v var=$i \{print\ \$var} | cut -d" " -f2 | sed 's/.$//'))); done
                j=$(($j/$n)); if (($j >= 55)); then echo "" >> {}; else rm {}; fi
        fi'
    else ls *.txt | parallel $popt 'if [ $(wc -c < {}) = 0 ]; then tesseract ../ScreensFiltrés/{.}.jpg {.} -l '$lang' -psm 6 2> /dev/null; if [ $(wc -c < {}) = 0 ]; then rm {}; fi; else echo "" >> {}; fi'
fi
for file in *.txt; do if (( $(wc -l $file | awk '{print $1}') > 4 )); then tesseract ../ScreensFiltrés/${file%.txt}.jpg ${file%.txt} -l $lang -psm 7 2>/dev/null; fi; done # Workaround bug "psm" Tesseract, dangerous
cd ..

## Remplacement anticipé des guillemets droits doubles ("...") en guillemets français doubles (« ... »)
echo "Final."
if [[ $lang = fra ]]; then for file in TessResult/*.txt; do if grep -q \" $file; then
    if [ $(grep -o \" $file | wc -l) = 1 ]
        then sed -e 's/"\. /… /g' -e 's/"\.$/…/g' $inplace $file # Correction éventuelle
             sed -e 's/^"/« /' -e 's/"$/ »/' $inplace $file
        else while grep -q \" $file; do sed '0,/"/{s/"/« /}' $file | sed '0,/"/{s/"/ »/}' > $file.tmp; mv $file.tmp $file; done
    fi
fi; done; fi
 
## Transformation du dossier OCR en srt (les timecodes seront reformatés plus tard)
rm "${FilteredVideo%.mp4}.srt" "${FilteredVideo%.mp4}_Alt.srt" 2> /dev/null
i=0; j=0; for file in TessResult/*.txt; do 
    if [[ $file != *_Alt.txt ]];
        then i=$(($i + 1)); k=$i; Alt=""
        else j=$(($j + 1)); k=$j; Alt="_Alt"
    fi
    echo $k >> OCR$Alt.srt; echo "`basename $file $Alt.txt | sed -e 's/[hm]/_dp/g' -e 's/s/_v/g' -e 's/-/_t/g'`" >> OCR$Alt.srt; cat $file >> OCR$Alt.srt
done
if [ -f OCR_Alt.srt ]; then bAlt=true; Alt="_Alt"; else bAlt=false; Alt=""; fi
sed $inplace 's/   //g' OCR.srt
if $bAlt; then sed $inplace 's/   //g' OCR_Alt.srt; fi

## Conversion des tags "ItAlIk" en balises italiques SubRip
for SRT in $(printf OCR%s.srt\\n "" $Alt); do {
    sed 's/ItAlIk2 ItAlIk1/ /g' $SRT |
    perl -0777 -pe 's/ItAlIk2\nItAlIk1/\n/igs' |
    sed 's/ItAlIk1\(.\)ItAlIk2/\1/g' |
    sed -e 's/ItAlIk1/<i>/g' -e 's/ItAlIk2/<\/i>/g' > $SRT.tmp
    mv $SRT.tmp $SRT
} & done; wait

## Corrections OCR et normalisation
for SRT in $(printf OCR%s.srt\\n "" $Alt); do {
    sed $inplace 's/|/l/g' $SRT
    if [[ $lang = fra ]]; then
        sed "s/I'/l'/g" $SRT |
        sed 's/\([cs]\)oeur/\1œur/g' |
        sed "s/ *'/’/g" |
        sed 's/- /— /g' |
        sed 's/\.\.\./…/g' |
        sed 's/\([:;?\!]\)/ \1/g' | sed 's/  \([:;?\!]\)/ \1/g' |
        sed 's/ :2/ ?/g' > $SRT.tmp
        #sed $inplace 's/___/…/g' $SRT.tmp
        mv $SRT.tmp $SRT
    fi
    if [[ $lang = eng ]]; then sed -e 's/^l /I /g' -e 's/<i>l /<i>I /g' -e 's/ l / I /g' $inplace $SRT; fi
} & done; wait

## Final
for SRT in $(printf OCR%s.srt\\n "" $Alt); do {
    sed -e 's/_t/ --> /' -e 's/_v/,/g' -e 's/_dp/:/g' $inplace $SRT
    if [[ "$OSTYPE" == "linux-gnu" ]]
        then head -n -1 $SRT > "${FilteredVideo%.*}${SRT#*OCR}"
        else tail -r $SRT | tail -n +2 | tail -r > "${FilteredVideo%.*}${SRT#*OCR}"
             rm $SRT.bk
    fi
    rm $SRT
} & done; wait
