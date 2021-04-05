import sys
import pytesseract
import logging
import os
import shutil


logging.basicConfig(level=logging.DEBUG)
try:
    LANG = sys.argv[2]
except IndexError:
    logging.info("Language not defined. Defaulting to English")
    LANG = "eng"

try:
    FILTERED_VIDEO = sys.argv[1]
except IndexError:
    if LANG == "fra":
        raise IndexError(
            f"""
N'oubliez pas de mettre le nom de la Vidéo Filtrée en argument.
Exemple : {sys.argv[0]} Vidéo_Filtrée.mp4 {LANG}
            """
        )
    raise IndexError(
        f"""
Don't forget to put the name of the filtered video in the arguments
Example : {sys.argv[0]} filtered_video.mp4 {LANG}
        """
    )

try:
    os.mkdir("filtered_scsht")
except FileExistsError:
    shutil.rmtree("filtered_scsht")
    os.mkdir("filtered_scsht")

try:
    os.mkdir("tess_result")
except FileExistsError:
    shutil.rmtree("tess_result")
    os.mkdir("tess_result")

has_alt = os.path.exists("scene_changes_alt.log")

if LANG == "fra":
    logging.info("Utilisation de YoloCR en mode CLI.")
    print("Prélude")
else:
    logging.info("Using YoloCR in CLI mode.")
    print("Prelude")


def convert_secs(rough_time: str) -> None:
    secs = int(rough_time.split(".")[0])
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    ms = int(rough_time.split(".")[1])
    print(f"{h:02}{m:02}{s:02}{ms:03}")