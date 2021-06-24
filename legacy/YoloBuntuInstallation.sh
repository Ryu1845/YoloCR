#!/bin/bash
##
## Script d'installation des prérequis du script YoloCR, pour Debian Stretch.
## Avec l'aimable participation de Cédric Villani et Nightwish : 
## http://www.huffingtonpost.fr/2015/05/07/cedric-villani-2025-plus-de-problemes-courage-fierte_n_7220124.html

release=$(lsb_release -a 2>&1 | grep Codename | cut -f2)
if [[ $release != focal ]]
	then if [[ $1 != eng-only ]]
		then echo "Ce script ne fonctionne que sur Ubuntu 20.04."
		else echo "This script only works on Ubuntu 20.04."
	fi; exit
fi

if (( $EUID == 0 ))
	then if [[ $1 != eng-only ]]
		then echo "Ce script ne doit pas être lancé en root."
		else echo "This script should not be run as root."
	fi; exit
fi

if [ ! -z $DISPLAY ]; then
	Desktop=$(grep DESKTOP /home/$USER/.config/user-dirs.dirs 2>/dev/null | cut -d/ -f2 | rev | cut -c 2- | rev)
	if [ -z $Desktop ]; then Desktop=Desktop; fi
	DesktopPkg="sxiv xdotool qtbase5-dev qt5-qmake libqt5websockets5-dev"
fi

sudo apt update
sudo apt install bc gawk curl tesseract-ocr imagemagick links parallel ffmpeg git build-essential autoconf automake libtool pkg-config python3-dev cython3 libffms2-4 libarchive-tools $DesktopPkg
if [[ $1 != eng-only ]]
	then sudo apt install tesseract-ocr-fra
		 wget https://github.com/tesseract-ocr/tessdata/blob/master/fra.traineddata?raw=true -O tessdata/fra.traineddata
	else wget https://github.com/tesseract-ocr/tessdata/blob/master/eng.traineddata?raw=true -O tessdata/eng.traineddata
fi
mkdir Gits; cd Gits

# Installation de zimg
git clone https://github.com/sekrit-twc/zimg.git; cd zimg
./autogen.sh && ./configure && make -j$(nproc)
sudo make install; cd ..

# Installation de Vapoursynth
git clone https://github.com/vapoursynth/vapoursynth.git; cd vapoursynth
./autogen.sh && ./configure && make -j$(nproc)
sudo make install; cd ..

# Installation de Vapoursynth Editor
if [ ! -z $DISPLAY ]; then
	git clone https://bitbucket.org/mystery_keeper/vapoursynth-editor.git; cd vapoursynth-editor/pro
	qmake -qt5 && make -j$(nproc); cd ..
	sudo cp build/release-64bit-gcc/vsedit /usr/local/bin/vsedit 
	sudo install -D build/release-64bit-gcc/vsedit.svg /usr/local/share/pixmaps/vsedit.svg
	if [ ! -d /usr/local/share/applications ]; then sudo mkdir /usr/local/share/applications; fi
	sudo wget https://gist.githubusercontent.com/YamashitaRen/4489ab810ee92f2fbbf7/raw/2ac6f4da0599d0b5e1166dd7458a689f8a5a2206/vsedit.desktop -P /usr/local/share/applications
	cp /usr/local/share/applications/vsedit.desktop /home/$USER/$Desktop/vsedit.desktop
	cd ..
fi

# Création du lien symbolique FFMS2 dans le dossier plugins de Vapoursynth
sudo ln -s $(dpkg-query -L libffms2-4 | grep libffms2.so | tail -1) /usr/local/lib/vapoursynth/libffms2.so

# Installation de HAvsFunc, mvsfunc et adjust
git clone https://github.com/HomeOfVapourSynthEvolution/havsfunc.git
git clone https://github.com/HomeOfVapourSynthEvolution/mvsfunc.git
git clone https://github.com/dubhater/vapoursynth-adjust.git
sudo cp havsfunc/havsfunc.py mvsfunc/mvsfunc.py vapoursynth-adjust/adjust.py /usr/local/lib/python3.8/site-packages/

# Installation de fmtconv
git clone https://github.com/EleonoreMizo/fmtconv.git; cd fmtconv; cd build/unix
./autogen.sh && ./configure --libdir=/usr/local/lib/vapoursynth && make -j$(nproc)
sudo make install; cd ../../..

# Installation de znedi3
git clone --recursive https://github.com/sekrit-twc/znedi3.git; cd znedi3
make -j$(nproc) X86=1
sudo cp vsznedi3.so /usr/local/lib/vapoursynth/; cd ..

# Installation de edi_rpow2
git clone https://gist.github.com/020c497524e794779d9c.git vapoursynth-edi_rpow2
sudo cp vapoursynth-edi_rpow2/edi_rpow2.py /usr/local/lib/python3.8/site-packages/edi_rpow2.py

# Vapoursynth doit fonctionner
if [[ $1 != eng-only ]]
	then echo -e '\n# Nécessaire pour Vapoursynth\nexport PYTHONPATH=/usr/local/lib/python3.8/site-packages' >> ~/.bashrc
	else echo -e '\n# Required for Vapoursynth\nexport PYTHONPATH=/usr/local/lib/python3.8/site-packages' >> ~/.bashrc
fi

# Éviter un reboot
sudo ldconfig
if [[ $1 != eng-only ]]
	then echo "Script d'installation terminé."
	else echo "Installation script finished."
fi
if [ ! -z $DISPLAY ]; then if [[ $1 != eng-only ]]
	then echo -e "Un raccourci pour Vapoursynth Editor a été créé sur le Bureau.\nNotez que les commandes "vsedit" et "vspipe" ne fonctionneront pas depuis le terminal actuel."
	else echo -e "A shortcut for Vapoursynth Editor had been created on the Desktop.\nNote that "vsedit" and "vspipe" commands will not work from current terminal."
fi; fi
