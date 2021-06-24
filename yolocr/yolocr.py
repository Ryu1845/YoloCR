#!/usr/bin/env python3
"OCR part of the YoloCR toolkit"
import asyncio
import logging
import os
import re
import shutil
import subprocess
import sys
from itertools import accumulate

from helpers import convert_secs, In_dir
import html2text
from PIL import Image, ImageOps
from tqdm import tqdm
import tesserocr

text_maker = html2text.HTML2Text()
text_maker.unicode_snob = True
logging.basicConfig(format="%(message)s\n", level=logging.DEBUG)
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
    timecode_pth: str,
) -> None:
    """
    Generate timecodes from the scene changes frame values
    Parameters
    ----------
    scn_chglog:
        path of scene changelog
    video:
        path of the video you want to generate the timecodes of
    timecode_pth:
        the path you want the timecodes to be saved in
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
        for line in frames:
            if int(line.split(" ")[2]) == 0:
                timecodes.append(f"{float(line.split(' ')[0])/fps:.4f}"[:-1])
            elif int(line.split(" ")[1]) == 0:
                timecodes.append(f"{(float(line.split(' ')[0])+1)/fps:.4f}"[:-1])

    with open(timecode_pth, "w") as timecodes_io:
        timecodes.sort(key=float)
        for frame_time in timecodes:
            timecodes_io.write(f"{frame_time}\n")


async def get_workload(tasks: list) -> list:
    """
    Generate a list of queues for async work based on a list of elements
    Parameter
    ---------
    tasks:
        list of element to divide in queues
    Returns
    -------
    asyncio queues for the workloads
    """
    cpu_count = len(os.sched_getaffinity(0))
    logging.debug(f"CPU count: {cpu_count}")
    frames_per_cpu = len(tasks) // cpu_count
    logging.debug(f"Number of frames per thread: {frames_per_cpu}")
    lengths_to_split = [frames_per_cpu] * cpu_count
    split_workload = [
        tasks[x - y : x] for x, y in zip(accumulate(lengths_to_split), lengths_to_split)
    ]
    rest = len(tasks) % cpu_count
    if rest != 0:
        split_workload[cpu_count - 1] += tasks[-rest:]
    logging.debug([len(sub) for sub in split_workload])
    logging.debug(
        [
            "unique" if len(set(sub)) == len(sub) else "not unique"
            for sub in split_workload
        ]
    )
    prev_sub: list = list()
    for sub in split_workload:
        if sub == prev_sub:
            logging.debug("not unique")
        prev_sub = sub

    queues = []
    for workload in split_workload:
        queue: asyncio.Queue = asyncio.Queue()
        for frame in workload:
            await queue.put(frame)
        queues.append(queue)
    return queues


async def gen_scsht(
    queue: asyncio.Queue,
    video: str,
    scsht_pth: str,
) -> None:
    """
    Screenshot a list of timecode asynchronously
    Parameters
    ----------
    queue:
        list of timecodes assigned to this thread
    video:
        path of the video to screenshot
    scsht_pth:
        path to save the screenshots in
    """
    total = queue.qsize()
    pbar = tqdm(
        total=total,
        unit="f",
        colour="#00ff00",
        bar_format="{l_bar}{bar}|ETA:{remaining}, {rate_fmt}{postfix}",
    )
    while not queue.empty():
        even, odd, frame_time = await queue.get()
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
        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.wait()
        queue.task_done()
        pbar.update()
    await queue.join()
    pbar.close()


async def generate_scsht(video: str, scsht_pth: str, timecode_pth: str) -> None:
    """
    Generate screenshots based on a file containing the timecodes
    """
    # TODO ALT
    logging.info("Generating Screenshots")
    with open(timecode_pth, "r") as timecodes_io:
        timecodes_str = timecodes_io.readlines()
        timecodes = [float(line) for line in timecodes_str]

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
    queues = await get_workload(frame_times)
    tasks = [
        asyncio.create_task(gen_scsht(queue, video, scsht_pth)) for queue in queues
    ]
    await asyncio.gather(*tasks)


def delete_black_frames(path: str) -> None:
    """
    Delete black frames in a directory
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
        proc = subprocess.Popen(cmd)
        proc.communicate()
        black_frame_size = os.path.getsize("black_frame.jpg")
        prev = len(os.listdir())
        for file in os.listdir():
            if os.path.getsize(file) == black_frame_size:
                os.remove(file)
        new = len(os.listdir())
        logging.debug(f"deleted {prev - new}")


async def ocr_tesseract(
    scsht_pth: str,
    tess_data_pth: str,
    tess_result_pth: str,
    lang: str,
) -> None:
    """
    Use Optical Character Recognition of Google's Tesseract
    to generate text from a directory of images
    """
    if os.path.exists(f"{tess_data_pth}/{lang}.traineddata"):
        os.environ["TESSDATA_PREFIX"] = os.path.abspath(tess_data_pth)
    logging.info("Using LSTM engine")

    logging.info("Negating images to Black over White")

    with In_dir(scsht_pth):
        negate_images(os.listdir())

    logging.info("Images OCR")
    os.environ["OMP_THREAD_LIMIT"] = "1"
    screenshots = [
        f"{scsht_pth.removesuffix('/')}/{file}" for file in os.listdir(scsht_pth)
    ]
    logging.debug(screenshots)
    queues = await get_workload(screenshots)
    tasks = [asyncio.create_task(ocr(queue, tess_result_pth, lang)) for queue in queues]
    await asyncio.gather(*tasks)

    # with In_dir(tess_result_pth):
    # for file in os.listdir():
    # with open(file, "r") as file_io:
    # lines = file_io.readlines()
    # html = "".join(lines)
    # html_w_nwlines = re.sub(
    # "<span class='ocr_line", "<br><span class='ocr_line", html
    # )
    # txt = text_maker.handle(html_w_nwlines).strip()
    # with open(file.replace(".hocr", ".txt"), "w") as file_io:
    # file_io.write(txt)


def negate_images(images: list) -> None:
    """
    Invert colors of a list of images
    Parameters
    ----------
    images:
        list of images to invert
    """
    for image in images:
        img = Image.open(image)
        img = ImageOps.invert(img)
        img.save(image)


async def ocr(
    queue: asyncio.Queue,
    tess_result_pth: str,
    lang: str,
) -> None:
    """
    Asynchronously OCR a queue of images
    Parameters
    ----------
    queue:
        queue containing the images to OCR
    tess_data:
        options for tessdata in tesseract
    """
    total = queue.qsize()
    pbar = tqdm(
        total=total,
        unit="f",
        colour="#00ffff",
        bar_format="{l_bar}{bar}|ETA:{remaining}, {rate_fmt}{postfix}",
    )
    while not queue.empty():
        frame = await queue.get()
        path = tess_result_pth + "/" + os.path.basename(frame).replace(".jpg", ".txt")
        with open(path, "w") as txt_io:
            txt_io.write(
                tesserocr.file_to_text(frame, psm=tesserocr.PSM.SINGLE_BLOCK, lang=lang)
            )
        queue.task_done()
        pbar.update()
    await queue.join()
    pbar.close()


def italics_verification(lang: str) -> None:
    """
    Convert Markdown italics to HTML italics
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


async def main(lang: str, filtered_video: str) -> None:
    try:
        os.mkdir("data/filtered_scsht")
    except FileExistsError:
        shutil.rmtree("data/filtered_scsht")
        os.mkdir("data/filtered_scsht")

    try:
        os.mkdir("data/tess_result")
    except FileExistsError:
        shutil.rmtree("data/tess_result")
        os.mkdir("data/tess_result")

    has_alt = os.path.exists("data/scene_changes_alt.log")
    generate_timecodes("data/scene_changes.log", filtered_video, "data/timecodes.txt")
    if has_alt:
        generate_timecodes(
            "data/scene_changes_alt.log", filtered_video, "data/timecodes_alt.txt"
        )
    await generate_scsht(filtered_video, "data/filtered_scsht", "data/timecodes.txt")
    delete_black_frames("data/filtered_scsht")
    await ocr_tesseract(
        "data/filtered_scsht", "data/tessdata", "data/tess_result", lang
    )
    italics_verification(lang)
    # check(lang=lang) # actually makes too many false negative
    convert_ocr(filtered_video.removesuffix(".mp4"), "data/tess_result")
    if has_alt:
        convert_ocr(filtered_video.replace(".mp4", "_alt"), "data/tess_result")


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
    asyncio.run(main(lang, filtered_video))
