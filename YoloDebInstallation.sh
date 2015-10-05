#!/bin/bash
##
## Script d'installation des prérequis du script YoloCR, pour Debian Jessie et LMDE Betsy
## Avec l'aimable participation de Cédric Villani et Nightwish : 
## http://www.huffingtonpost.fr/2015/05/07/cedric-villani-2025-plus-de-problemes-courage-fierte_n_7220124.html

release=$(lsb_release -a 2>&1 | grep Codename | cut -f2)
if [[ $release != jessie && $release != betsy ]]
	then if [[ $1 != eng-only ]]
		then echo "Ce script ne fonctionne que sur Debian Jessie et LMDE Betsy."
		else echo "This script only works on Debian Jessie and LMDE Betsy."
	fi; exit
fi

if [[ $1 != eng-only ]]; then tesseractfra=tesseract-ocr-fra; fi
Desktop=$(grep DESKTOP /home/$USER/.config/user-dirs.dirs 2>/dev/null | cut -d/ -f2 | rev | cut -c 2- | rev)
if [ -z $Desktop ]; then Desktop=Desktop; fi

if [[ $release = jessie && ! $(apt-cache policy | grep "Unofficial Multimedia Packages") ]]; then
	su -c "echo -e '\n#Marillat\ndeb http://www.deb-multimedia.org jessie main non-free' >> /etc/apt/sources.list
	apt update; apt install deb-multimedia-keyring
	apt update; apt dist-upgrade"
fi
su -c "apt install curl tesseract-ocr $tesseractfra links sxiv xdotool parallel ffmpeg git build-essential autoconf automake libtool libavcodec-dev libswscale-dev yasm python3-dev cython3 libffms2-3 bsdtar qtbase5-dev qt5-qmake"
mkdir Gits; cd Gits

# Téléchargement de Plowshare
git clone https://github.com/mcrapet/plowshare.git
plowshare/src/mod.sh --install

# Installation de Vapoursynth
git clone https://github.com/vapoursynth/vapoursynth.git; cd vapoursynth
./autogen.sh && ./configure --disable-assvapour --disable-ocr && make
su -c "make install"; cd ..

# Création du lien symbolique FFMS2 dans le dossier plugins de Vapoursynth
su -c "ln -s $(dpkg-query -L libffms2-3 | tail -1) /usr/local/lib/vapoursynth/libffms2.so"

# Installation du plugin GenericFilters
git clone https://github.com/myrsloik/GenericFilters.git; cd GenericFilters/src
./configure && make
su -c "make install"; cd ../..

# Installation de HAvsFunc
cd ..
Gits/plowshare/src/download.sh $(links -dump http://forum.doom9.org/archive/index.php/t-166582.html | grep mediafire | head -1 | cut -d'(' -f2 | cut -d')' -f1)
bsdtar -xf $(ls havsfunc*.7z) && rm havsfunc*.7z
su -c "cp havsfunc.py /usr/local/lib/python3.4/site-packages/havsfunc.py"

# Installation de SceneChange
mkdir SceneChange; cd $_
../Gits/plowshare/src/download.sh http://www.mediafire.com/download.php?dnld4p98i333idp
bsdtar -xf scenechange-0.2.0-2.7z && rm scenechange-0.2.0-2.7z
for i in {10..15}; do sed -i "${i}s/^/#/" src/compile.sh; done
for i in {18..24}; do sed -i "${i}s/#//" src/compile.sh; done
cd src && sh compile.sh
su -c "cp libscenechange.so libtemporalsoften2.so /usr/local/lib/vapoursynth/"
cd ../../Gits

# Installation de fmtconv
git clone https://github.com/EleonoreMizo/fmtconv.git; cd fmtconv/build/unix
./autogen.sh && ./configure --libdir=/usr/local/lib/vapoursynth && make
su -c "make install"; cd ../../..

# Installation de nnedi3
git clone https://github.com/dubhater/vapoursynth-nnedi3.git; cd vapoursynth-nnedi3
./autogen.sh && ./configure --libdir=/usr/local/lib/vapoursynth && make
su -c "make install"; cd ..

# Installation de nnedi3_rpow2
git clone https://gist.github.com/020c497524e794779d9c.git vapoursynth-nnedi3_rpow2
su -c "cp vapoursynth-nnedi3_rpow2/nnedi3_rpow2.py /usr/local/lib/python3.4/site-packages/nnedi3_rpow2.py"

# Installation de zimg
git clone https://github.com/sekrit-twc/zimg.git; cd zimg
./autogen.sh && ./configure --libdir=/usr/local/lib/vapoursynth --enable-x86simd && make
su -c "make install"; cd ..

# Installation de Vapoursynth Editor
git clone https://bitbucket.org/mystery_keeper/vapoursynth-editor.git; cd vapoursynth-editor/pro
qmake -qt5 && make; cd ..
su -c "cp build/release-64bit-gcc/vsedit /usr/local/bin/vsedit 
install -D build/release-64bit-gcc/vsedit.svg /usr/local/share/pixmaps/vsedit.svg
mkdir /usr/local/share/applications && wget https://gist.githubusercontent.com/YamashitaRen/4489ab810ee92f2fbbf7/raw/d38d73141eccafbeb936c9499fc3f10a885a3a42/vsedit.desktop -P /usr/local/share/applications"
cp /usr/local/share/applications/vsedit.desktop /home/$USER/$Desktop/vsedit.desktop

# Vapoursynth doit fonctionner
if [[ $1 != eng-only ]]
then echo -e '\n# Nécessaire pour Vapoursynth\nexport PYTHONPATH=/usr/local/lib/python3.4/site-packages' >> ~/.bashrc
else echo -e '\n# Required for Vapoursynth\nexport PYTHONPATH=/usr/local/lib/python3.4/site-packages' >> ~/.bashrc
fi

# Éviter un reboot
su -c "ldconfig"
if [[ $1 != eng-only ]]
then echo -e "Script installation terminé.\nUn raccourci pour Vapoursynth Editor a été créé sur le Bureau.\nNotez que les commandes "vsedit" et "vspipe" ne fonctionneront pas depuis le terminal actuel." 
else echo -e "Installation script finished.\nA shortcut for Vapoursynth Editor had been created on the Desktop.\nNote that "vsedit" and "vspipe" commands will not work from current terminal."
fi
