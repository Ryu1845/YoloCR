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

if [[ ! $(ls havsfunc*.7z 2> /dev/null) || ! -f scenechange-0.2.0-2.7z ]]
	then if [[ $1 != eng-only ]]
		then echo "Avant toute chose, téléchargez les archives des dernières versions de HAvsFunc et SceneChange et placez-les dans le même dossier que ce script. Inutile de les extraire."
		else echo "First, download latest archives of HAvsFunc and SceneChange and put them in the same directory as this script. Don't bother extracting them."
	fi; echo -e "http://forum.doom9.org/showthread.php?t=166582\nhttp://forum.doom9.org/showthread.php?t=166769"; exit
fi

if [[ $EUID -ne 0 ]]
	then if [[ $1 != eng-only ]]
		then echo "Ce script doit être lancé avec les droits super-utilisateur."
		else echo "This script needs root rights."
	fi; exit
fi

if [[ $1 != eng-only ]]; then tesseractfra=tesseract-ocr-fra; fi
Username=$(echo $(realpath ./) | cut -d'/' -f 3)
Desktop=$(grep DESKTOP /home/$Username/.config/user-dirs.dirs | cut -d/ -f2 | rev | cut -c 2- | rev)
if [ -z $Desktop ]; then Desktop=Desktop; fi

if [[ $release = jessie && ! $(apt-cache policy | grep "Unofficial Multimedia Packages") ]]
	then echo -e "\n#Marillat\ndeb http://www.deb-multimedia.org jessie main non-free" >> /etc/apt/sources.list
	apt update && apt install deb-multimedia-keyring
	apt update && apt dist-upgrade
fi
apt install tesseract-ocr $tesseractfra links sxiv xdotool parallel ffmpeg git build-essential autoconf automake libtool libavcodec-dev libswscale-dev yasm python3-dev cython3 libffms2-3 bsdtar qtbase5-dev qt5-qmake
su -c "mkdir Gits" $Username; cd Gits

# Installation de Vapoursynth
su -c "git clone https://github.com/vapoursynth/vapoursynth.git" $Username; cd vapoursynth
su -c "./autogen.sh && ./configure --disable-assvapour --disable-ocr && make" $Username
make install; cd ..

# Création du lien symbolique FFMS2 dans le dossier plugins de Vapoursynth
ln -s $(dpkg-query -L libffms2-3 | tail -1) /usr/local/lib/vapoursynth/libffms2.so

# Installation du plugin GenericFilters
su -c "git clone https://github.com/myrsloik/GenericFilters.git" $Username; cd GenericFilters/src
su -c "./configure && make" $Username
make install; cd ../..

# Installation de HAvsFunc
cd ..
su -c "bsdtar -xf $(ls havsfunc*.7z)" $Username && rm havsfunc*.7z
cp havsfunc.py /usr/local/lib/python3.4/site-packages/havsfunc.py

# Installation de SceneChange
su -c "mkdir SceneChange; mv scenechange-0.2.0-2.7z SceneChange/scenechange-0.2.0-2.7z" $Username; cd SceneChange
su -c "bsdtar -xf scenechange-0.2.0-2.7z" $Username && rm scenechange-0.2.0-2.7z
for i in {10..15}; do sed -i "${i}s/^/#/" src/compile.sh; done
for i in {18..24}; do sed -i "${i}s/#//" src/compile.sh; done
su -c "cd src && sh compile.sh" $Username
cp src/libscenechange.so src/libtemporalsoften2.so /usr/local/lib/vapoursynth/
cd ../Gits

# Installation de fmtconv
su -c "git clone https://github.com/EleonoreMizo/fmtconv.git" $Username; cd fmtconv/build/unix
su -c "./autogen.sh && ./configure --libdir=/usr/local/lib/vapoursynth && make" $Username
make install; cd ../../..

# Installation de nnedi3
su -c "git clone https://github.com/dubhater/vapoursynth-nnedi3.git" $Username; cd vapoursynth-nnedi3
su -c "./autogen.sh && ./configure --libdir=/usr/local/lib/vapoursynth && make" $Username
make install; cd ..

# Installation de nnedi3_rpow2
su -c "git clone https://gist.github.com/020c497524e794779d9c.git vapoursynth-nnedi3_rpow2" $Username
cp vapoursynth-nnedi3_rpow2/nnedi3_rpow2.py /usr/local/lib/python3.4/site-packages/nnedi3_rpow2.py

# Installation de zimg
su -c "git clone https://github.com/sekrit-twc/zimg.git" $Username; cd zimg
su -c "./autogen.sh && ./configure --libdir=/usr/local/lib/vapoursynth && make" $Username
make install; cd ..

# Installation de Vapoursynth Editor
su -c "git clone https://bitbucket.org/mystery_keeper/vapoursynth-editor.git" $Username; cd vapoursynth-editor/pro
su -c "qmake -qt5 && make" $Username
cd ..; cp build/release-64bit-gcc/vsedit /usr/local/bin/vsedit
mkdir -p /usr/local/share/pixmaps && cp build/release-64bit-gcc/vsedit.svg $_/vsedit.svg
mkdir -p /usr/local/share/applications && wget https://gist.githubusercontent.com/YamashitaRen/4489ab810ee92f2fbbf7/raw/d38d73141eccafbeb936c9499fc3f10a885a3a42/vsedit.desktop -P $_
su -c "cp /usr/local/share/applications/vsedit.desktop /home/$Username/$Desktop/vsedit.desktop" $Username

# Vapoursynth doit fonctionner
if [[ $1 != eng-only ]]
then su -c "echo -e '\n# Nécessaire pour Vapoursynth\nexport PYTHONPATH=/usr/local/lib/python3.4/site-packages' >> /home/$Username/.bashrc" $Username
else su -c "echo -e '\n# Required for Vapoursynth\nexport PYTHONPATH=/usr/local/lib/python3.4/site-packages' >> /home/$Username/.bashrc" $Username
fi

# Éviter un reboot
ldconfig
if [[ $1 != eng-only ]]
then echo -e "Script installation terminé.\nUn raccourci pour Vapoursynth Editor a été créé sur le Bureau.\nNotez que les commandes "vsedit" et "vspipe" ne fonctionneront pas depuis le terminal actuel." 
else echo -e "Installation script finished.\nA shortcut for Vapoursynth Editor had been created on the Desktop.\nNote that "vsedit" and "vspipe" commands will not work from current terminal."
fi
