import os
import json
import datetime
import statistics
import math

import matplotlib.lines as mlines
import matplotlib.pyplot as plt

import numpy as np


camera_types = [
    ["android",     "Smartphone",       "blue",    "D"],
    ["picamera",    "Embedded Camera",  "green",   "s"],
    ["stillcam",    "Still Camera",     "red",     "o"],    
    # ["gphoto",      "Still Camera",     "red",     "o"],    
    # ["webcam",      "Webcam",           "grey",     "^"],
]

INPUT                   = "lowlight_{}.json"
DETECTIONS_DIR          = "output_{}_json"

NUM_LUX_BUCKETS         = 11
MAX_LUX_VALUE           = 200 + 20

# NUM_LUX_BUCKETS         = 21
# MAX_LUX_VALUE           = 200 + 10

MAX_DETECTION_VALUE     = 65
SIZE_LUX_BUCKET         = MAX_LUX_VALUE/NUM_LUX_BUCKETS

DISPLAY_X_LIM           = [-3, 200+3]

SHIFT                   = False

lux_measurements = {}


def get_bucket_index(lux_value):
    return int(lux_value/SIZE_LUX_BUCKET)

# ---

raw_xss = []
raw_yss = []
type_detections = []

for camera_type in camera_types:

    xs = []
    ys = []
    detections = [[] for x in range(0, NUM_LUX_BUCKETS+1)]

    with open(INPUT.format(camera_type[0]), "r") as f:
        data = json.load(f)

        print("CAMERA TYPE: {}".format(camera_type[0]))

        for image_name in data.keys():
            image_data = data[image_name][0]

            lux_measurements = image_data["lux"]
            filename = image_data["filename"]

            num_detections = None 

            try:
                full_filename = os.path.join(DETECTIONS_DIR.format(camera_type[0]), filename + ".json")
                with open(full_filename) as d:
                    num_detections = len(json.load(d)["found_patterns"])
            except Exception as e:
                print("file missing: {}".format(full_filename))
                continue

            avg_lux = statistics.mean(lux_measurements)
            if avg_lux > MAX_LUX_VALUE:
                print("discarded, MAX_LUX_VALUE {} exceeded: {}".format(MAX_LUX_VALUE, avg_lux))
                continue

            detections[get_bucket_index(avg_lux)].append(num_detections)
            xs.append(avg_lux)
            ys.append(num_detections)
        
    raw_xss.append(xs)
    raw_yss.append(ys)
    type_detections.append(detections)

# ---

fig = plt.figure(figsize=(6, 3))
ax = fig.add_subplot(111)


plots = []
handles = []

for index_type in range(0, len(camera_types)):

    camera = camera_types[index_type]

    xs = []
    ys = []
    ys_err = []
    detections = type_detections[index_type]

    for i in range(0, len(detections)):

        if len(detections[i]) == 0:
            break
        
        mean = statistics.mean(detections[i])
        ys.append(mean)

        xs.append(i*SIZE_LUX_BUCKET) #+SIZE_LUX_BUCKET/2)

        if len(detections[i]) > 2:
            dev = statistics.stdev(detections[i])
            ys_err.append(dev)
        else:
            ys_err.append(0)

    # ax.boxplot(detections, positions=[int(i * SIZE_LUX_BUCKET) for i in range(0, len(detections))], showfliers=False, widths=[10 for x in detections])

    # plt.scatter(raw_xss[index_type], raw_yss[index_type], 
    #     s=1, 
    #     color=camera[2],
    #     alpha=0.2)

    if SHIFT:
        xs = [x + index_type*2 for x in xs]

    p = plt.errorbar(xs, ys, yerr=ys_err, 
        label=camera[1], 
        elinewidth=1.0, 
        capsize=3, 
        color=camera[2], 
        marker=camera[3],
        markersize=5)
    plots.append(p)

    plotline, caplines, barlinecols = p
    for item in caplines + barlinecols:
        item.set_alpha(0.7)

    h = mlines.Line2D([], [], label=camera[1], color=camera[2], marker=camera[3], linestyle="None", markersize=6)
    handles.append(h)

ncol = len(camera_types)
if len(camera_types) == 4:
    ncol = 2

legend = ax.legend(handles=handles, loc="upper center", frameon=False, ncol=ncol)

ax.set_ylim([0, MAX_DETECTION_VALUE])
ax.set_xlim(DISPLAY_X_LIM)

ax.set_ylabel("identified points in pattern", labelpad=5)
ax.set_xlabel("Illuminance [lx]", labelpad=5)

plt.tight_layout()
plt.savefig("plot_patternvslight.png", transparent=False)
plt.savefig("plot_patternvslight.pdf", transparent=False)