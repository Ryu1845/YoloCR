#!/bin/bash
##
## Script d'installation des prérequis du script YoloCR, pour Debian Stretch.
## Avec l'aimable participation de Cédric Villani et Nightwish : 
## http://www.huffingtonpost.fr/2015/05/07/cedric-villani-2025-plus-de-problemes-courage-fierte_n_7220124.html

release=$(lsb_release -a 2>&1 | grep Codename | cut -f2)
if [[ $release != stretch ]]
	then if [[ $1 != eng-only ]]
		then echo "Ce script ne fonctionne que sur Debian Stretch."
		else echo "This script only works on Debian Stretch."
	fi; exit
fi

if [[ $1 != eng-only ]]; then tesseractfra=tesseract-ocr-fra; fi
Desktop=$(grep DESKTOP /home/$USER/.config/user-dirs.dirs 2>/dev/null | cut -d/ -f2 | rev | cut -c 2- | rev)
if [ -z $Desktop ]; then Desktop=Desktop; fi

su -c "apt install bc gawk curl tesseract-ocr $tesseractfra links sxiv xdotool parallel ffmpeg git build-essential autoconf automake libtool pkg-config yasm python3-dev cython3 libffms2-4 bsdtar qtbase5-dev qt5-qmake libqt5websockets5-dev"
nasmurl=http://ftp.debian.org/debian/pool/main/n/nasm/
nasmdeb=$(links -dump $nasmurl | grep _amd64 | tail -1 | awk '{ print $3; }')
wget $nasmurl$nasmdeb; su -c "dpkg -i $nasmdeb"; rm $nasmdeb
mkdir Gits; cd Gits

# Installation de zimg
git clone https://github.com/sekrit-twc/zimg.git; cd zimg
git checkout v2.8
./autogen.sh && ./configure && make -j$(nproc)
su -c "make install"; cd ..

# Installation de Vapoursynth
git clone https://github.com/vapoursynth/vapoursynth.git; cd vapoursynth
git checkout R43
./autogen.sh && ./configure && make -j$(nproc)
su -c "make install"; cd ..

# Installation de Vapoursynth Editor
git clone https://bitbucket.org/mystery_keeper/vapoursynth-editor.git; cd vapoursynth-editor/pro
qmake -qt5 && make -j$(nproc); cd ..
su -c "cp build/release-64bit-gcc/vsedit /usr/local/bin/vsedit 
install -D build/release-64bit-gcc/vsedit.svg /usr/local/share/pixmaps/vsedit.svg
if [ ! -d /usr/local/share/applications ]; then mkdir /usr/local/share/applications; fi
wget https://gist.githubusercontent.com/YamashitaRen/4489ab810ee92f2fbbf7/raw/d38d73141eccafbeb936c9499fc3f10a885a3a42/vsedit.desktop -P /usr/local/share/applications"
cp /usr/local/share/applications/vsedit.desktop /home/$USER/$Desktop/vsedit.desktop
cd ..

# Création du lien symbolique FFMS2 dans le dossier plugins de Vapoursynth
su -c "ln -s $(dpkg-query -L libffms2-4 | grep libffms2.so | tail -1) /usr/local/lib/vapoursynth/libffms2.so"

# Installation de HAvsFunc, mvsfunc et adjust
git clone https://github.com/HomeOfVapourSynthEvolution/havsfunc.git
git clone https://github.com/HomeOfVapourSynthEvolution/mvsfunc.git
git clone https://github.com/dubhater/vapoursynth-adjust.git
su -c "cp havsfunc/havsfunc.py mvsfunc/mvsfunc.py vapoursynth-adjust/adjust.py /usr/local/lib/python3.5/site-packages/"

# Installation de fmtconv
git clone https://github.com/EleonoreMizo/fmtconv.git; cd fmtconv/build/unix
./autogen.sh && ./configure --libdir=/usr/local/lib/vapoursynth && make -j$(nproc)
su -c "make install"; cd ../../..

# Installation de znedi3
git clone --recursive https://github.com/sekrit-twc/znedi3.git; cd znedi3
make -j$(nproc) X86=1
su -c "cp vsznedi3.so /usr/local/lib/vapoursynth/"; cd ..

# Installation de edi_rpow2
git clone https://gist.github.com/020c497524e794779d9c.git vapoursynth-edi_rpow2
su -c "cp vapoursynth-edi_rpow2/edi_rpow2.py /usr/local/lib/python3.5/site-packages/edi_rpow2.py"

# Vapoursynth doit fonctionner
if [[ $1 != eng-only ]]
then echo -e '\n# Nécessaire pour Vapoursynth\nexport PYTHONPATH=/usr/local/lib/python3.5/site-packages' >> ~/.bashrc
else echo -e '\n# Required for Vapoursynth\nexport PYTHONPATH=/usr/local/lib/python3.5/site-packages' >> ~/.bashrc
fi

# Éviter un reboot
su -c "ldconfig"
if [[ $1 != eng-only ]]
then echo -e "Script installation terminé.\nUn raccourci pour Vapoursynth Editor a été créé sur le Bureau.\nNotez que les commandes "vsedit" et "vspipe" ne fonctionneront pas depuis le terminal actuel." 
else echo -e "Installation script finished.\nA shortcut for Vapoursynth Editor had been created on the Desktop.\nNote that "vsedit" and "vspipe" commands will not work from current terminal."
fi
