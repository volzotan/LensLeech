import subprocess
import os
import pathlib

# camera_type = "brightframe_picamera"
# camera_type = "brightframe_android"
# camera_type = "brightframe_gphoto"
# camera_type = "brightframe_webcam"

# camera_type = "picamera"
# camera_type = "webcam"
# camera_type = "android"
# camera_type = "gphoto"
camera_type = "stillcam"

IMAGE_DIR   = "output_{}".format(camera_type)
JSON_DIR    = "output_{}_json".format(camera_type)

OVERRIDE = True

os.makedirs(JSON_DIR, exist_ok=True)

images = [f for f in os.listdir(IMAGE_DIR) if os.path.isfile(os.path.join(IMAGE_DIR, f))]
current_path = pathlib.Path().resolve()

for i in range(0, len(images)):
    img = images[i]

    if not img.endswith("jpg"):
        print("skipping unknown file: {}".format(img))
        continue

    output_filename = os.path.join(current_path, JSON_DIR, "{}.json".format(img))

    if not OVERRIDE and os.path.exists(output_filename):
        print("skipping already existing file: {}".format(img))
        continue

    print("{} / {} | processing: {}".format(i, len(images), img))

    cmd = ["python3", "detect.py",
        "--input-dir", os.path.join(current_path, IMAGE_DIR), 
        "--input-file", img, 
        "--output-dir", os.path.join(current_path, JSON_DIR), "--write", 
        "--output-data", output_filename]

    if camera_type == "android":
        cmd.append("--rotate90")

    subprocess.run(cmd, shell=False, check=True, cwd="../../processing_pattern")

    # exit()