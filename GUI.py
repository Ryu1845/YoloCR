"GUI for YoloCR"
# TODO put preview in a separate page
import asyncio
import os
import subprocess

import cv2
import json
import PySimpleGUIQt as sg
import toml

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


def get_vid_info(video):
    cmd = "ffprobe -v quiet -print_format json -show_format -show_streams".split()
    cmd.append(video)
    result = subprocess.run(cmd, capture_output=True, text=True)
    info = json.loads(result.stdout)
    return info


def convert_to_bytes(path, height, crop_box, height_alt=-1, resize=None):
    img = cv2.imread(path)
    h_img, w_img, _ = img.shape

    start_pt = (int((w_img - crop_box[0]) / 2), h_img - height - crop_box[1])
    end_pt = (int((w_img + crop_box[0]) / 2), h_img - height)
    color = (255, 0, 0)
    thickness = 5
    image = cv2.rectangle(img, start_pt, end_pt, color, thickness=thickness)

    if height_alt != -1:
        start_pt2 = (int((w_img - crop_box[0]) / 2), h_img - height_alt - crop_box[1])
        end_pt2 = (int((w_img + crop_box[0]) / 2), h_img - height_alt)
        image = cv2.rectangle(image, start_pt2, end_pt2, color, thickness=thickness)

    if resize:
        new_w = int(w_img * resize / 100)
        new_h = int(h_img * resize / 100)
        new_dim = (new_w, new_h)
        image = cv2.resize(image, new_dim, interpolation=cv2.INTER_LANCZOS4)

    _, im_buf_arr = cv2.imencode(".png", image)
    byte_im = im_buf_arr.tobytes()
    return byte_im


def preview_vp(video, time, crop_box, height_alt, resize=None):
    pass


def main(config):
    info = get_vid_info(config["source_file"])
    duration = float(info["format"]["duration"])

    # All the stuff inside your window. This is the PSG magic code compactor...
    source_file_row = [
        sg.Text("Source File Path"),
        sg.InputText(key="source_file", default_text=config["source_file"]),
        sg.FileBrowse(),
    ]
    time_scsht_row = [
        sg.T("Screenshot Time"),
        sg.Slider(
            (0, int(duration)),
            key="time_scsht",
            enable_events=True,
            orientation="h",
            size=(4, 0.3),
        ),
        sg.T("0", key="time_scsht_lbl"),
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
            key="crop_box_width_lbl",
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
            key="crop_box_height_lbl",
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
            key="height_crop_box_lbl",
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
            key="height_crop_box_alt_lbl",
        ),
    ]
    crop_frame = [
        sg.Frame(
            "Crop",
            [
                cb_dimension_row,
                height_cb_row,
                height_alt_cb_row,
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
            key="ss_factor_lbl",
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
            key="i_threshold_lbl",
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
            key="o_threshold_lbl",
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
            key="SCD_threshold_lbl",
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
        time_scsht_row,
        [sg.Button("Generate Screenshot")],
        crop_frame,
        upscale_frame,
        threshold_frame,
        [sg.Checkbox("Preview", key="has_preview", enable_events=True)],
        [sg.Button("Save Settings"), sg.Cancel()],
    ]
    preview_col = [
        [sg.Image(key="preview_image")],
    ]
    # layout = [
    #     [
    #         sg.Column(settings_col, element_justification="c"),
    #         sg.VSeperator(),
    #         sg.Col(preview_col, element_justification="c"),
    #     ]
    # ]
    layout = [
        source_file_row,
        time_scsht_row,
        [sg.Button("Generate Screenshot")],
        crop_frame,
        upscale_frame,
        threshold_frame,
        [
            sg.Checkbox("Preview", key="has_preview", enable_events=True),
            sg.Slider(
                (0, 200),
                key="resize_factor",
                enable_events=True,
                size=(4, 0.3),
                orientation="h",
                default_value=30,
            ),
            sg.T("30%", key="resize_factor_lbl"),
        ],
        [sg.Button("Save Settings"), sg.Cancel()],
        [sg.Image(key="preview_image")],
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
            if not os.path.exists("screenshot.png") or event == "Generate Screenshot":
                gen_scsht(values["source_file"], values["time_scsht"])

            new_vals = (
                values["height_crop_box"],
                values["crop_box_width"],
                values["crop_box_height"],
                values["height_crop_box_alt"],
            )
            if new_vals != prev_vals or event == "Generate Screenshot":
                window["preview_image"].update(
                    data=convert_to_bytes(
                        "screenshot.png",
                        values["height_crop_box"],
                        (values["crop_box_width"], values["crop_box_height"]),
                        height_alt=values["height_crop_box_alt"],
                        resize=values["resize_factor"],
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

        m, s = divmod(values["time_scsht"], 60)
        h, m = divmod(m, 60)
        readable_time_scsht = f"{h:d}:{m:02d}:{s:02d}"
        window["time_scsht_lbl"].update(readable_time_scsht)
        window["crop_box_width_lbl"].update(values["crop_box_width"])
        window["crop_box_height_lbl"].update(values["crop_box_height"])
        window["height_crop_box_lbl"].update(values["height_crop_box"])
        window["height_crop_box_alt_lbl"].update(values["height_crop_box_alt"])
        window["ss_factor_lbl"].update(values["supersampling_factor"])
        window["i_threshold_lbl"].update(values["inline_threshold"])
        window["o_threshold_lbl"].update(values["outline_threshold"])
        window["SCD_threshold_lbl"].update(values["SCD_threshold"] / 100)
        window["resize_factor_lbl"].update(f"{values['resize_factor']}%")

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
        if event == "Save Settings":
            os.rename("config.tmp.toml", "config.toml")

    window.close()


# asyncio.run(yolocr.main("fra", "Filtered_video.mp4"))

if __name__ == "__main__":
    config_path = "config.toml"
    config = toml.load(config_path)
    main(config)
