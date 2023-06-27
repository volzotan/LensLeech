import matplotlib
import matplotlib.pyplot as plt

import math
import statistics
import json

import numpy as np

COLOR_1 = "#ff0000"
COLOR_2 = "#00ff00"
COLOR_3 = "#0000ff"

GROUND_TRUTH_FILE   = "../blender/ground_truth.json"
ERROR_FILE          = "error.json"
OUTPUT_FILENAME     = "plot_rotation_error"

font = {'family' : "FiraSans-Regular",
        # 'weight' : 'bold',
        'size'   : 15}

matplotlib.rc('font', **font)

# fig, axs = plt.subplots(2, sharex=True, sharey=False, figsize=(8, 4))

# colors = [COLOR_1, COLOR_2, COLOR_3]

with open(ERROR_FILE) as f:
    data = json.load(f)

    xs = list(range(0, len(data)))

    errors = []
    vals = []
    gts = []

    print("num frames: {}".format(len(data)))

    for x in xs:
        val = float(data[x]["rotation"])
        gt = float(data[x]["gt_rotation"])

        error1 = (val - gt)
        error2 = ((val-math.tau) - gt)

        # error = min(error1, error2)

        if abs(error1) < abs(error2):
            error = error1
        else:
            error = error2

        vals.append(math.degrees(val))
        gts.append(math.degrees(gt))
        errors.append(math.degrees(error))

        # print("{} {}".format(vals[-1], gts[-1]))

    print("cumulative error: {:5.2f} deg in {} frames. avg: {:5.2f} deg/frame std: {:5.2f}".format(sum(np.abs(errors)), len(xs), statistics.mean(errors), statistics.stdev(errors)))

    # smoothing
    window_size = 3
    # errors = errors[0:window_size//2] + np.convolve(errors, np.ones(window_size)/window_size, mode='valid').tolist() + errors[-1 - window_size//2:-1]

    fig = plt.figure(figsize=(10, 4), dpi=100)
    ax = fig.add_subplot(111)

    # plt.plot(xs, vals)
    # plt.plot(xs, gts)
    ax.plot(xs, errors, color=COLOR_1)

    kwargs = {"alpha": 0.2, "lw": 1}

    # plt.plot([0, 0], [0, max(errors)], 'k--', **kwargs)
    # plt.plot([60,   60], [0, max(errors)], 'k--', **kwargs)
    # plt.plot([120, 120], [0, max(errors)], 'k--', **kwargs)
    # plt.plot([180, 180], [0, max(errors)], 'k--', **kwargs)
    # plt.plot([240, 240], [0, max(errors)], 'k--', **kwargs)
    # plt.plot([300, 300], [0, max(errors)], 'k--', **kwargs)

    plt.title("rotational error")
    ax.set_ylabel("deviation error [deg]", labelpad=5)
    ax.set_xlabel("rotation ground truth [deg]", labelpad=5)

    plt.tight_layout()

    plt.savefig(OUTPUT_FILENAME + ".png", transparent=False)
    plt.savefig(OUTPUT_FILENAME + ".pdf")




    # 5  -5  = 10
    # 350 5  = 15
