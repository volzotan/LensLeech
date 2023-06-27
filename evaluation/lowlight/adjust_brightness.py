import subprocess
import os

SCENES_DIR      = "mitindoor"
OUTPUT_DIR      = SCENES_DIR + "_brightnessadjusted"
OUTPUT_DIR2     = "brightframe_brightnessadjusted"
 
scenes = [f for f in os.listdir(SCENES_DIR) if os.path.isfile(os.path.join(SCENES_DIR, f))]

os.makedirs(OUTPUT_DIR, exist_ok=True)

for value in [-60, -15, 0, 15, 40, 60]:

    print("value: {}".format(value))

    for scene in scenes:
        input_filename = os.path.join(SCENES_DIR, scene)
        output_filename = os.path.join(OUTPUT_DIR, "b{}_".format(value) + scene)

        subprocess.run(["convert", input_filename, "-brightness-contrast", str(value), output_filename])

# os.makedirs(OUTPUT_DIR2, exist_ok=True)

# for value in range(-100, 0):

#     print("value: {}".format(value))

#     input_filename = "brightframe.jpg"
#     output_filename = os.path.join(OUTPUT_DIR2, "b{}_brightframe.jpg".format(value))

#     subprocess.run(["convert", input_filename, "-brightness-contrast", str(value), output_filename])


