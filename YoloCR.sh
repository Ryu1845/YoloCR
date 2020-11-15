#!/bin/bash
##

if [ ! -z $2 ]; then test=false; for testlang in $(tesseract  --list-langs 2>&1 | tail -n +2); do if [ $testlang == $2 ]; then test=true; fi; done; fi
if [ -z "$1" ]; then echo -e "N'oubliez pas de mettre le nom de la Vidéo Filtrée en argument.\nExemple : ./YoloCR.sh Vidéo_Filtrée.mp4 <lang>"; exit=true
elif [ ! -z $3 ]; then echo -e "Mettez le nom de la Vidéo Filtrée entre guillemets.\nExemple : ./YoloCR.sh \"Vidéo Filtrée.mp4\" <lang>"; exit=true
elif [[ $test = false ]]; then echo -e "Vérifiez que le dictionnaire Tesseract correspondant à la langue choisie est bien installé.\nExemple : ./YoloCR.sh Vidéo_Filtrée.mp4 fra"; exit=true
elif ! echo $BASH | grep -q bash; then echo -e "Ce script doit être lancé avec bash.\nExemple : bash YoloCR.sh Vidéo_Filtrée.mp4 <lang>"; exit=true
elif [[ $test = true ]]; then lang=$2; fi

if [ -z $lang ]; then if tesseract --list-langs 2>&1 | grep -q fra
    then lang=fra
    else lang=eng
fi; fi

if [ "$exit" = "true" ]; then tesseract --list-langs 2>&1 | sed "s/$lang/$lang \(default\)/"; exit; fi
if ! awk -W version 2>&1 | grep -q GNU; then echo "Ce script nécessite gawk."; exit; fi

## Prélude
if hash sxiv 2>/dev/null
    then mode=GUI; Active=$(xdotool getactivewindow)
    else mode=CLI
fi
if [ $lang = fra ]
    then echo -e "Utilisation de YoloCR en mode $mode.\nPrélude."
    else echo -e "Using YoloCR in $mode mode.\nPrelude."
fi
FilteredVideo=$1
if [[ "$OSTYPE" = *"linux"* || "$OSTYPE" = "cygwin" ]]
    then inplace="-i"
    else inplace="-i .bk"
fi
if [ -d ScreensFiltrés ]; then rm ScreensFiltrés/*.jpg 2>/dev/null; else mkdir ScreensFiltrés; fi
if [ -d TessResult ]; then rm TessResult/*.hocr TessResult/*.txt 2>/dev/null; else mkdir TessResult; fi
if [ -f SceneChangesAlt.log ]; then bAlt=true; else bAlt=false; rm TimecodesAlt.txt 2>/dev/null; fi
FPS=$(ffprobe "$FilteredVideo" -v 0 -select_streams v -print_format flat -show_entries stream=r_frame_rate | cut -d'"' -f2 | bc -l)
awk -v fps=$FPS '{if ($3 == 0) {var=sprintf ("%.4f", $1/fps); print substr(var, 0, length(var)-1)} else if ($2 == 0) {var=sprintf ("%.4f", ($1+1)/fps); print substr(var, 0, length(var)-1)}}' SceneChanges.log | sort -n > Timecodes.txt &
    if $bAlt; then awk -v fps=$FPS '{if ($3 == 0) {var=sprintf ("%.4f", $1/fps); print substr(var, 0, length(var)-1)} else if ($2 == 0) {var=sprintf ("%.4f", ($1+1)/fps); print substr(var, 0, length(var)-1)}}' SceneChangesAlt.log | sort -n > TimecodesAlt.txt; fi
        wait
if parallel --minversion 20131122 1>/dev/null; then popt="--no-notice --bar -j $(nproc)"; else popt="--no-notice --eta -j $(nproc)"; fi
TessVersionNum=$(tesseract -v 2>&1 | head -1 | cut -d' ' -f2)
if [ "$OSTYPE" = "cygwin" ]; then TessVersionNum=$(echo $TessVersionNum | tr -d '\015'); fi
TessVersionNum1=$(echo $TessVersionNum | cut -d. -f1)
TessVersionNum2=$(echo $TessVersionNum | cut -d. -f2)

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
        fi
            wait; cd ScreensFiltrés
ffmpeg -loglevel error -i $(ls | head -1) -filter:v colorchannelmixer=rr=0:gg=0:bb=0 -pix_fmt yuvj420p BlackFrame.jpg
find ./ -name "*.jpg" -size $(ls -l BlackFrame.jpg | awk '{print $5}')c -delete

## Sélection du moteur OCR
if grep -q Microsoft /proc/version || [ "$OSTYPE" = "cygwin" ]; then
    if reg.exe query HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App\ Paths\\FineReader.exe /ve | grep -q REG_SZ && hash tesseract 2>/dev/null; then
        while true; do read -p "Voulez vous utiliser (T)esseract ou Abby (F)ineReader ?" TF
            case $TF in
                [Tt]* ) OCRType=Tesseract; break;;
                [Ff]* ) OCRType=FineReader; break;;
                * ) echo "Répondre (T)esseract ou (F)ineReader.";;
            esac
        done
    elif reg.exe query HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App\ Paths\\FineReader.exe /ve | grep -q REG_SZ; then OCRType=FineReader
    else OCRType=Tesseract; fi
else OCRType=Tesseract; fi

## OCR d'un dossier avec Tesseract
if [ $OCRType = Tesseract ]; then
    if [ $lang = fra ]
        then echo "OCR du dossier ScreensFiltrés avec Tesseract v${TessVersionNum}."
             msg="Utilisation du moteur"
        else echo "OCR of the ScreensFiltrés directory with Tesseract v${TessVersionNum}."
             msg="Using engine"
    fi
    if (( $TessVersionNum1 >= 4 ))
        then psm="--psm"
                 if [ -f ../tessdata/$lang.traineddata ]; then tessdata="--tessdata-dir ../tessdata"; fi
                 if tesseract $(ls *.jpg | head -1) - $tessdata -l $lang --oem 0 1>/dev/null 2>&1
                    then echo "$msg Legacy."; oem="--oem 0"
                    else echo "$msg LSTM."; ls *.jpg | parallel $popt convert {} -negate {}
                 fi
        else echo "$msg Legacy."; psm="-psm"
    fi
    ls *.jpg | parallel $popt 'OMP_THREAD_LIMIT=1 tesseract {} ../TessResult/{/.} '$tessdata' -l '$lang' '$oem' '$psm' 6 hocr 2>/dev/null'; cd ../TessResult
    if (( $TessVersionNum1 < 4 )) && (( $TessVersionNum2 < 3 )); then for file in *.html; do mv "$file" "${file%.html}.hocr"; done; fi
    if [ $lang = fra ]
        then echo "Vérification de l'OCR italique."; Question="Est-ce de l'italique ? (o/n)"; BadAnswer="Répondre (o)ui ou (n)on."
        else echo "Verify the italics OCR."; Question="Is it italic type ? (y/n)"; BadAnswer="Answer (y)es or (n)o."
    fi
    for file in *.hocr; do
        if grep -q '<em>' $file; then
            if grep -q '\.\.\.' $file; then
                if [ $mode = GUI ]
                    then sxiv "../ScreensFiltrés/${file%.hocr}.jpg" & SXIVPID=$!
                        if [ "$OSTYPE" = "linux-gnu" ]; then
                            while [ $(xdotool getactivewindow) = $Active ]; do sleep 0.1; done
                            xdotool windowactivate $Active
                        fi
                        while true; do read -p "$Question" oyn
                            case $oyn in
                                [OoYy]* ) sed -e 's/<em>/ItAlIk1/g' -e 's/<\/em>/ItAlIk2/g' $inplace $file; break;;
                                [Nn]* ) break;;
                                * ) echo "$BadAnswer";;
                            esac
                        done; kill $SXIVPID; wait $SXIVPID 2>/dev/null
                    else sed -e 's/<em>/ItAlIk1/g' -e 's/<\/em>/ItAlIk2/g' $inplace $file
                         echo "Vérifiez les balises italique à ${file%.hocr}" 
                fi
            else sed -e 's/<em>/ItAlIk1/g' -e 's/<\/em>/ItAlIk2/g' $inplace $file
            fi
        fi
        if grep -q '     </span>' $file; then sed $inplace 's/     <\/span>/     <\/span><br>/g' $file; fi
        links -dump -codepage UTF-8 -force-html -width 512 $file > ${file%.hocr}.txt
    done

## Vérification de la confidence OCR si Tesseract >= 3.03, ajout des retours à la ligne si besoin, workaround bug "sous-titres vides" et suppresion de ceux restant
    if [ $lang = fra ]
        then echo "Traitement des faux positifs et Suppression des sous-titres vides."
        else echo "Treat false positives and Delete empty subtitles."
    fi
    if (( $TessVersionNum1 >= 4 || $TessVersionNum2 >= 3 ))
        then ls *.txt | parallel $popt \
             if [ \$\(wc -c \< {}\) = 0 ]\; \
                then OMP_THREAD_LIMIT=1 tesseract ../ScreensFiltrés/{.}.jpg {.} \$tessdata -l \$lang \$oem \$psm 6 2\>/dev/null\; \
                     if \(\( \$\(wc -c \< {}\) \> 0 \)\)\; then echo "" \>\> {}\; else rm {}\; fi\; \
                else n=\$\(grep -o x_wconf {.}.hocr \| wc -l\)\; \
                     j=\$\(cat {.}.hocr \| grep -Po \"x_wconf \\K[^\']*\" \| tr '\\n' +\)\; \
                     j=\$\(\(\${j::-1}/\$n\)\)\; if \(\( \$j \>= 55 \)\)\; then echo "" \>\> {}\; else rm {}\; fi\; \
             fi
        else ls *.txt | parallel $popt 'if [ $(wc -c < {}) = 0 ]; then OMP_THREAD_LIMIT=1 tesseract ../ScreensFiltrés/{.}.jpg {.} -l '$lang' '$oem' '$psm' 6 2>/dev/null; if [ $(wc -c < {}) = 0 ]; then rm {}; fi; else echo "" >> {}; fi'
    fi
    for file in *.txt; do if (( $(wc -l $file | awk '{print $1}') > 4 )); then tesseract ../ScreensFiltrés/${file%.txt}.jpg ${file%.txt} $tessdata -l $lang $oem $psm 7 2>/dev/null; echo "" >> $file; fi; done # Workaround bug "psm" Tesseract, dangerous
fi

## OCR d'un dossier avec FineReader
if [ $OCRType = FineReader ]; then
    if [ $lang = fra ]
        then echo "Une fois l'OCR par FineReader effectué, placez les fichiers dans le dossier TessResult et appuyez sur la touche de votre choix."
        else echo "When you're done with FineReader's OCR, put the files in the TessResult direcory and press the key of your choice."
    fi
    read answer; case $answer in * ) ;; esac
fi

## Remplacement anticipé des guillemets droits doubles ("...") en guillemets français doubles (« ... »)
echo "Final."
cd ..
if [ $lang = fra ]; then for file in TessResult/*.txt; do if grep -q \" $file; then
    if [ $OCRType = FineReader ]; then cat $file | iconv -f WINDOWS-1252 -t UTF-8 >> $file.tmp; mv $file.tmp $file; fi
    if [ $(grep -o \" $file | wc -l) = 1 ]
        then sed -e 's/"\. /… /g' -e 's/"\.$/…/g' $inplace $file # Correction éventuelle
             sed -e 's/^"/« /' -e 's/"$/ »/' $inplace $file
        else while grep -q \" $file; do sed '0,/"/{s/"/« /}' $file | sed '0,/"/{s/"/ »/}' > $file.tmp; mv $file.tmp $file; done
    fi
    if [[ $OCRType = FineReader ]]; then cat $file | iconv -f UTF-8 -t WINDOWS-1252 >> $file.tmp; mv $file.tmp $file; fi
fi; done; fi
 
## Transformation du dossier OCR en srt (les timecodes seront reformatés plus tard)
rm "${FilteredVideo%.mp4}.srt" "${FilteredVideo%.mp4}_Alt.srt" 2>/dev/null
i=0; j=0; for file in TessResult/*.txt; do 
    if [[ $file != *_Alt.txt ]];
        then i=$(($i + 1)); k=$i; Alt=""
        else j=$(($j + 1)); k=$j; Alt="_Alt"
    fi
    echo $k >> OCR$Alt.srt; echo "`basename $file $Alt.txt | sed -e 's/[hm]/_dp/g' -e 's/s/_v/g' -e 's/-/_t/g'`" >> OCR$Alt.srt
    if [ $OCRType = Tesseract ]
        then cat $file >> OCR$Alt.srt
        else cat $file | iconv -f WINDOWS-1252 -t UTF-8 >> OCR$Alt.srt; echo -e "\n\n" >> OCR$Alt.srt
    fi
done
if [ -f OCR_Alt.srt ]; then bAlt=true; Alt="_Alt"; else bAlt=false; Alt=""; fi
sed $inplace 's/   //g' OCR.srt
if $bAlt; then sed $inplace 's/   //g' OCR_Alt.srt; fi

## Conversion des tags "ItAlIk" en balises italiques SubRip
if [ $OCRType = Tesseract ]; then for SRT in $(printf OCR%s.srt\\n "" $Alt); do {
    if grep -q 'ItAlIk' $SRT; then
        sed $inplace 's/\//l/g' $SRT # Autre correction éventuelle
        sed 's/ItAlIk2 ItAlIk1/ /g' $SRT |
        perl -0777 -pe 's/ItAlIk2\nItAlIk1/\n/igs' |
        sed 's/ItAlIk1\(.\)ItAlIk2/\1/g' |
        sed -e 's/ItAlIk1/<i>/g' -e 's/ItAlIk2/<\/i>/g' > $SRT.tmp
        mv $SRT.tmp $SRT
    fi
} & done; wait; fi

## Corrections OCR et normalisation
for SRT in $(printf OCR%s.srt\\n "" $Alt); do {
    sed $inplace 's/|/l/g' $SRT
    if [[ $lang = fra ]]; then
        sed -e "s/I'/l'/g" -e 's/iI /il /g' $SRT |
        sed 's/^\]/J/g' |
        sed 's/[®©]/O/g' |
        sed -e 's/\([cs]\)oeur/\1œur/g' -e 's/oeuvre/œuvre/g' -e 's/oeuf/œuf/g' |
        sed "s/ *['‘]/’/g" |
        sed 's/\(.\)—\(.\)/\1-\2/g' |
        sed -e 's/<< /« /g' -e 's/ >>/ »/g' |
        sed 's/- /— /g' |
        sed 's/\.\.\./…/g' |
        sed 's/…\./…/g' |
        sed 's/\([:;?\!]\)/ \1/g' | sed 's/  \([:;?\!]\)/ \1/g' |
        sed 's/ :2/ ?/g' |
        perl -0777 -pe 's/\n\n[0-9]\n\n/\n\n/igs' > $SRT.tmp
        #sed $inplace 's/___/…/g' $SRT.tmp
        mv $SRT.tmp $SRT
    fi
    if [ $lang = eng ]; then sed -e 's/^l /I /g' -e 's/<i>l /<i>I /g' -e 's/ l / I /g' $inplace $SRT; fi
} & done; wait

## Final
for SRT in $(printf OCR%s.srt\\n "" $Alt); do {
    sed -e 's/_t/ --> /' -e 's/_v/,/g' -e 's/_dp/:/g' $SRT > "${FilteredVideo%.*}${SRT#*OCR}"
    rm $SRT $SRT.bk 2>/dev/null
} & done; wait
