[yoloCR](http://gogs.seigi.tk/Yuri/YoloCR/)
========

Requirements
--------

Global Requirements for all the OS.

### Global Requirements

* ffmpeg
* Vapoursynth R27+
    * plugins for Vapoursynth : [FFMS2](https://github.com/FFMS/ffms2), [HAvsFunc](http://forum.doom9.org/showthread.php?t=166582), [SceneChange](http://forum.doom9.org/showthread.php?t=166769), [fmtconv](http://forum.doom9.org/showthread.php?t=166504), [nnedi3](http://forum.doom9.org/showthread.php?t=166434)
 * [Vapoursynth Editor](https://bitbucket.org/mystery_keeper/vapoursynth-editor)

### Unix/Linux Requirements

* plugin for Vapoursynth : [GenericFilters](https://github.com/myrsloik/GenericFilters)
* Tesseract-OCR (we recommand version 3.03+)
  * and install the language package `eng` or `fra` too
* links
* sxiv (Simple X Image Viewer)
* xdotool (Linux only)
* parallel (GNU Parallel)

>*Note*: most of these package, with the exception of all the plugins for vapoursynth, are available as official package for your distro.
><br>For Ubuntu, adding the ppa: [`ppa:djcj/vapoursynth`](https://launchpad.net/~djcj/+archive/ubuntu/vapoursynth) is recommended to install *vapoursynth*, *vapoursynth-editor*, and  *vapoursynth-extra-plugins* (to install all the plugins above)

### Windows Requirements

* [Tesseract](https://code.google.com/p/tesseract-ocr/downloads/detail?name=tesseract-ocr-setup-3.02.02.exe)
  * and install the language package `eng` or `fra` too.
* [Cygwin](https://www.cygwin.com/). During the install, activate: 
  * gnupg
  * wget
  * perl
  * bc
  * links

* Install `GNU Parallel` from the Cygwin terminal:
  * `wget -O - pi.dk/3 | bash`
  * `mv ~/bin/parallel /usr/local/bin/`

>*Note*: Cygwin terminal usage here → [https://help.ubuntu.com/community/UsingTheTerminal](https://help.ubuntu.com/community/UsingTheTerminal)
><br>C drive path is "/cygdrive/c".
><br>Scripts have to be used within Cygwin terminal.

How to use?
----------

### Help for determining the parameters for the `YoloCR.vpy` file

#### Determine the Resize parameters.

Resize is very helpful to locate the subtitles.
*First, open `YoloResize.vpy` in Vapoursynth Editor.
  * `FichierSource` is the path of the video to OCR. Don't forget the apostrophes.
	* `DimensionCropbox` allows you to limit the OCR zone.
	* `HauteurCropBox` allows you to define the height of the Cropbox's bottom border.
	<br>> Note that theses two parameters have to be adjusted before upscale.
	<br>You can then change `Supersampling` parameter to -1 and verify that your subtitles aren't eated by the white borderline by using **F5**.

#### Determine the threshold of the subtitles

It's to improve the OCR-process and the subtitles detection.
* Open `YoloSeuil.vpy` in Vapoursynth editor.
  * Report `FichierSource`, `DimensionCropBox` and `HauteurCropBox` you have defined in the `Resize` file.
  * Choose the fitting ModeS. 'L' if you want to define a white or black threshold, succesively 'R', 'G' and 'B' otherwise.
	* Adjust the Threshold by using **F5**.

> Inline threshold have to be as high as possible, but subtitles must remain completely visible.
> <br>Outline threshold have to be as low as possible, but outline must remain fully black.

### Filter the video

First, you'll have to filter the video with Vapoursynth. 
  * Edit the first lines in `YoloCR.vpy` thanks to the two previos steps (and the previous file `YoloSeuil.vpy`).
 
Then filter it: `vspipe -y YoloCR.vpy - | ffmpeg -i - -c:v mpeg4 -qscale:v 3 -y nameOftheVideoOutput.mp4`
>Be careful: your must use a different name for your `FichierSource` in the previous files and `nameOftheVideoOutput.mp4` for the output of the ffmpeg command.

You now have an OCR-isable video and scenechange informations.

### OCR the video

Then you can OCR the video.
`./YoloCR.sh nameOftheVideoOutput.mp4`
> The `nameOftheVideoOutput.mp4` must be the same than the output of the ffmpeg command.

**Now it's Checking time :D**

Contact: [irc://irc.rizon.net/seigi-fr](irc://irc.rizon.net/seigi-fr)

