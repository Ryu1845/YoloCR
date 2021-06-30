# [YoloCR](https://bitbucket.org/YuriZero/yolocr/src)

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/f0a7a983688a4bfd920cc4d15562d350)](https://app.codacy.com/gh/Ryu1845/YoloCR?utm_source=github.com\&utm_medium=referral\&utm_content=Ryu1845/YoloCR\&utm_campaign=Badge_Grade_Settings)

I cleaned the vpy so they use a config file and are **somewhat** pep8 compliant and as such more readable.
This is a fork, for the original see the link in the title.
There's also a PKGBUILD, don't try to use it, it doesn't work

## For noobs

Install the requirements with the Ubuntu 20.04 (Focal Fossa) installation script.
You can install Ubuntu 20.04 inside a virtual machine like Virtualbox.

## Requirements

Global Requirements for all the OS.

### Global Requirements

*   ffmpeg

*   Vapoursynth R36+
    *   plugins for Vapoursynth:
        *   [FFMS2](https://github.com/FFMS/ffms2)
        *   [HAvsFunc](http://forum.doom9.org/showthread.php?t=166582), requires [mvsfunc](http://forum.doom9.org/showthread.php?t=172564) and [adjust](https://github.com/dubhater/vapoursynth-adjust)
        *   [fmtconv](http://forum.doom9.org/showthread.php?t=166504)
        *   *optional*: [edi_rpow2](http://forum.doom9.org/showthread.php?t=172652), requires [znedi3](https://github.com/sekrit-twc/znedi3)
        *   *very optional*: [Waifu2x-w2xc](http://forum.doom9.org/showthread.php?t=172390)
    *   note:

        *   Vapoursynth plugins (.so on Unix, .dll on Windows) should be placed inside one of theses directories: <http://www.vapoursynth.com/doc/autoloading.html>
        *   Vapoursynth scripts (.py) should be placed inside the "site-packages" directory of your Python3 installation.

    *   [Vapoursynth Editor](https://bitbucket.org/mystery_keeper/vapoursynth-editor)

### Unix/Linux Requirements

*   Tesseract-OCR (>=4)
    *   and install the data corresponding to the languages you want to OCR

*   Imagemagick

> *Note*: most of these package, with the exception of all the plugins for vapoursynth, are available as official package for your distro.
> For Ubuntu 20.04, all the requirements can be installed with the YoloBuntuInstallation script : `sh YoloBuntuInstallation.sh eng-only`
> For Ubuntu, *vapoursynth*, *vapoursynth-editor* and  *vapoursynth-extra-plugins* (to install all the mandatory plugins above) are available through this ppa: [`ppa:djcj/vapoursynth`](https://launchpad.net/~djcj/+archive/ubuntu/vapoursynth)

### Windows Requirements

*   [Cygwin](https://www.cygwin.com/). During the install, activate:
    *   bc
    *   gnupg
    *   make
    *   perl
    *   wget
    *   tesseract-ocr
    *   tesseract-ocr-eng

> *Note*: Cygwin terminal usage here → <https://help.ubuntu.com/community/UsingTheTerminal>
> C drive path is "/cygdrive/c".
> Scripts have to be used within Cygwin terminal.
> If you use Windows 10, you can install BashOnWindows instead of Cygwin.

## How to use

### Help for determining the parameters for the config file

#### Determine the Resize parameters

Resize is very helpful to locate the subtitles.

1.  open the config file in a text editor

2.  open `YoloResize.py` in Vapoursynth Editor.

3.  Change these values in the config:
    *   `source_file` is the path of the video to OCR.
    *   `crop_box_dimension` allows you to limit the OCR zone.
    *   `crop_box_height` allows you to define the height of the Cropbox's bottom border.

> Note that theses two parameters have to be adjusted before upscale.

You can then change `supersampling_factor` parameter to -1 and verify that your subtitles aren't eated by the white borderline by using **F5**.

#### Determine the threshold of the subtitles

This part is made to improve the OCR process and the subtitles detection.

1.  Open `YoloSeuil.py` in Vapoursynth editor.
2.  Choose the fitting threshold_mode. 'L' if you want to define a white or black threshold, succesively 'R', 'G' and 'B' otherwise.
3.  Adjust the Threshold with the help of the "Color Panel" found in the **F5** window.

You must to do this two times if you are using threshold_mode="L":

*   in the first case, the Inline threshold will be the minimum.
*   in the second case, the Outline threshold will be the maximum.

You can then change `threshold` paremeter to the values previously found.

*   in the first case, the subtitles must remain completely visible. The highest the value, the better.
*   in the second case, the Outline must remain completely black. The lowest the value, the better.

### Filter the video + OCR

1.  Edit `inline_threshold` and `outline_threshold` thanks to the two previous steps
    *   `inline_threshold` = the inline threshold value (decrease it if it improves the clarity of the letters)
    *   `outline_threshold` = the outline threshold value (increase it if some letters got erased)

2.  Then filter it: `vspipe -y yolocr/YoloCR.py . -p`

> You can use `yolocr/yolocr-cli.py` to set the values while also executing the script
> You can use `YoloTime.sh` instead of `yolocr.py` if you only want the Timing of the subtitles. **NOT SUPPORTED ANYMORE**

**Now it's Checking time :D**

## Serial use of YoloCR

1.  Make sure that the directory you're in includes the video files you want to OCR and only theses.

2.  Move to the YoloCR directory and use this bash command:
    *   `for file in *.mp4; do ./yolocr/yolocr-cli.py -f "$file" -l eng; done`

> "\*.mp4" means that all files having the mp4 extension will be processed. You can change eng for the language you want. Read about bash regex if you want more flexibility.
