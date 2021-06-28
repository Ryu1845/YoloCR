#!/usr/bin/env python3
"OCR part of the YoloCR toolkit"
import logging
import os
from concurrent.futures import ThreadPoolExecutor
import re
import shutil
import subprocess
import sys

from helpers import convert_secs, In_dir, negate_images
from tqdm import tqdm
import tesserocr

logging.basicConfig(format="%(message)s\n", level=logging.INFO)
logging.debug("Logging in DEBUG")

try:
    _tess_ver_proc = subprocess.check_output(["tesseract", "-v"])
except FileNotFoundError:
    raise ProcessLookupError("Tesseract not found, please install")
TESS_VER_NUM = re.findall(r"\d+\.\d+\.\d+", str(_tess_ver_proc))[0]
logging.debug(f"Using Tesseract version {TESS_VER_NUM}")


def generate_timecodes(
    scn_chglog: str,
    video: str,
) -> list:
    """
    Generate timecodes from the scene changes frame values
    Parameters
    ----------
    scn_chglog:
        path of scene changelog
    video:
    """
    logging.info("Generating Timecodes")
    args = [
        "ffprobe",
        video,
        "-v",
        "0",
        "-select_streams",
        "v",
        "-print_format",
        "flat",
        "-show_entries",
        "stream=r_frame_rate",
    ]
    output_ffprobe = subprocess.check_output(args)
    output_digits = re.findall(r"\d+", str(output_ffprobe))
    fps = int(output_digits[1]) / int(output_digits[2])
    logging.info(f"The video framerate is {fps}")

    with open(scn_chglog, "r") as scene_changes_io:
        timecodes = []
        frames = scene_changes_io.readlines()
        # TODO treat numbers properly
        for line in frames:
            if int(line.split(" ")[2]) == 0:
                timecodes.append(float(f"{float(line.split(' ')[0])/fps:.4f}"[:-1]))
            elif int(line.split(" ")[1]) == 0:
                timecodes.append(float(f"{(float(line.split(' ')[0])+1)/fps:.4f}"[:-1]))

    timecodes.sort(key=float)
    return timecodes


def gen_scsht(
    frame_time: tuple,
    video: str,
    scsht_pth: str,
) -> None:
    """
    Screenshot a list of timecode asynchronously
    Parameters
    ----------
    frame_time:
        frame time of the frame you want to screenshot
    video:
        path of the video to screenshot
    scsht_pth:
        path to save the screenshots in
    """
    even, odd, frame_time = frame_time
    image = f"{scsht_pth}/{convert_secs(even)}-{convert_secs(odd)}.jpg"
    cmd = [
        "ffmpeg",
        "-ss",
        str(frame_time),
        "-i",
        video,
        "-vframes",
        "1",
        "-loglevel",
        "error",
        image,
    ]
    _ = subprocess.run(cmd)


def gen_frame_times(timecodes: list) -> list:
    """
    Generate a list of tuples of frame_times based on the timecodes
    Parameters
    ----------
    timecodes:
        the list of scene changes timecodes
    Returns
    -------
    frame_times:
        list of tuples for the OCR
    """
    # TODO ALT
    logging.info("Generating Screenshots")

    frame_times = []
    logging.debug(len(timecodes))
    timecodes = list(set(timecodes))[1:]
    timecodes.sort(key=float)
    logging.debug(len(timecodes))
    for idx, timecode in enumerate(timecodes):
        if idx % 2 == 0:
            even = timecode
        else:
            odd = timecode
            frame_time = f"{(even + odd) / 2:.3f}"
            frame_times.append((even, odd, frame_time))
    logging.debug(len(frame_times))
    return frame_times


def delete_black_frames(path: str) -> None:
    """
    Delete black frames in a directory
    Parameters
    ----------
    path:
        directory to delete the frames from
    """
    with In_dir(path):
        cmd = [
            "ffmpeg",
            "-loglevel",
            "error",
            "-i",
            os.listdir()[0],
            "-filter:v",
            "colorchannelmixer=rr=0:gg=0:bb=0",
            "-pix_fmt",
            "yuvj420p",
            "black_frame.jpg",
        ]
        _ = subprocess.run(cmd)
        black_frame_size = os.path.getsize("black_frame.jpg")
        prev = len(os.listdir())
        for file in os.listdir():
            if os.path.getsize(file) == black_frame_size:
                os.remove(file)
        new = len(os.listdir())
        logging.debug(f"deleted {prev - new}")


def ocr(
    frame: str,
    tess_result_pth: str,
    lang: str,
    tess_data: str,
) -> None:
    """
    Perform OCR on an image
    Parameters
    ----------
    frame:
        path of the frame to ocr
    tess_result_pth:
        path of the results
    lang:
        language of the text
    tess_data:
        tessdata path for tesseract
    """
    path = tess_result_pth + "/" + os.path.basename(frame).replace(".jpg", ".txt")
    with open(path, "w") as txt_io:
        if tess_data:
            txt_io.write(
                tesserocr.file_to_text(
                    frame, psm=tesserocr.PSM.SINGLE_BLOCK, lang=lang, path=tess_data
                )
            )
        else:
            txt_io.write(
                tesserocr.file_to_text(frame, psm=tesserocr.PSM.SINGLE_BLOCK, lang=lang)
            )


def italics_verification(lang: str) -> None:
    """
    Convert Markdown italics to HTML italics
    Parameters
    ----------
    lang:
        language of the OCR
    """
    logging.info(
        "Vérification de l'OCR italique"
        if lang == "fra"
        else "Verifying the italics OCR"
    )
    for file in os.listdir():
        if ".txt" in file:
            lines_i = list()
            with open(file, "r") as file_io:
                lines = file_io.readlines()
                for line in lines:
                    for idx, _ in enumerate(re.findall("_", line)):
                        if idx % 2:
                            line = re.sub("_", "</i>", line)
                        else:
                            line = re.sub("_", "<i>", line)
                    lines_i.append(line)
            with open(file, "w") as file_io:
                file_io.writelines(lines_i)


def check(lang: str) -> None:
    """
    Delete false and empty subtitles
    Parameters
    ----------
    lang:
        language of the OCR
    """
    logging.info(
        "Traitement des faux positifs et Suppression des sous-titres vides."
        if lang == "fra"
        else "Treating false positives and Deleting empty subtitles."
    )
    # reversing list so it checks txt before hocr and doesn't try to open a deleted file
    listdir = os.listdir()
    listdir.sort()
    listdir = listdir[::-1]
    for file in listdir:
        with open(file, "r") as file_io:
            lines = file_io.readlines()
            confidences = list()
            for line in lines:
                confidence = re.findall(r"x_wconf \d+", line)
                if len(confidence) > 0:
                    confidence_int = int(re.findall(r"\d+", confidence[0])[0])
                    confidences.append(confidence_int)
            final_confidence = (
                sum(confidences) / len(confidences) if len(confidences) > 0 else 100
            )
        if not lines or final_confidence < 55:
            txt_file = file.replace(".hocr", ".txt")
            try:
                logging.debug(
                    f"Deleting {txt_file}, tesseract confidence {final_confidence}"
                )
                os.remove(txt_file)
            except FileNotFoundError:
                logging.debug(f"Cannot delete {txt_file}, it's already deleted")


def convert_ocr(
    sub_filename: str,
    tess_result_pth: str,
) -> None:
    """
    Assemble the different text files into an SRT subtitle file
    Parameters
    ----------
    sub_filename:
        name of the final file
    tess_result_pth:
        path of the results of the OCR
    """
    logging.info("Converting OCR to srt")
    try:
        os.remove(sub_filename + ".srt")
    except FileNotFoundError:
        logging.debug("subtitle files didn't exist before")

    with In_dir(tess_result_pth):
        i = 0
        list_sub = os.listdir()
        list_sub.sort()
        for file in list_sub:
            if ".txt" in file:
                i += 1
                k = i
                with open(file, "r") as file_io:
                    lines = file_io.readlines()
                with open(f"../../{sub_filename}.srt", "a") as ocr_io:
                    ocr_io.write(str(k) + "\n")
                    sub_time = os.path.basename(file)
                    sub_time = re.sub("[hm]", ":", sub_time)
                    sub_time = re.sub("s", ",", sub_time)
                    sub_time = re.sub("-", " --> ", sub_time)
                    sub_time = re.sub(".txt", "", sub_time)
                    ocr_io.write(sub_time + "\n")
                    ocr_io.writelines(lines)
                    ocr_io.write("\n\n")

    lines_new = list()
    with open(f"{sub_filename}.srt", "r") as ocr_io:
        lines = ocr_io.readlines()
        for line in lines:
            line = re.sub(r"   ", "", line)
            lines_new.append(line)
    with open(f"{sub_filename}.srt", "w") as ocr_io:
        ocr_io.writelines(lines_new)


def main(lang: str, filtered_video: str) -> None:
    """
    Execute the process
    Parameters
    ----------
    lang:
        language of the OCR
    filtered_video:
        video to OCR
    """
    scsht_pth = "data/filtered_scsht"
    tess_result_pth = "data/tess_result"
    tess_data_pth = "data/tessdata"
    try:
        os.mkdir(scsht_pth)
    except FileExistsError:
        shutil.rmtree(scsht_pth)
        os.mkdir(scsht_pth)

    try:
        os.mkdir(tess_result_pth)
    except FileExistsError:
        shutil.rmtree(tess_result_pth)
        os.mkdir(tess_result_pth)

    has_alt = os.path.exists("data/scene_changes_alt.log")
    timecodes = generate_timecodes("data/scene_changes.log", filtered_video)
    if has_alt:
        timecodes_alt = generate_timecodes("data/scene_changes_alt.log", filtered_video)
        gen_frame_times(timecodes_alt)
        frame_times = gen_frame_times(timecodes_alt)
        with ThreadPoolExecutor() as executor:
            list(
                tqdm(
                    executor.map(
                        gen_scsht,
                        frame_times,
                        [filtered_video] * len(frame_times),
                        [scsht_pth] * len(frame_times),
                    ),
                    total=len(frame_times),
                )
            )
    frame_times = gen_frame_times(timecodes)
    with ThreadPoolExecutor() as executor:
        list(
            tqdm(
                executor.map(
                    gen_scsht,
                    frame_times,
                    [filtered_video] * len(frame_times),
                    [scsht_pth] * len(frame_times),
                ),
                total=len(frame_times),
            )
        )

    delete_black_frames(scsht_pth)
    if os.path.exists(f"{tess_data_pth}/{lang}.traineddata"):
        tess_data = os.path.abspath(tess_data_pth)
    else:
        tess_data = None

    logging.info("Using LSTM engine")

    logging.info("Negating images to Black over White")

    with In_dir(scsht_pth):
        negate_images(os.listdir())

    logging.info("Images OCR")
    os.environ["OMP_THREAD_LIMIT"] = "1"
    screenshots = [os.path.join(scsht_pth, file) for file in os.listdir(scsht_pth)]
    with ThreadPoolExecutor() as executor:
        list(
            tqdm(
                executor.map(
                    ocr,
                    screenshots,
                    [tess_result_pth] * len(screenshots),
                    [lang] * len(screenshots),
                    [tess_data] * len(screenshots),
                ),
                total=len(screenshots),
            )
        )
    italics_verification(lang)
    # check(lang=lang) # actually makes too many false negative
    convert_ocr(filtered_video.removesuffix(".mp4"), tess_result_pth)
    if has_alt:
        convert_ocr(filtered_video.replace(".mp4", "_alt"), tess_result_pth)


if __name__ == "__main__":
    try:
        lang = sys.argv[2]
    except IndexError:
        logging.info("Language not defined. Defaulting to English")
        lang = "eng"

    try:
        filtered_video = sys.argv[1]
    except IndexError:
        if lang == "fra":
            raise IndexError(
                f"""
    N'oubliez pas de mettre le nom de la Vidéo Filtrée en argument.
    Exemple : {sys.argv[0]} Vidéo_Filtrée.mp4 {lang}
                """
            )
        raise IndexError(
            f"""
    Don't forget to put the name of the filtered video in the arguments
    Example : {sys.argv[0]} filtered_video.mp4 {lang}
            """
        )

    if lang == "fra":
        logging.info("Utilisation de YoloCR en mode CLI.")
        print("Prélude")
    else:
        logging.info("Using YoloCR in CLI mode.")
        print("Prelude")
    main(lang, filtered_video)
