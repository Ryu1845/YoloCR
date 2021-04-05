#!/bin/bash
# TODO port to python because bash is such a pain
##
convert_secs() {
    secs=$(echo $1 | cut -d. -f1)
    ((h=${secs}/3600))
    ((m=(${secs}%3600)/60))
    ((s=${secs}%60))
    ms=$(echo $1 | cut -d. -f2 | bc)
    printf "%02dh%02dm%02ds%03d\n" $h $m $s $ms
}
export -f convert_secs


error_handling() {
    # Check if tesseract dictionary is installed
    if [ ! -z $2 ]; then 
        test=false
        for testlang in $(tesseract  --list-langs 2>&1 | tail -n +2); do
            if [ $testlang == $2 ]; then
                test=true
            fi
        done
    fi
    if [ -z "$1" ]; then
        echo -e "N'oubliez pas de mettre le nom de la Vidéo Filtrée en argument.\n\Exemple : ./YoloCR.sh Vidéo_Filtrée.mp4 <lang>"
        exit=true
    elif [ ! -z $3 ]; then
        echo -e "Mettez le nom de la Vidéo Filtrée entre guillemets.\nExemple : ./YoloCR.sh \"Vidéo Filtrée.mp4\" <lang>"
        exit=true
    elif [[ $test = false ]]; then
        echo -e "Vérifiez que le dictionnaire Tesseract correspondant à la langue choisie est bien installé.\nExemple : ./YoloCR.sh Vidéo_Filtrée.mp4 fra"
        exit=true
    elif ! echo $BASH | grep -q bash; then
        echo -e "Ce script doit être lancé avec bash.\nExemple : bash YoloCR.sh Vidéo_Filtrée.mp4 <lang>"
        exit=true
    elif [[ $test = true ]]; then
        lang=$2
    fi
    # Either English or French for language
    if [ -z $lang ]; then
        if tesseract --list-langs 2>&1 | grep -q fra; then
            lang=fra
        else
            lang=eng
        fi
    fi

    if [ "$exit" = "true" ]; then
        tesseract --list-langs 2>&1 |
        sed "s/$lang/$lang \(default\)/"
        exit
    fi
    if ! awk -W version 2>&1 | grep -q GNU; then
        echo "Ce script nécessite gawk."
        exit
    fi
}


init() {
    if parallel --minversion 20131122 1>/dev/null; then
        popt="--no-notice --bar -j $(nproc)"
    else
        popt="--no-notice --eta -j $(nproc)"
    fi
    tess_version_num=$(tesseract -v 2>&1 | head -1 | cut -d' ' -f2)
    if [ "$OSTYPE" = "cygwin" ]; then
        tess_version_num=$(echo $tess_version_num | tr -d '\015')
    fi
    tess_version_num1=$(echo $tess_version_num | cut -d. -f1)
    tess_version_num2=$(echo $tess_version_num | cut -d. -f2)

    # Check if GUI or CLI
    if hash sxiv 2>/dev/null; then
        mode=GUI
        Active=$(xdotool getactivewindow)
    else
        mode=CLI
    fi
    [ $lang = fra ] && echo -e "Utilisation de YoloCR en mode $mode.\nPrélude." || echo -e "Using YoloCR in $mode mode.\nPrelude."

    filtered_video=$1

    if [[ "$OSTYPE" = *"linux"* || "$OSTYPE" = "cygwin" ]]; then
        inplace="-i"
    else
        inplace="-i .bk"
    fi
    if [ -d filtered_scsht ]; then
        rm filtered_scsht/*.jpg 2>/dev/null
    else
        mkdir filtered_scsht
    fi
    if [ -d tess_result ];then
        rm tess_result/*.hocr tess_result/*.txt 2>/dev/null
    else
        mkdir tess_result
    fi
    if [ -f scene_changes_alt.log ]; then
        has_alt=true
    else
        has_alt=false
        rm timecodes_alt.txt 2>/dev/null
    fi
}


generate_timecodes() {
    FPS=$(\
            ffprobe "$filtered_video" \
                -v 0 \
                -select_streams v \
                -print_format flat \
                -show_entries stream=r_frame_rate | \
            cut -d'"' -f2 | \
            bc -l\
        )
    awk -v fps=$FPS \
   '{if ($3 == 0) {
        var=sprintf ("%.4f", $1/fps)
        print substr(var, 0, length(var)-1)
    } else if ($2 == 0) {
        var=sprintf ("%.4f", ($1+1)/fps)
        print substr(var, 0, length(var)-1)
    }}' scene_changes.log |
    sort -n > timecodes.txt &
    if $has_alt; then
        awk -v fps=$FPS \
        '{if ($3 == 0) {
            var=sprintf ("%.4f", $1/fps)
            print substr(var, 0, length(var)-1)
        } else if ($2 == 0) {
            var=sprintf ("%.4f", ($1+1)/fps)
            print substr(var, 0, length(var)-1)
        }}' scene_changes_alt.log |
        sort -n > timecodes_alt.txt
    fi
    wait
}


generate_scsht() {
    if $has_alt;then
        crop="-filter:v crop=h=ih/2:y=ih/2"
        if (( $(tail -1 scene_changes_alt.log  | cut -d' ' -f1) > $(tail -1 scene_changes.log | cut -d' ' -f1) )); then
            Alt=Alt
        fi
    fi
    nline_timecodes=$(wc -l < timecodes.txt)
    seq 1 2 $(($nline_timecodes-1)) |
    parallel $popt \
       'odd=$(sed "{}q;d" timecodes.txt)
        even=$(sed "$(({}+1))q;d" timecodes.txt)
        c=$(echo "if ($even-$odd-0.003>2/'$FPS') x=($even+$odd)/2 else x=$odd; if (x<1) print 0; x" | bc -l)
        ffmpeg \
            -loglevel error \
            -ss "${c}"\
            -i '\"$filtered_video\"' \
            -vframes 1 \
            '$crop' \
            filtered_scsht/$(convert_secs "$odd")-$(convert_secs "$even").jpg' &
    if $has_alt; then
        nline_timecodes_alt=$(wc -l < timecodes_alt.txt)
        for ((i=1; i<=${nline_timecodes_alt}-1; i+=2)); do
            odd=$(sed "${i}q;d" timecodes_alt.txt)
            even=$(sed "$((${i}+1))q;d" timecodes_alt.txt)
            c=$(echo "if ($even-$odd-0.003>2/$FPS) x=($even+$odd)/2 else x=$odd; if (x<1) print 0; x" | bc -l)
            ffmpeg \
                -loglevel error \
                -ss "${c}" \
                -i "$filtered_video" \
                -vframes 1 \
                -filter:v crop=h=ih/2:y=0 \
                filtered_scsht/"$(convert_secs $odd)"-"$(convert_secs $even)"_Alt.jpg
        done
    fi
    wait
    cd filtered_scsht || exit

    # Delete black frames
    ffmpeg \
        -loglevel error \
        -i "$(ls | head -1)" \
        -filter:v colorchannelmixer=rr=0:gg=0:bb=0 \
        -pix_fmt yuvj420p \
        black_frame.jpg
    black_frame_size=$(ls -l black_frame.jpg | awk '{print $5}')
    find ./ -name "*.jpg" -size ${black_frame_size}c -delete
}


ocr_select() {
    if grep -q Microsoft /proc/version || [ "$OSTYPE" = "cygwin" ]; then
        if reg.exe query HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App\ Paths\\FineReader.exe /ve | grep -q REG_SZ && hash tesseract 2>/dev/null; then
            while true; do
                read -p "Voulez vous utiliser (T)esseract ou Abby (F)ineReader ?" TF
                case $TF in
                    [Tt]* ) OCRType=Tesseract; break;;
                    [Ff]* ) OCRType=FineReader; break;;
                    * ) echo "Répondre (T)esseract ou (F)ineReader.";;
                esac
            done
        elif reg.exe query HKEY_LOCAL_MACHINE\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\App\ Paths\\FineReader.exe /ve | grep -q REG_SZ; then
            OCRType=FineReader
        else
            OCRType=Tesseract
        fi
    else
        OCRType=Tesseract
    fi
}


ocr_tesseract() {
    if (( $tess_version_num1 >= 4 ));then
        psm="--psm"
        if [ -f ../tessdata/$lang.traineddata ]; then
            tessdata="--tessdata-dir ../tessdata"
        fi
        if tesseract "$(ls *.jpg | head -1)" - $tessdata -l $lang --oem 0 1>/dev/null 2>&1;then
            echo "$msg Legacy."
            oem="--oem 0"
        else
            echo "$msg LSTM."
            ls *.jpg |
            parallel $popt convert {} -negate {}
        fi
    else
        echo "$msg Legacy."
        psm="-psm"
    fi
    ls *.jpg |
    parallel $popt 'OMP_THREAD_LIMIT=1 tesseract {} ../tess_result/{/.} '$tessdata' -l '$lang' '$oem' '$psm' 6 hocr 2>/dev/null'
    cd ../tess_result || exit
    if (( $tess_version_num1 < 4 )) && (( $tess_version_num2 < 3 )); then
        for file in *.html; do
            mv "$file" "${file%.html}.hocr"
        done
    fi
    if [ $lang = fra ];then
        echo "Vérification de l'OCR italique."
        Question="Est-ce de l'italique ? (o/n)"
        BadAnswer="Répondre (o)ui ou (n)on."
    else
        echo "Verify the italics OCR."
        Question="Is it italic type ? (y/n)"
        BadAnswer="Answer (y)es or (n)o."
    fi
    for file in *.hocr; do
        if grep -q '<em>' $file; then
            if grep -q '\.\.\.' $file; then
                if [ $mode = GUI ];then
                    sxiv "../filtered_scsht/${file%.hocr}.jpg" & SXIVPID=$!
                    if [ "$OSTYPE" = "linux-gnu" ]; then
                        while [ "$(xdotool getactivewindow)" = $Active ]; do
                            sleep 0.1
                        done
                        xdotool windowactivate $Active
                    fi
                    while true; do
                        read -p "$Question" oyn
                        case $oyn in
                            [OoYy]* ) sed -e 's/<em>/ItAlIk1/g' -e 's/<\/em>/ItAlIk2/g' $inplace $file; break;;
                            [Nn]* ) break;;
                            * ) echo "$BadAnswer";;
                        esac
                    done
                    kill $SXIVPID
                    wait $SXIVPID 2>/dev/null
                else
                    sed -e 's/<em>/ItAlIk1/g' -e 's/<\/em>/ItAlIk2/g' $inplace $file
                    echo "Vérifiez les balises italique à ${file%.hocr}" 
                fi
            else
                sed -e 's/<em>/ItAlIk1/g' -e 's/<\/em>/ItAlIk2/g' $inplace $file
            fi
        fi
        if grep -q '     </span>' $file; then
            sed $inplace 's/     <\/span>/     <\/span><br>/g' $file
        fi
        links -dump -codepage UTF-8 -force-html -width 512 $file > ${file%.hocr}.txt
    done

    final_check
}


final_check() {
## Vérification de la confidence OCR si Tesseract >= 3.03,
## ajout des retours Ã  la ligne si besoin,
## workaround bug "sous-titres vides" et suppresion de ceux restant
    [ $lang = fra ] && echo "Traitement des faux positifs et Suppression des sous-titres vides." || echo "Treat false positives and Delete empty subtitles."
    if (( $tess_version_num1 >= 4 || $tess_version_num2 >= 3 ));then
        ls *.txt |
        parallel $popt ocr {}

    else
        ls *.txt |
        parallel $popt ocr_legacy {}
    fi
    for file in *.txt; do
        if (( $(wc -l $file | awk '{print $1}') > 4 )); then
            tesseract ../filtered_scsht/${file%.txt}.jpg ${file%.txt} $tessdata -l $lang $oem $psm 7 2>/dev/null
            echo "" >> $file
        fi
    done # Workaround bug "psm" Tesseract, dangerous
}


ocr() {
    if [ "$(wc -c < $1)" = 0 ]; then
        OMP_THREAD_LIMIT=1 tesseract ../filtered_scsht/${1%.*}.jpg ${1%.*} $tessdata -l $lang $oem $psm 6 2>/dev/null
        if (( $(wc -c < $1) > 0 )); then
            echo "" >> $1
        else
            rm $1
        fi
    else
        n=$(grep -o x_wconf ${1%.*}.hocr | wc -l)
        j=$(cat ${1%.*}.hocr | grep -Po "x_wconf \K[^\'']*" | tr "\n" +)
        j=$((${j::-1}/$n))
        if (( $j >= 55 )); then
            echo "" >> $1
        else
            rm $1
        fi
    fi
}
export -f ocr


ocr_legacy() {
    if [ "$(wc -c < $1)" = 0 ]; then
        OMP_THREAD_LIMIT=1 tesseract ../filtered_scsht/${1%.*}.jpg ${1%.*} -l '$lang' '$oem' '$psm' 6 2>/dev/null
        if [ "$(wc -c < "$1")" = 0 ]; then
            rm $1
        fi
    else
        echo "" >> $1
    fi
}
export -f ocr_legacy


replace_quotes() {
    for file in tess_result/*.txt; do
        if grep -q \" $file; then
            if [ $OCRType = FineReader ]; then
                cat $file |
                iconv -f WINDOWS-1252 -t UTF-8 >> $file.tmp
                mv $file.tmp $file
            fi
            if [ "$(grep -o \" $file | wc -l)" = 1 ];then
                sed -e 's/"\. /â€¦ /g' -e 's/"\.$/â€¦/g' $inplace $file # Correction éventuelle
                sed -e 's/^"/« /' -e 's/"$/ »/' $inplace $file
            else
                while grep -q \" $file; do
                    sed '0,/"/{s/"/« /}' $file | sed '0,/"/{s/"/ »/}' > $file.tmp
                    mv $file.tmp $file
                done
            fi
            if [[ $OCRType = FineReader ]]; then
                cat $file |
                iconv -f UTF-8 -t WINDOWS-1252 >> $file.tmp
                mv $file.tmp $file
            fi
        fi
    done
}


convert_ocr() {
    rm "${filtered_video%.mp4}.srt" "${filtered_video%.mp4}_Alt.srt" 2>/dev/null
    i=0
    j=0
    for file in tess_result/*.txt; do 
        if [[ $file != *_Alt.txt ]];then
            i=$(($i + 1)); k=$i; Alt=""
        else
            j=$(($j + 1)); k=$j; Alt="_Alt"
        fi
        echo $k >> OCR$Alt.srt
        echo "$(basename $file $Alt.txt | sed -e 's/[hm]/_dp/g' -e 's/s/_v/g' -e 's/-/_t/g')" >> OCR$Alt.srt
        if [ $OCRType = Tesseract ];then
            cat $file >> OCR$Alt.srt
        else
            cat $file |
            iconv -f WINDOWS-1252 -t UTF-8 >> OCR$Alt.srt
            echo -e "\n\n" >> OCR$Alt.srt
        fi
    done

    if [ -f OCR_Alt.srt ]; then
        has_alt=true
        Alt="_Alt"
    else
        has_alt=false
        Alt=""
    fi
    sed $inplace 's/   //g' OCR.srt
    if $has_alt; then
        sed $inplace 's/   //g' OCR_Alt.srt
    fi
}


convert_italics() {
    if [ $OCRType = Tesseract ]; then
        for SRT in $(printf OCR%s.srt\\n "" $Alt); do {
            if grep -q 'ItAlIk' $SRT; then
                sed $inplace 's/\//l/g' $SRT # Autre correction éventuelle
                sed 's/ItAlIk2 ItAlIk1/ /g' $SRT |
                perl -0777 -pe 's/ItAlIk2\nItAlIk1/\n/igs' |
                sed 's/ItAlIk1\(.\)ItAlIk2/\1/g' |
                sed -e 's/ItAlIk1/<i>/g' -e 's/ItAlIk2/<\/i>/g' > $SRT.tmp
                mv $SRT.tmp $SRT
            fi
        } & done
        wait
    fi
}


correct_ocr() {
    for SRT in $(printf OCR%s.srt\\n "" $Alt); do
        sed $inplace 's/|/l/g' $SRT
        if [[ $lang = fra ]]; then
            sed -e "s/I'/l'/g" -e 's/iI /il /g' $SRT |
            sed 's/^\]/J/g' |
            sed 's/[®©]/O/g' |
            sed -e 's/\([cs]\)oeur/\1Å“ur/g' -e 's/oeuvre/Å“uvre/g' -e 's/oeuf/Å“uf/g' |
            sed "s/ *['â€˜]/â€™/g" |
            sed 's/\(.\)â€”\(.\)/\1-\2/g' |
            sed -e 's/<< /« /g' -e 's/ >>/ »/g' |
            sed 's/- /â€” /g' |
            sed 's/\.\.\./â€¦/g' |
            sed 's/â€¦\./â€¦/g' |
            sed 's/\([:;?\!]\)/ \1/g' | sed 's/  \([:;?\!]\)/ \1/g' |
            sed 's/ :2/ ?/g' |
            perl -0777 -pe 's/\n\n[0-9]\n\n/\n\n/igs' > $SRT.tmp
            #sed $inplace 's/___/â€¦/g' $SRT.tmp
            mv $SRT.tmp $SRT
        fi
        if [ $lang = eng ]; then
            sed -e 's/^l /I /g' -e 's/<i>l /<i>I /g' -e 's/ l / I /g' $inplace $SRT
        fi
    done
    wait
}

main() {
    ## Error handling 
    error_handling $@

    ## Prélude
    ## Initialisation
    init $@

    # Generate timecodes
    [ $lang = fra ] && echo "Génération des timecodes à partir de la Vidéo Filtrée." || echo "Generating timecodes from the Filtered Video."
    generate_timecodes

    ## Utilisation des timecodes pour générer les images à OCR
    [ $lang = fra ] && echo "Génération des Screenshots à partir de la Vidéo Filtrée." || echo "Generating Screenshots using the Filtered Video."
    generate_scsht

    ## Sélection du moteur OCR
    [ $lang = fra ] && echo "Selection du moteur d'OCR" || echo "Selecting OCR engine."
    ocr_select

    ## OCR d'un dossier avec Tesseract
    if [ $OCRType = Tesseract ]; then
        if [ $lang = fra ];then
            echo "OCR du dossier filtered_scsht avec Tesseract v${tess_version_num}."
            msg="Utilisation du moteur"
        else
            echo "OCR of the filtered_scsht directory with Tesseract v${tess_version_num}."
            msg="Using engine"
        fi
        ocr_tesseract
    fi

    ## OCR d'un dossier avec FineReader
    if [ $OCRType = FineReader ]; then
        if [ $lang = fra ];then
            echo "Une fois l'OCR par FineReader effectué, placez les fichiers dans le dossier tess_result et appuyez sur la touche de votre choix."
        else
            echo "When you're done with FineReader's OCR, put the files in the tess_result direcory and press the key of your choice."
        fi
        read answer
        case $answer in * ) ;; esac
    fi

    ## Remplacement anticipé des guillemets droits doubles ("...") en guillemets français doubles (« ... »)
    cd ..
    if [ $lang = fra ]; then
        replace_quotes
    fi
    
    ## Transformation du dossier OCR en srt (les timecodes seront reformatés plus tard)
    convert_ocr

    ## Conversion des tags "ItAlIk" en balises italiques SubRip
    [ $lang = fra ] && echo "Conversion des tags \"ItAlIk\" en balises italiques SubRip" || echo "Converting \"ItAlIk\" tags into SubRip italics tags"
    convert_italics

    ## Corrections OCR et normalisation
    [ $lang = fra ] && echo "Corrections OCR et normalisation" || echo "Correcting OCR and normalisation"
    correct_ocr

    ## Final
    for SRT in $(printf OCR%s.srt\\n "" $Alt); do
        sed -e 's/_t/ --> /' -e 's/_v/,/g' -e 's/_dp/:/g' $SRT > "${filtered_video%.*}${SRT#*OCR}"
        rm $SRT $SRT.bk 2>/dev/null
    done
    wait
}


main $@
