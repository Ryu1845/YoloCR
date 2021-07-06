import vapoursynth as vs
import toml
import cv2
import numpy as np

config = toml.load('../config.toml')
core = vs.get_core()
clip = core.ffms2.Source(config['source_file'])
crop_box_dimension = config['crop']['crop_box_dimension']
height_crop_box = config['crop']['crop_box_height']


def draw_box(n, f):
    frame = f
    frame = [frame]
    fout = frame[0].copy()
    arr = np.asarray(frame[0].get_read_array(0))
    pt1 = ((f.width-crop_box_dimension[0])//2, f.height-(height_crop_box+crop_box_dimension[1]))
    pt2 = ((f.width+crop_box_dimension[0])//2, f.height-height_crop_box)
    output = cv2.rectangle(arr, pt1, pt2, (125, 125, 125), thickness=20)
    out_arr = np.asarray(fout.get_write_array(0))
    np.copyto(out_arr, output)
    return fout


clip = core.std.ModifyFrame(clip, clip, draw_box)
clip.set_output()
