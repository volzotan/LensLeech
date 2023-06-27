import sys

import cv2
import numpy as np

# INPUT_FILE = "debruijn_torus_256_256_4_4.png"
# OUTPUT_FILE = "debruijn_torus_256_256_4_4.npy"

INPUT_FILE = "debruijn_torus_16_32_3_3.png"
OUTPUT_FILE = "debruijn_torus_16_32_3_3.npy"

im = cv2.imread(INPUT_FILE)
im = cv2.cvtColor(im, cv2.COLOR_BGR2GRAY)
im = np.array(im, dtype=bool)

np.save(OUTPUT_FILE, im)