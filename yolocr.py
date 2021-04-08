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

import html2text
from PIL import Image, ImageOps
from tqdm import tqdm

text_maker = html2text.HTML2Text()
text_maker.unicode_snob = True
logging.basicConfig(format="\n%(message)s\n", level=logging.DEBUG)
logging.debug("Logging in DEBUG")

try:
    _tess_ver_proc = subprocess.check_output(["tesseract", "-v"])
except FileNotFoundError:
    raise ProcessLookupError("Tesseract not found, please install")
TESS_VER_NUM = re.findall(r"\d+\.\d+\.\d+", str(_tess_ver_proc))[0]
logging.debug(f"Using Tesseract version {TESS_VER_NUM}")
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

HAS_ALT = os.path.exists("scene_changes_alt.log")

if LANG == "fra":
    logging.info("Utilisation de YoloCR en mode CLI.")
    print("Prélude")
else:
    logging.info("Using YoloCR in CLI mode.")
    print("Prelude")


def convert_secs(rough_time: str) -> str:
    """
    Convert seconds to human readable time
    Parameters
    ----------
    rough_time:
        time you want to convert in seconds
    Returns
    -------
    human readable time
    """
    secs = int(rough_time.split(".")[0])
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    ms = int(rough_time.split(".")[1])
    time_cvtd = f"{h:02}h{m:02}m{s:02}s{ms:03}"
    return time_cvtd


def generate_timecodes(
    scn_chglog: str = "scene_changes.log",
    video: str = FILTERED_VIDEO,
    timecode_pth: str = "timecodes.txt",
) -> float:
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
    Returns
    -------
    framerate of the video
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
                timecodes.append(f"{float(line.split(' ')[0])/fps:.4f}"[:-1])

    with open(timecode_pth, "w") as timecodes_io:
        timecodes.sort(key=float)
        for frame_time in timecodes:
            timecodes_io.write(f"{frame_time}\n")
    return fps


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
    queue: asyncio.Queue, video: str = FILTERED_VIDEO, scsht_pth: str = "filtered_scsht"
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
        odd, even, frame_time = await queue.get()
        image = f"{scsht_pth}/{convert_secs(str(even))}-{convert_secs(str(odd))}.jpg"
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


async def generate_scsht(fps: float, video: str = FILTERED_VIDEO) -> None:
    """
    Generate screenshots based on a file containing the timecodes
    Parameters
    ----------
    fps:
        framerate of the video
    """
    # TODO ALT
    logging.info("Generating Screenshots")
    with open("timecodes.txt", "r") as timecodes_io:
        timecodes_str = timecodes_io.readlines()
        timecodes = [float(line) for line in timecodes_str]

    frame_times = []
    for idx, even in enumerate(timecodes[::2]):
        try:
            odd: float = timecodes[idx * 2 + 1]
        except IndexError:
            break
        if even - odd - 0.003 > 2 / fps:
            frame_time = (even + odd) / 2
        else:
            frame_time = odd
        if frame_time < 1:
            frame_time = 0
        frame_times.append((odd, even, frame_time))
    logging.debug(len(frame_times))
    queues = await get_workload(frame_times)
    tasks = [asyncio.create_task(gen_scsht(queue, video=video)) for queue in queues]
    await asyncio.gather(*tasks)


def delete_black_frames(scsht_pth: str = "filtered_scsht") -> None:
    """
    Delete black frames that would have been created in the process of generating the screenshots
    """
    os.chdir(scsht_pth)
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
    for file in os.listdir():
        if os.path.getsize(file) == black_frame_size:
            os.remove(file)


async def ocr_tesseract(
    tess_data_pth: str = "../tessdata", tess_result_pth: str = "../tess_result"
) -> None:
    """
    Use Optical Character Recognition of Google's Tesseract
    to generate text from a directory of images
    """
    tess_data = []
    if os.path.exists(f"{tess_data_pth}/{LANG}.traineddata"):
        tess_data = ["--tessdata-dir", tess_data_pth]
    logging.info("Using LSTM engine")

    logging.info("Negating images to Black over White")
    negate_images(os.listdir())

    logging.info("Images OCR")
    os.environ["OMP_THREAD_LIMIT"] = "1"
    queues = await get_workload(os.listdir())
    tasks = [asyncio.create_task(ocr(queue, tess_data)) for queue in queues]
    await asyncio.gather(*tasks)
    os.chdir(tess_result_pth)

    for file in os.listdir():
        with open(file, "r") as file_io:
            lines = file_io.readlines()
        html = "".join(lines)
        html_w_nwlines = re.sub(
            "<span class='ocr_line", "<br><span class='ocr_line", html
        )
        txt = text_maker.handle(html_w_nwlines).strip()
        with open(file.replace(".hocr", ".txt"), "w") as file_io:
            file_io.write(txt)


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
    tess_data: list,
    tess_result_pth: str = "../tess_result",
    lang: str = LANG,
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
        cmd = (
            ["tesseract", frame, f"{tess_result_pth}/{frame.split('/')[-1]}"]
            + tess_data
            + ["-l", lang, "--psm", "6", "hocr"]
        )
        # logging.debug(" ".join(cmd))
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()
        queue.task_done()
        pbar.update()
    await queue.join()
    pbar.close()


def italics_verification(lang: str = LANG) -> None:
    """
    Convert Markdown italics to HTML italics
    """
    logging.info(
        "Vérification de l'OCR italique"
        if lang == "fra"
        else "Verifying the italics OCR"
    )
    for file in tqdm(
        os.listdir(),
        bar_format="{l_bar}{bar}|ETA:{remaining}, {rate_fmt}{postfix}",
        colour="#0000ff",
    ):
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


def check(lang: str = LANG) -> None:
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
    sub_filename: str = FILTERED_VIDEO.removesuffix(".mp4"),
    tess_result_pth: str = "./tess_result",
) -> None:
    """
    Assemble the different text files into an SRT subtitle file
    """
    logging.info("Converting OCR to srt")
    os.chdir("..")
    try:
        os.remove(sub_filename + ".srt")
    except FileNotFoundError:
        logging.debug("subtitle files didn't exist before")

    os.chdir(tess_result_pth)
    i = 0
    list_sub = os.listdir()
    list_sub.sort()
    for file in list_sub:
        if ".txt" in file:
            i += 1
            k = i
            with open(file, "r") as file_io:
                lines = file_io.readlines()
            with open(f"../{sub_filename}.srt", "a") as ocr_io:
                ocr_io.write(str(k) + "\n")
                sub_time = os.path.basename(file)
                sub_time = re.sub("[hm]", ":", sub_time)
                sub_time = re.sub("s", ",", sub_time)
                sub_time = re.sub("-", " --> ", sub_time)
                sub_time = re.sub(".jpg.txt", "", sub_time)
                ocr_io.write(sub_time + "\n")
                ocr_io.writelines(lines)
                ocr_io.write("\n\n")

    os.chdir("..")
    lines_new = list()
    with open(f"{sub_filename}.srt", "r") as ocr_io:
        lines = ocr_io.readlines()
        for line in lines:
            line = re.sub(r"   ", "", line)
            lines_new.append(line)
    with open(f"{sub_filename}.srt", "w") as ocr_io:
        ocr_io.writelines(lines_new)


async def main() -> None:
    fps = generate_timecodes()
    if HAS_ALT:
        generate_timecodes(
            scn_chglog="scene_changes_alt.log", timecode_pth="timecodes_alt.txt"
        )
    await generate_scsht(fps)
    delete_black_frames()
    await ocr_tesseract()
    italics_verification()
    check()
    convert_ocr()
    if HAS_ALT:
        convert_ocr(sub_filename=FILTERED_VIDEO.replace(".mp4", "_alt"))


if __name__ == "__main__":
    asyncio.run(main())
