import asyncio
import logging
from itertools import islice, accumulate
import os
import re
import shutil
import subprocess
import sys

import html2text
from PIL import Image, ImageOps
from tqdm import tqdm

text_maker = html2text.HTML2Text()
text_maker.unicode_snob = True
# TODO format logging
# TODO use f-string instead of lazy
logging.basicConfig(format="\n%(message)s\n", level=logging.INFO)
logging.debug("Logging in DEBUG")

try:
    _tess_ver_proc = subprocess.check_output(["tesseract", "-v"])
except FileNotFoundError:
    raise ProcessLookupError("Tesseract not found, please install")
TESS_VER_NUM = re.findall(r"\d+\.\d+\.\d+", str(_tess_ver_proc))[0]
logging.debug("Using Tesseract version %s", TESS_VER_NUM)
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
    secs = int(rough_time.split(".")[0])
    h = secs // 3600
    m = (secs % 3600) // 60
    s = secs % 60
    ms = int(rough_time.split(".")[1])
    time_cvtd = f"{h:02}h{m:02}m{s:02}s{ms:03}"
    return time_cvtd


def generate_timecodes() -> float:
    logging.info("Generating Timecodes")
    args = [
        "ffprobe",
        FILTERED_VIDEO,
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
    logging.info("FPS is %f", fps)

    with open("scene_changes.log", "r") as scene_changes_io:
        timecodes = []
        frames = scene_changes_io.readlines()
        for line in frames:
            if int(line.split(" ")[2]) == 0:
                timecodes.append(f"{float(line.split(' ')[0])/fps:.4f}"[:-1])
            elif int(line.split(" ")[1]) == 0:
                timecodes.append(f"{float(line.split(' ')[0])/fps:.4f}"[:-1])

    with open("timecodes.txt", "w") as timecodes_io:
        timecodes.sort(key=float)
        for frame_time in timecodes:
            timecodes_io.write(f"{frame_time}\n")

    if HAS_ALT:
        with open("scene_changes_alt.log", "r") as scene_changes_io:
            timecodes = []
            frames = scene_changes_io.readlines()
            for line in frames:
                if int(line.split(" ")[2]) == 0:
                    timecodes.append(f"{float(line.split(' ')[0])/fps:.4f}"[:-1])
                elif int(line.split(" ")[1]) == 0:
                    timecodes.append(f"{float(line.split(' ')[0])/fps:.4f}"[:-1])
        with open("timecodes_alt.txt", "w") as timecodes_io:
            timecodes.sort(key=float)
            for frame_time in timecodes:
                timecodes_io.write(f"{frame_time}\n")
    return fps


async def get_workload(tasks: list) -> list:
    cpu_count = len(os.sched_getaffinity(0))
    logging.debug("CPU count: %d", cpu_count)
    frames_per_cpu = len(tasks) // cpu_count
    logging.debug("Number of frames per thread: %d", frames_per_cpu)
    split_workload = [
        list(islice(iter(tasks), nb_frame)) for nb_frame in [frames_per_cpu] * cpu_count
    ]
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


async def gen_scsht(queue: asyncio.Queue) -> None:
    total = queue.qsize()
    pbar = tqdm(
        total=total,
        unit="f",
        colour="#00ff00",
        bar_format="{l_bar}{bar}|ETA:{remaining}, {rate_fmt}{postfix}",
    )
    while not queue.empty():
        odd, even, frame_time = await queue.get()
        image = f"filtered_scsht/{convert_secs(str(even))}-{convert_secs(str(odd))}.jpg"
        cmd = [
            "ffmpeg",
            "-ss",
            str(frame_time),
            "-i",
            FILTERED_VIDEO,
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


async def generate_scsht(fps: float) -> None:
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
    tasks = [asyncio.create_task(gen_scsht(queue)) for queue in queues]
    await asyncio.gather(*tasks)


def delete_black_frames() -> None:
    os.chdir("filtered_scsht")
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


async def ocr_tesseract():
    tess_data = []
    if os.path.exists(f"../tessdata/{LANG}.traineddata"):
        tess_data = ["--tessdata-dir", "../tessdata"]
    logging.info("Using LSTM engine")

    print("\n")
    logging.info("Negating images to Black over White")
    negate_images(os.listdir())

    logging.info("Images OCR")
    os.environ["OMP_THREAD_LIMIT"] = "1"
    queues = await get_workload(os.listdir())
    tasks = [asyncio.create_task(ocr(queue, tess_data)) for queue in queues]
    await asyncio.gather(*tasks)
    os.chdir("../tess_result")

    for file in os.listdir():
        with open(file, "r") as file_io:
            lines = file_io.readlines()
        html = "".join(lines)
        txt = text_maker.handle(html).strip()
        with open(file.replace(".hocr", ".txt"), "w") as file_io:
            file_io.write(txt)


def negate_images(images: list):
    pbar = tqdm(
        total=len(images),
        unit="f",
        colour="#ffff00",
        bar_format="{l_bar}{bar}|ETA:{remaining}, {rate_fmt}{postfix}",
    )
    for image in images:
        img = Image.open(image)
        img = ImageOps.invert(img)
        img.save(image)
        pbar.update()
    pbar.close()


async def ocr(queue, tess_data):
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
            ["tesseract", frame, f"../tess_result/{frame.split('/')[-1]}"]
            + tess_data
            + ["-l", LANG, "--psm", "6", "hocr"]
        )
        proc = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.DEVNULL, stderr=asyncio.subprocess.DEVNULL
        )
        await proc.wait()
        queue.task_done()
        pbar.update()
    await queue.join()
    pbar.close()


def italics_verification():
    logging.info(
        "Vérification de l'OCR italique"
        if LANG == "fra"
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


def check():
    logging.info(
        "Traitement des faux positifs et Suppression des sous-titres vides."
        if LANG == "fra"
        else "Treating false positives and Deleting empty subtitles."
    )
    # reversing list so it checks txt before hocr and doesn't try to open a deleted file
    for file in os.listdir()[::-1]:
        with open(file, "r") as file_io:
            lines = file_io.readlines()
            confidences = list()
            for line in lines:
                confidence = re.findall(r"x_wconf \d+", line)
                if len(confidence) > 0:
                    confidence = int(re.findall(r"\d+", confidence[0])[0])
                    confidences.append(confidence)
            final_confidence = (
                sum(confidences) / len(confidences) if len(confidences) > 0 else 100
            )
        if not lines or final_confidence < 55:
            txt_file = file.replace(".hocr", ".txt")
            try:
                logging.debug("deleting %s, confidence %d", txt_file, final_confidence)
                os.remove(txt_file)
            except FileNotFoundError:
                logging.debug("%s already deleted", txt_file)


def convert_ocr():
    logging.info("Converting OCR to srt")
    sub_filename = FILTERED_VIDEO.replace(".mp4", "")
    os.chdir("..")
    try:
        os.remove(sub_filename + ".srt")
        os.remove(sub_filename + "_alt.srt")
    except FileNotFoundError:
        logging.debug("srt files didn't exist before")

    os.chdir("./tess_result")
    i = 0
    j = 0
    list_sub = os.listdir()
    list_sub.sort()
    for file in list_sub:
        if ".txt" in file:
            if "_Alt" not in file:
                i += 1
                k = i
                alt = ""
            else:
                j += 1
                k = j
                alt = "_alt"
            with open(file, "r") as file_io:
                lines = file_io.readlines()
            with open(f"../{sub_filename}{alt}.srt", "a") as ocr_io:
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
    if HAS_ALT:
        lines_new = list()
        with open(f"{sub_filename}_alt.srt", "r") as ocr_io:
            lines = ocr_io.readlines()
            for line in lines:
                line = re.sub(r"   ", "", line)
                lines_new.append(line)
        with open(f"{sub_filename}_alt.srt", "w") as ocr_io:
            ocr_io.writelines(lines_new)


async def main():
    fps = generate_timecodes()
    await generate_scsht(fps)
    delete_black_frames()
    await ocr_tesseract()
    italics_verification()
    check()
    convert_ocr()


if __name__ == "__main__":
    asyncio.run(main())
