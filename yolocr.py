import asyncio
import logging
from itertools import islice
import os
import re
import shutil
import subprocess
import sys

import pytesseract
from tqdm import tqdm

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
    time_cvtd = f"{h:02}h{m:02}m{s:02}s{ms:03}ms"
    return time_cvtd


def generate_timecodes() -> float:
    logging.info("generating timecodes")
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


def get_workload(frame_times: list) -> list:
    cpu_count = len(os.sched_getaffinity(0))
    logging.debug("CPU count: %d", cpu_count)
    frames_per_cpu = len(frame_times) // cpu_count
    logging.debug("Number of frames per thread: %d", frames_per_cpu)
    split_workload = [
        list(islice(iter(frame_times), nb_frame))
        for nb_frame in [frames_per_cpu] * cpu_count
    ]
    rest = len(frame_times) % cpu_count
    split_workload[cpu_count - 1] += frame_times[-rest:]
    logging.debug([len(sub) for sub in split_workload])
    return split_workload


async def gen_scsht(queue: asyncio.Queue) -> None:
    total = queue.qsize()
    pbar = tqdm(total=total)
    while not queue.empty():
        frame_time = await queue.get()
        cmd = [
            "ffmpeg",
            "-ss",
            str(frame_time),
            "-i",
            FILTERED_VIDEO,
            "-vframes",
            "1",
            "-y",
            "-loglevel",
            "quiet",
            f"filtered_scsht/{convert_secs(str(frame_time))}.jpg",
        ]
        proc = await asyncio.create_subprocess_exec(*cmd)
        await proc.wait()
        queue.task_done()
        pbar.update()
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
        frame_times.append(frame_time)

    queues = []
    split_workload = get_workload(frame_times)
    for workload in split_workload:
        queue: asyncio.Queue = asyncio.Queue()
        for frame in workload:
            await queue.put(frame)
        queues.append(queue)

    tasks = [asyncio.create_task(gen_scsht(queue)) for queue in queues]
    await asyncio.gather(*tasks)


async def delete_black_frames() -> None:
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
    proc = await asyncio.create_subprocess_exec(*cmd)
    await proc.wait()
    black_frame_size = os.path.getsize("black_frame.jpg")
    for file in os.listdir():
        if os.path.getsize(file) == black_frame_size:
            os.remove(file)


async def main():
    fps = generate_timecodes()
    await generate_scsht(fps)
    await delete_black_frames()


if __name__ == "__main__":
    asyncio.run(main())
