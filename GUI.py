"GUI for YoloCR"
# TODO put preview in a separate page
import asyncio
import base64
import io
import os
import subprocess

import PySimpleGUIQt as sg
import toml
from PIL import Image, ImageDraw

import yolocr

sg.theme("DarkTeal2")  # Add a little color to your windows


def gen_scsht(video, frame_time):
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
        "-y",
        "screenshot.png",
    ]
    subprocess.run(cmd)


def convert_to_bytes(file_or_bytes, height, crop_box, height_alt=-1, resize=None):
    """
    Will convert into bytes and optionally resize an image that is a file or a base64 bytes object.
    Turns into  PNG format in the process so that can be displayed by tkinter
    :param file_or_bytes: either a string filename or a bytes base64 image object
    :type file_or_bytes:  (Union[str, bytes])
    :param resize:  optional new size
    :type resize: (Tuple[int, int] or None)
    :return: (bytes) a byte-string object
    :rtype: (bytes)
    """
    if isinstance(file_or_bytes, str):
        img = Image.open(file_or_bytes)
    else:
        try:
            img = Image.open(io.BytesIO(base64.b64decode(file_or_bytes)))
        except Exception as e:
            dataBytesIO = io.BytesIO(file_or_bytes)
            img = Image.open(dataBytesIO)

    w, h = img.size
    shape = [
        (w - crop_box[0]) / 2,
        h - height,
        (w + crop_box[0]) / 2,
        h - height - crop_box[1],
    ]
    img1 = ImageDraw.Draw(img)
    img1.rectangle(shape, outline="red", width=5)
    if height_alt != -1:
        shape = [
            (w - crop_box[0]) / 2,
            h - height_alt,
            (w + crop_box[0]) / 2,
            h - height_alt - crop_box[1],
        ]
        img2 = ImageDraw.Draw(img)
        img2.rectangle(shape, outline="red", width=5)

    if resize:
        new_width, new_height = resize
        scale = min(new_height / h, new_width / w)
        img = img.resize((int(w * scale), int(h * scale)), Image.ANTIALIAS)
    bio = io.BytesIO()
    img.save(bio, format="PNG")
    del img
    return bio.getvalue()


def main(config):
    # All the stuff inside your window. This is the PSG magic code compactor...
    source_file_row = [
        sg.Text("Source File Path"),
        sg.InputText(key="source_file", default_text=config["source_file"]),
        sg.FileBrowse(),
    ]
    cb_dimension_row = [
        sg.Text("Crop Box Dimensions"),
        sg.Slider(
            (0, 1920),
            default_value=config["crop"]["crop_box_dimension"][0],
            key="crop_box_width",
            tooltip="Width of the Crop Box",
            enable_events=True,
        ),
        sg.T(
            config["crop"]["crop_box_dimension"][0],
            key="crop_box_width_label",
        ),
        sg.Slider(
            (0, 1080),
            default_value=config["crop"]["crop_box_dimension"][1],
            key="crop_box_height",
            tooltip="Height of the Crop Box",
            enable_events=True,
        ),
        sg.T(
            config["crop"]["crop_box_dimension"][1],
            key="crop_box_height_label",
        ),
    ]
    height_cb_row = [
        sg.Text("Height Crop Box"),
        sg.Slider(
            (0, 1080),
            size=(4, 0.3),
            default_value=config["crop"]["crop_box_height"],
            key="height_crop_box",
            orientation="h",
            enable_events=True,
        ),
        sg.T(
            config["crop"]["crop_box_height"],
            key="height_crop_box_label",
        ),
    ]
    height_alt_cb_row = [
        sg.Text("Height Alt Crop Box"),
        sg.Slider(
            (-1, 1080),
            size=(4, 0.3),
            default_value=config["crop"]["crop_box_height_alt"],
            key="height_crop_box_alt",
            orientation="h",
            tooltip="Put at -1 to deactivate",
            enable_events=True,
        ),
        sg.T(
            config["crop"]["crop_box_height_alt"],
            key="height_crop_box_alt_label",
        ),
    ]
    crop_frame = [
        sg.Frame(
            "Crop",
            [
                cb_dimension_row,
                height_cb_row,
                height_alt_cb_row,
                [sg.Button("Preview Settings")],
            ],
        )
    ]
    ss_factor_row = [
        sg.Text("Supersampling Factor"),
        sg.Slider(
            (-1, 4),
            orientation="h",
            tooltip="Use -1 to automagically choose it",
            key="supersampling_factor",
            default_value=config["upscale"]["supersampling_factor"],
            enable_events=True,
        ),
        sg.Text(
            config["upscale"]["supersampling_factor"],
            key="ss_factor_label",
        ),
    ]
    upscale_mode_row = [
        sg.Text("Upscale Mode"),
        sg.Listbox(
            ["sinc", "znedi3", "waifu2x"],
            key="upscale_mode",
            size=(10, 2),
            default_values=[config["upscale"]["upscale_mode"]],
            enable_events=True,
        ),
    ]
    upscale_frame = [
        sg.Frame(
            "Upscale",
            [
                ss_factor_row,
                upscale_mode_row,
            ],
        )
    ]
    inline_threshold_row = [
        sg.Text("Inline Threshold"),
        sg.Slider(
            (0, 255),
            size=(4, 0.3),
            orientation="h",
            key="inline_threshold",
            default_value=config["threshold"]["inline_threshold"],
            enable_events=True,
        ),
        sg.Text(
            config["threshold"]["inline_threshold"],
            key="i_threshold_label",
        ),
    ]
    outline_threshold_row = [
        sg.Text("Outline Threshold"),
        sg.Slider(
            (0, 255),
            orientation="h",
            size=(4, 0.3),
            key="outline_threshold",
            default_value=config["threshold"]["outline_threshold"],
            enable_events=True,
        ),
        sg.Text(
            config["threshold"]["outline_threshold"],
            key="o_threshold_label",
        ),
    ]
    scd_threshold_row = [
        sg.Text("SCD Threshold"),
        sg.Slider(
            (0, 100),
            size=(4, 0.3),
            orientation="h",
            key="SCD_threshold",
            default_value=config["threshold"]["SCD_threshold"] * 100,
            enable_events=True,
        ),
        sg.Text(
            config["threshold"]["SCD_threshold"],
            key="SCD_threshold_label",
        ),
    ]
    threshold_frame = [
        sg.Frame(
            "Threshold",
            [
                [sg.Text("Threshold Mode")],
                inline_threshold_row,
                outline_threshold_row,
                scd_threshold_row,
            ],
        )
    ]
    settings_col = [
        source_file_row,
        crop_frame,
        upscale_frame,
        threshold_frame,
        [sg.Checkbox("Preview", key="has_preview", enable_events=True)],
        [sg.Submit(), sg.Cancel()],
    ]

    preview_col = [
        [sg.Image(key="preview_image")],
    ]

    layout = [
        [
            sg.Column(settings_col, element_justification="c"),
            sg.VSeperator(),
            sg.Col(preview_col, element_justification="c"),
        ]
    ]

    # Create the Window
    window = sg.Window("YoloCR", layout, font=("Helvetica", 12))
    # Event Loop to process "events"
    prev_vals = ()
    while True:
        event, values = window.read()
        if event in (sg.WIN_CLOSED, "Cancel"):
            break
        if values["has_preview"]:
            window["crop_box_width"].update(enable_events=False)
            window["crop_box_height"].update(enable_events=False)
            window["height_crop_box"].update(enable_events=False)
            window["height_crop_box_alt"].update(enable_events=False)
            if not os.path.exists("screenshot.png"):
                gen_scsht(values["source_file"], 12)
            if (
                values["height_crop_box"],
                values["crop_box_width"],
                values["crop_box_height"],
                values["height_crop_box_alt"],
            ) != prev_vals:
                window["preview_image"].update(
                    data=convert_to_bytes(
                        "screenshot.png",
                        values["height_crop_box"],
                        (values["crop_box_width"], values["crop_box_height"]),
                        height_alt=values["height_crop_box_alt"],
                    )
                )
                prev_vals = (
                    values["height_crop_box"],
                    values["crop_box_width"],
                    values["crop_box_height"],
                    values["height_crop_box_alt"],
                )
        else:
            window["preview_image"].update(data=bytes())

        window["crop_box_width_label"].update(values["crop_box_width"])
        window["crop_box_height_label"].update(values["crop_box_height"])
        window["height_crop_box_label"].update(values["height_crop_box"])
        window["height_crop_box_alt_label"].update(values["height_crop_box_alt"])
        window["ss_factor_label"].update(values["supersampling_factor"])
        window["i_threshold_label"].update(values["inline_threshold"])
        window["o_threshold_label"].update(values["outline_threshold"])
        window["SCD_threshold_label"].update(values["SCD_threshold"] / 100)

        config = {
            "source_file": values["source_file"],
            "crop": {
                "crop_box_dimension": [
                    int(values["crop_box_width"]),
                    int(values["crop_box_height"]),
                ],
                "crop_box_height": int(values["height_crop_box"]),
                "crop_box_height_alt": int(values["height_crop_box_alt"]),
            },
            "upscale": {
                "supersampling_factor": int(values["supersampling_factor"]),
                "expand_ratio": config["upscale"]["expand_ratio"],
                "upscale_mode": values["upscale_mode"][0],
            },
            "threshold": {
                "threshold_mode": config["threshold"]["threshold_mode"],
                "threshold": config["threshold"]["threshold"],
                "inline_threshold": int(values["inline_threshold"]),
                "outline_threshold": int(values["outline_threshold"]),
                "SCD_threshold": values["SCD_threshold"] / 100,
            },
        }
        with open("config.tmp.toml", "w") as config_io:
            toml.dump(config, config_io)
        if event == "Submit":
            os.rename("config.tmp.toml", "config.toml")

    window.close()


# asyncio.run(yolocr.main("fra", "Filtered_video.mp4"))

if __name__ == "__main__":
    config_path = "config.toml"
    config = toml.load(config_path)
    main(config)
