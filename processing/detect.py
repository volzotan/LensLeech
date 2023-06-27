import sys
import logging as log
import math
import datetime
import json
import os

import argparse
import socket
from pathlib import Path

import numpy as np
import numpy.ma as ma
import cv2

from skimage.morphology import disk
import matplotlib.pyplot as plt

import scipy
import circle_fit

INPUT_DIR           = "video"
OUTPUT_DIR          = "video_processed"

INPUT_FILE          = "A6000_10mm_960px.mp4"

MAP_FILE            = "2678_data_3_i-1725881.json"
# MAP_FILE            = "2633_data_0_i-1303443.json"

SVG_FILE            = "debug.svg"
DATA_FILE           = "detections.json"

GROUND_TRUTH_FILE   = "../blender/ground_truth.json"
ERROR_FILE          = "error.json"

UDP_ADDR_RX         = ""
UDP_PORT_RX         = 5004

UDP_ADDR_TX         = "192.168.178.255"
UDP_PORT_TX         = 5005

IMAGE_DIMENSIONS    = [960, 540]

# --------------------------------------------------

SEGMENTATION_HSV    = "hsv"
SEGMENTATION_SOTSU  = "singleotsu"
SEGMENTATION_DOTSU  = "doubleotsu"

# --------------------------------------------------

THRESHOLD_SQUEEZE   = 0.25

THRESHOLD_PRESS     = 0.05
ROLLING_BUFFER_LEN  = 60

MIN_DETECTED_KEYPOINTS = 3

SEGMENTATION        = SEGMENTATION_DOTSU

UNDISTORT           = True
CROP_CIRCLE         = False

# OUTPUT_FRAMERATE    = 30.027
OUTPUT_FRAMERATE    = 25

# --------------------------------------------------

# DEBUG

DRAW_LABELS         = False
EXPORT_MAP          = False

# --------------------------------------------------

MAX_ROT             = 6

COLORS              = [(255, 0, 0), (0, 255, 0)]

font                = cv2.FONT_HERSHEY_SIMPLEX
font_scale          = 1.0
font_scale_med      = 0.75
font_scale_small    = 0.5
font_color          = (255, 255, 255)
font_thickness      = 2
font_thickness_med  = 1

kernel3 = np.ones((3, 3), np.uint8)
kernel5 = np.ones((5, 5), np.uint8)
kernel7 = np.ones((10, 10), np.uint8)

map_data = {}
with open(MAP_FILE, "r") as f:
    map_data = json.load(f)

lookup = map_data["lookup_table"]

neighbour_distances_map = {}
for qrs in lookup.values():
    neighbour_distances_map["{}|{}|{}".format(*qrs)] = np.zeros([ROLLING_BUFFER_LEN])
    neighbour_distances_map["{}|{}|{}".format(*qrs)][:] = np.nan
event_squeeze       = 0
event_press         = 0

ground_truth = None
error = []

circlemask = np.zeros([540, 960], dtype=np.uint8)
cv2.circle(circlemask, [960//2, 540//2], (540-60)//2, (255, 255, 255), -1)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)

# --------------------------------------------------

params_round = cv2.SimpleBlobDetector_Params()

params_round.minDistBetweenBlobs = 15 #30

params_round.filterByColor = False

params_round.filterByArea = True
params_round.minArea = 200
params_round.maxArea = 5000

# resized
# params_round.minArea = 120
# params_round.maxArea = 1000

params_round.filterByInertia = True 
params_round.minInertiaRatio = 0.3
params_round.maxInertiaRatio = 1.0

params_round.filterByConvexity = True
params_round.minConvexity = 0.5
params_round.maxConvexity = 1.0

detector_round = cv2.SimpleBlobDetector_create(params_round)

# --------------------------------------------------

distortion_coeff = np.zeros([1, 5], dtype=np.float64)
distortion_coeff[0, 0] = 3.0 #1.3

camera_matrix = np.identity(3)
camera_matrix[0, 2] = IMAGE_DIMENSIONS[0]/2
camera_matrix[1, 2] = IMAGE_DIMENSIONS[1]/2

camera_matrix[0, 0] = IMAGE_DIMENSIONS[0]
camera_matrix[1, 1] = camera_matrix[0, 0]

# --------------------------------------------------

def prepare_output_frame(channel1, channel2, channel3, channel4):

    output_frame = np.zeros((1080, 1920, 3), np.uint8)    

    output_frame[0:540, 0:960]  = channel1 # top left
    output_frame[0:540, 960:]   = channel2 # top right 
    output_frame[540:, 0:960]   = channel3 # bottom left
    output_frame[540:, 960:]    = channel4 # bottom right

    if DRAW_LABELS:
        label_channel2 = "marker points"
        label_channel3 = "filtered"
        label_channel4 = "processed"

        offset = (12, 35)
        output_frame = cv2.putText(output_frame, "input", (offset[0], offset[1]),                   font, font_scale, (0, 0, 0), font_thickness+10, cv2.LINE_AA)
        output_frame = cv2.putText(output_frame, label_channel2, (960+offset[0], offset[1]),        font, font_scale, (0, 0, 0), font_thickness+10, cv2.LINE_AA)
        output_frame = cv2.putText(output_frame, label_channel3, (offset[0], 540+offset[1]),        font, font_scale, (0, 0, 0), font_thickness+10, cv2.LINE_AA)
        output_frame = cv2.putText(output_frame, label_channel4, (960+offset[0], 540+offset[1]),    font, font_scale, (0, 0, 0), font_thickness+10, cv2.LINE_AA)
        output_frame = cv2.putText(output_frame, "input", (offset[0], offset[1]),                   font, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)
        output_frame = cv2.putText(output_frame, label_channel2, (960+offset[0], offset[1]),        font, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)
        output_frame = cv2.putText(output_frame, label_channel3, (offset[0], 540+offset[1]),        font, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)
        output_frame = cv2.putText(output_frame, label_channel4, (960+offset[0], 540+offset[1]),    font, font_scale, (255, 255, 255), font_thickness, cv2.LINE_AA)

    return output_frame

def process(img, preprocessed_keypoints=None):

    info = {
        "rotation": None,
        "press": None,
        "press_values": {},
        "squeeze": None,
        "push": None,
        "found_patterns": []
    }

    # event variables
    global event_squeeze
    global event_press
    event_squeeze = event_squeeze * 0.8
    event_press = event_press * 0.8

    output_frame = None
    hsv = None 
    keypoints = None

    channel3 = img

    if img is not None:

        # undistort captured image
        if UNDISTORT:
            img = cv2.undistort(img, camera_matrix, distortion_coeff, None, None)

            crop = 0.10
            img = cv2.resize(img[
                int(540*crop/2):int(540-(540*crop/2)), 
                int(960*crop/2):int(960-(960*crop/2))], 
                (960, 540))

        if CROP_CIRCLE:
            img[circlemask == 0] = [0, 0, 0]

        hsv = cv2.cvtColor(img, cv2.COLOR_BGR2HSV)

        if SEGMENTATION == SEGMENTATION_HSV:

            # blue channel
            low_0 = [95-10, 20, 50]
            high_0 = [140, 255, 255]

            # green channel
            low_1 = [30+5, 20, 50]
            high_1 = [94-10, 255, 255]

            # red channel
            low_ring1 = [140+20, 100, 100]
            high_ring1 = [180, 255, 255]
            low_ring2 = [0, low_ring1[1], low_ring1[2]]
            high_ring2 = [30-20, 255, 255]

            image_0 = cv2.inRange(hsv, np.array(low_0), np.array(high_0))
            filtered_0 = cv2.erode(image_0, kernel3, iterations = 2)
            filtered_0 = cv2.dilate(filtered_0, kernel7, iterations = 1)
            blobs_0 = detector_round.detect(filtered_0)

            image_1 = cv2.inRange(hsv, np.array(low_1), np.array(high_1))
            filtered_1 = cv2.erode(image_1, kernel3, iterations = 2)
            filtered_1 = cv2.dilate(filtered_1, kernel7, iterations = 1)
            blobs_1 = detector_round.detect(filtered_1)

            ring_mask1 = cv2.inRange(hsv, np.array(low_ring1), np.array(high_ring1))
            ring_mask2 = cv2.inRange(hsv, np.array(low_ring2), np.array(high_ring2))
            image_ring = ring_mask1 | ring_mask2
            filtered_ring = cv2.erode(image_ring, kernel3, iterations = 2)
            filtered_ring = cv2.dilate(image_ring, kernel7, iterations = 1)

            keypoints = np.empty([len(blobs_0) + len(blobs_1), 4], float) # X, Y, size, color

            for i in range(0, len(blobs_0)):
                keypoint = blobs_0[i]
                keypoints[i, 0] = keypoint.pt[0]    # X
                keypoints[i, 1] = keypoint.pt[1]    # Y
                keypoints[i, 2] = keypoint.size     # size
                keypoints[i, 3] = 0                 # color

            for i in range(0, len(blobs_1)):
                keypoint = blobs_1[i]
                keypoints[len(blobs_0) + i, 0] = keypoint.pt[0]    # X
                keypoints[len(blobs_0) + i, 1] = keypoint.pt[1]    # Y
                keypoints[len(blobs_0) + i, 2] = keypoint.size     # size
                keypoints[len(blobs_0) + i, 3] = 1                 # color


            if args["show"] or args["write"]:
                # filtered_both = np.zeros([*filtered_0.shape, 3], dtype=np.uint8)
                filtered_both = cv2.cvtColor(cv2.split(hsv)[1], cv2.COLOR_GRAY2BGR)
                filtered_both[filtered_ring > 0, :] = (0, 0, 255)
                filtered_both[filtered_0 > 0, :]    = (255, 0, 0)
                filtered_both[filtered_1 > 0, :]    = (0, 255, 0)
                channel3 = filtered_both

        elif SEGMENTATION in [SEGMENTATION_SOTSU, SEGMENTATION_DOTSU]:

            resize_factor = 1
            # resize_shape = [img.shape[1]//resize_factor, img.shape[0]//resize_factor]
            # hsv_resized = cv2.resize(hsv, resize_shape, interpolation=cv2.INTER_AREA)
            hsv_resized = hsv

            blobmask_resized = None

            if SEGMENTATION == SEGMENTATION_SOTSU:

                low_0 = [30, 10, 20]
                high_0 = [140, 255, 255]

                image_0 = cv2.inRange(hsv_resized, np.array(low_0), np.array(high_0))

                x_low_0 = [30, 10, 180]
                x_high_0 = [140, 20, 255]

                image_0_x = cv2.inRange(hsv_resized, np.array(x_low_0), np.array(x_high_0))
                image_0[image_0_x > 0] = 0

                filtered_0 = cv2.erode(image_0, kernel3, iterations = 2)
                filtered_0 = cv2.dilate(filtered_0, kernel3, iterations = 1)

                blobmask_resized = filtered_0

            elif SEGMENTATION == SEGMENTATION_DOTSU:

                low_0 = [20, 0, 50]
                high_0 = [150, 255, 255]

                img_range = cv2.inRange(hsv_resized, np.array(low_0), np.array(high_0))

                filtered = cv2.erode(img_range, kernel3, iterations = 2)
                filtered = cv2.dilate(filtered, kernel3, iterations = 1)

                segmented_only_v = hsv_resized[:, :, 2]
                segmented_only_v[filtered == 0] = 255

                segmented_only_v = cv2.erode(segmented_only_v, kernel3, iterations = 2)
                segmented_only_v = cv2.dilate(segmented_only_v, kernel3, iterations = 1)

                ret, th_mask = cv2.threshold(segmented_only_v, 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)

                th_mask = ~th_mask # invert the image for analysis

                blobmask_resized = th_mask

            detections = detector_round.detect(blobmask_resized)
            keypoints = np.zeros([len(detections), 4], dtype=float)
            blobs = np.zeros([len(detections), 3], dtype=float)

            if len(detections) >= 2:
    
                for i in range(0, len(detections)):

                    # centroid patch color
                    row = int(detections[i].pt[1])
                    col = int(detections[i].pt[0])

                    patch_rad = 10

                    row_min = max(row-patch_rad, 0)
                    col_min = max(col-patch_rad, 0)
                    row_max = min(row+patch_rad, hsv_resized.shape[0])
                    col_max = min(col+patch_rad, hsv_resized.shape[1])
                    centroid_region = hsv_resized[row_min:row_max+1, col_min:col_max+1, :]
                    blobs[i] = np.mean(centroid_region, axis=(0, 1))

                # blobs_otsu = np.asarray(blobs + blobs_stuffing, dtype=np.uint8)
                th_value_h, th_mask_h = cv2.threshold(blobs[:, 0].astype(dtype=np.uint8), 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)
                th_value_s, th_mask_s = cv2.threshold(blobs[:, 1].astype(dtype=np.uint8), 0, 255, cv2.THRESH_BINARY+cv2.THRESH_OTSU)

                for i in range(0, len(detections)):

                    keypoints[i, 0] = detections[i].pt[0] * resize_factor
                    keypoints[i, 1] = detections[i].pt[1] * resize_factor
                    keypoints[i, 2] = 30
                
                    # otsu

                    # only H
                    if blobs[i, 0] > th_value_h:
                        keypoints[i, 3] = 0
                    else:
                        keypoints[i, 3] = 1  

            if args["show"] or args["write"]:

                # show patches with color indicator point in the center
      
                channel3 = cv2.resize(cv2.cvtColor(blobmask_resized, cv2.COLOR_GRAY2BGR), [img.shape[1], img.shape[0]], interpolation=cv2.INTER_AREA)
 
                for i in range(0, len(keypoints)):
                    keypoint = keypoints[i]

                    c = np.zeros([1, 1, 3], dtype=np.uint8)
                    c[0, 0, :] = [int(blobs[i, 0]), 255, 255] # viz only Hue channel
                    c = cv2.cvtColor(c, cv2.COLOR_HSV2BGR)
                    c = c[0, 0].tolist()
                    cv2.circle(channel3, [int(keypoint[0]), int(keypoint[1])], int(keypoint[2]/2)*2, c, -1)

                for i in range(0, len(keypoints)):
                    cv2.circle(channel3, [int(keypoints[i][0]), int(keypoints[i][1])], 8, COLORS[int(keypoints[i][3])], -1)

        else:
            log.error("unknown segmentation: {}".format(SEGMENTATION))
            sys.exit(-1)

    else:

        img = np.zeros([540, 960, 3], dtype=np.uint8)
        hsv = np.zeros([540, 960, 3], dtype=np.uint8)

        channel3 = img

        keypoints = np.empty([len(preprocessed_keypoints), 4], float) # X, Y, size, color

        for i in range(0, len(preprocessed_keypoints)):
            keypoints[i][0] = preprocessed_keypoints[i][0] + 960/2
            keypoints[i][1] = preprocessed_keypoints[i][1] + 540/2
            keypoints[i][2] = preprocessed_keypoints[i][2]
            keypoints[i][3] = preprocessed_keypoints[i][3]


    if args["show"] or args["write"]:

        image_with_keypoints = cv2.cvtColor(cv2.cvtColor(img, cv2.COLOR_BGR2GRAY), cv2.COLOR_GRAY2BGR) 
        info_img = np.zeros((540, 960, 3), np.uint8)

        channel1 = img
        channel2 = image_with_keypoints
        channel4 = info_img

        output_frame = prepare_output_frame(channel1, channel2, channel3, channel4)

    if keypoints.shape[0] <= 7:
        return output_frame, info

    # NEIGHBOURS

    # rows: keypoints, columns: rotation positions, depth: QRS hexagon coordinates
    rotation_pos = np.zeros([keypoints.shape[0], MAX_ROT, 3], dtype=int)
    rotation_pos_valid = np.zeros([keypoints.shape[0], MAX_ROT], dtype=bool)

    # keypoints, rotation positions, neighbours keypoint index
    neighbour_pos = np.zeros([keypoints.shape[0], MAX_ROT, 6], dtype=int)

    # keypoints
    avg_circularity = np.full([keypoints.shape[0]], np.nan)
    neighbour_distances = np.full([keypoints.shape[0]], np.nan)
    neighbour_distances_diffratio = np.full([keypoints.shape[0]], np.nan)

    distances = scipy.spatial.distance.cdist(keypoints[:, 0:2], keypoints[:, 0:2])

    for i in range(0, keypoints.shape[0]):

        neighbour_indices = np.argsort(distances[i])[1:7]

        # sanity check: is the main blob really in the center? If not the blob lies on the border of the image
        if abs(np.mean(keypoints[neighbour_indices, 0]) - keypoints[i, 0]) > 20 or abs(np.mean(keypoints[neighbour_indices, 1]) - keypoints[i, 1]) > 20:
            continue

        neighbour_order = np.argsort([get_rot(*keypoints[ind, 0:2], offset=keypoints[i, 0:2]) for ind in neighbour_indices]) # order ascending
        # order is ascending, so counter-clockwise, but values are stored 
        # clockwise (flat top hex, starting at 1 o'clock). So reverse array:
        neighbour_order = np.flip(neighbour_order)

        # calculate circularity for squeeze
        distances_neighbours = scipy.spatial.distance.cdist(keypoints[neighbour_indices[neighbour_order], 0:2], [keypoints[i, 0:2]]) # distance from center to neighbours
        mean_distances_neighbours = np.mean(distances_neighbours)

        # sanity check 2: does the pattern include an outlier neighbour? (happens when a single point was lost during blob detection)
        if np.max(distances_neighbours) > mean_distances_neighbours * 1.20:
            continue

        # ratio of diff of min/max distance
        avg_circularity[i] = ((np.max(distances_neighbours)-np.min(distances_neighbours))/mean_distances_neighbours)
        neighbour_distances[i] = mean_distances_neighbours

        for rot_step in range(0, 6):

            pattern = [keypoints[i, 3]]

            rotated_order = np.roll(neighbour_order, rot_step)
            for n_index in rotated_order:
                pattern.append(keypoints[neighbour_indices[n_index], 3])

            pattern_pos = find_in_table(pattern)

            if not pattern_pos is None:
                rotation_pos[i, rot_step] = pattern_pos
                neighbour_pos[i, rot_step] = [neighbour_indices[ind] for ind in rotated_order]
                rotation_pos_valid[i, rot_step] = True


    matching_neighbours = np.zeros([keypoints.shape[0], 6], dtype=int)

    for i in range(0, rotation_pos.shape[0]):
        for rot_step in range(0, rotation_pos.shape[1]):

            if not rotation_pos_valid[i, rot_step]:
                continue

            # check if all keypoint neighbours are real neighbours on the map as well
            detected_keypoint = keypoints[i]
            neighbours_of_detected_keypoint = neighbour_pos[i][rot_step]
            hex_coordinate_of_detected_keypoint = rotation_pos[i, rot_step]           
            hex_coordinates_of_map_neighbours = get_neighbours(*hex_coordinate_of_detected_keypoint)

            for ind in neighbours_of_detected_keypoint:

                if not rotation_pos_valid[ind, rot_step]:
                    continue

                hex_coordinates_of_detected_keypoints_neighbour = rotation_pos[ind, rot_step]

                if hex_coordinates_of_detected_keypoints_neighbour.tolist() in hex_coordinates_of_map_neighbours:
                    matching_neighbours[i, rot_step] += 1

    rot_values = np.argmax(matching_neighbours, axis=1)

    # min number of confirmed neighbours to be valid
    rotation_pos_valid[np.max(matching_neighbours, axis=1) <= 3] = False

    map_detected = {}
    for i in range(0, rot_values.shape[0]):
        map_detected["{}|{}|{}".format(*rotation_pos[i, rot_values[i]])] = True  

    # using rot_values as a list of indices to filter along the second dimensions (ie. column) requires 
    # take_along_axis as well as expand_dims to match dimensions
    num_detected_keypoints = np.count_nonzero(np.take_along_axis(rotation_pos_valid, np.expand_dims(rot_values, axis=1), axis=1)) 

    if num_detected_keypoints < MIN_DETECTED_KEYPOINTS:
        return output_frame, info

    for i in range(0, keypoints.shape[0]):

        if not rotation_pos_valid[i, rot_values[i]]:
            continue

        qrs = rotation_pos[i, rot_values[i]]
        
        # circular buffer for cheap (TODO: basically anything else would be faster)
        buffer = neighbour_distances_map["{}|{}|{}".format(*qrs)]
        buffer = np.roll(neighbour_distances_map["{}|{}|{}".format(*qrs)], -1)
        buffer[-1] = neighbour_distances[i]
        neighbour_distances_map["{}|{}|{}".format(*qrs)] = buffer

    # calculate rotation

    blob_rot = None
    src = []
    dst = []
    for i in range(0, keypoints.shape[0]):
        if not rotation_pos_valid[i, rot_values[i]]:
            continue

        # flip Y axis (math coordinate system is bottom left)
        # normalization not necessary, that's done by align_vectors()
        src.append([keypoints[i, 0], 540-keypoints[i, 1], 0])

        x, y = pointy_hex_to_pixel(*rotation_pos[i, rot_values[i]])

        dst.append([x, y, 0])         

    src = np.asarray(src, dtype=float)
    dst = np.asarray(dst, dtype=float)

    # center around origin (scipy's Kabsch algorithm does not do that)
    src = src - np.mean(src, axis=0)
    dst = dst - np.mean(dst, axis=0)

    try:
        # align_vectors() is scipy's wrapper for Kabsch's algorithm
        estimated_rot, rmsd = scipy.spatial.transform.Rotation.align_vectors(dst, src)

        blob_rot = estimated_rot.as_euler("XYZ")

        if math.isclose(blob_rot[0], 180):
            blob_rot = None
        elif blob_rot[2] < 0:
            blob_rot = math.tau + blob_rot[2]
        else:
            blob_rot = blob_rot[2]
    except Exception as e:
        log.error("processing rotation failed: {}".format(e))

    if args["ground_truth"]:
        error.append({
            "frame": frame_counter, 
            "rotation": blob_rot, 
            "rotation_deg": math.degrees(blob_rot), 
            "gt_rotation": ground_truth[frame_counter]["rotation"],
            "gt_rotation_deg": math.degrees(ground_truth[frame_counter]["rotation"]),
        })

    info["rotation"] = blob_rot

    # detect squeeze

    if np.nanmean(avg_circularity) > THRESHOLD_SQUEEZE:
        event_squeeze += 1

    if event_squeeze >= 2:
        info["squeeze"] = True
    else:
        info["squeeze"] = False

    # detect press

    if np.count_nonzero(neighbour_distances) > 0:
        max_patterns = []
        max_patterns_neighbours = []

        for i in range(0, keypoints.shape[0]):
            if np.isnan(neighbour_distances[i]):
                continue

            qrs = rotation_pos[i, rot_values[i]]
            key = "{}|{}|{}".format(*qrs)
            mean = np.nanmean(neighbour_distances_map[key])

            if not np.isnan(mean):
                val = (neighbour_distances[i] - mean)/mean

                neighbour_distances_diffratio[i] = val
                info["press_values"][key] = val

                if val > THRESHOLD_PRESS:
                    max_patterns.append(key)
                    max_patterns_neighbours.append(get_neighbours_keys(*qrs)) # TODO: uargh

        for i in range(0, len(max_patterns)):

            count = 0

            for n in max_patterns_neighbours[i]:
                if n in max_patterns:
                    count += 1

            if count >= 5:
                event_press += 1

        if event_press >= 2:
            info["press"] = True
        else:
            info["press"] = False

    # detect push

    # CENTROID OF ALL DETECTED POINTS

    pos = np.zeros([2], dtype=float)
    for i in range(0, keypoints.shape[0]):
        if not rotation_pos_valid[i, rot_values[i]]:
            continue

        pos = np.add(pos, keypoints[i, 0:2])

    if num_detected_keypoints > 3:
        pos /= num_detected_keypoints
        
        # normalize for square with a side length of image width
        # caveat: number will exceed [-1, 1] for diagonals

        pos = [
            (pos[0]-IMAGE_DIMENSIONS[0]/2)/(IMAGE_DIMENSIONS[0]/2)*-1,
            (pos[1]-IMAGE_DIMENSIONS[1]/2)/(IMAGE_DIMENSIONS[0]/2)*-1,
        ]

        info["push"] = pos

    # viz
    if args["show"] or args["write"]:

        info_img[:] = (77, 77, 77)

        if info["press"]:
            info_img[:] = (0, 0, 120)

        if info["squeeze"]:
            info_img[:] = (0, 120, 0)

        for i in range(0, keypoints.shape[0]):
            if rotation_pos_valid[i][rot_values[i]]:
                # cv2.circle(image_with_keypoints, [int(keypoints[i][0]), int(keypoints[i][1])], int(keypoints[i][2]/2), (255, 255, 255), -1)
                cv2.circle(image_with_keypoints, [int(keypoints[i][0]), int(keypoints[i][1])], 8, (255, 255, 255), -1)
            else:
                # cv2.circle(image_with_keypoints, [int(keypoints[i][0]), int(keypoints[i][1])], int(keypoints[i][2]/2), (0, 0, 0), -1)
                cv2.circle(image_with_keypoints, [int(keypoints[i][0]), int(keypoints[i][1])], 8, (0, 0, 0), -1)

        for i in range(keypoints.shape[0]):
            color = (255, 0, 0)
            if keypoints[i, 3] == 1:
                color = (0, 255, 0)

            cv2.circle(image_with_keypoints, [int(keypoints[i, 0]), int(keypoints[i, 1])], int(keypoints[i, 2]/2), color, 4)

        # map detections
        dist = 10

        for key in map_data["data"]:
            q, r, s = [int(c) for c in key.split("|")]
            x, y = pointy_hex_to_pixel(q, r, s, hex_size=dist, center=[960-150, 540-140])

            color = (0, 0, 0)
            if map_data["data"][key] == 0:
                color = (50, 0, 0)
            elif map_data["data"][key] == 1:
                color = (0, 50, 0)

            if key in map_detected:
                color = [255 if c > 0 else 0 for c in color]

            cv2.circle(info_img, [int(x), int(y)], 6, color, -1)

        if EXPORT_MAP:

            export_dist = 40
            export_diam = 25

            map_image = np.zeros([1000, 1000, 4], dtype=np.uint8)

            for key in map_data["data"]:
                q, r, s = [int(c) for c in key.split("|")]
                x, y = pointy_hex_to_pixel(q, r, s, hex_size=export_dist, center=[1000//2, 1000//2])

                color = (0, 0, 0)
                if map_data["data"][key] == 0:
                    color = (100, 0, 0, 90)
                elif map_data["data"][key] == 1:
                    color = (0, 100, 0, 90)

                if key in map_detected:
                    color = [255 if c > 0 else 0 for c in color]

                cv2.circle(map_image, [int(x), int(y)], export_diam, color, -1)

            cv2.imwrite(os.path.join("export_map", "{}.png".format(frame_counter)), map_image)

            # fill empty images in sequence   
            map_image = np.zeros([1000, 1000, 4], dtype=np.uint8)
            for key in map_data["data"]:
                q, r, s = [int(c) for c in key.split("|")]
                x, y = pointy_hex_to_pixel(q, r, s, hex_size=export_dist, center=[1000//2, 1000//2])
                
                color = (0, 0, 0)
                if map_data["data"][key] == 0:
                    color = (100, 0, 0, 90)
                elif map_data["data"][key] == 1:
                    color = (0, 100, 0, 90)

                cv2.circle(map_image, [int(x), int(y)], export_diam, color, -1)

            for i in range(0, frame_counter):
                filename = os.path.join("export_map", "{}.png".format(i))
                if not os.path.exists(filename):
                    cv2.imwrite(filename, map_image)

        # map pressure

        for key in map_data["data"]:
            q, r, s = [int(c) for c in key.split("|")]
            x, y = pointy_hex_to_pixel(q, r, s, hex_size=dist, center=[960-150, 140])

            color = [128, 128, 128]

            val = 0
            if key in info["press_values"]:
                val = info["press_values"][key] * 1000
                color = (128, 128+val, 128-val)

                if info["press_values"][key] > THRESHOLD_PRESS:
                    color = (255, 255, 255)

            color = [255 if c > 255 else int(c) for c in color]            
            cv2.circle(info_img, [int(x), int(y)], 6, color, -1)

        # rotation

        if blob_rot is not None:

            angle = math.degrees(blob_rot)
            cv2.putText(info_img, "Rotation: {:5.2f} deg".format(angle), (10, 100), font, font_scale, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.line(channel2, (960//2, 540//2), (int(960/2+300*math.cos(blob_rot)), int(540/2+300* math.sin(blob_rot))), (255, 255, 255), thickness=10)

            if args["ground_truth"]:
                gt = math.degrees(ground_truth[frame_counter]["rotation"])
                cv2.putText(info_img, 
                    "gt: {:5.2f} | diff: {:5.2f}".format(gt, angle-gt, -1), 
                    (400, 100), font, font_scale, (255, 255, 255), 2, cv2.LINE_AA)

            cv2.rectangle(channel2, (30, 540-50-30), (30+290, 540-30), (255, 255, 255), -1)
            # cv2.rectangle(channel2, (30, 540-50-30), (30+290, 540-30), (50, 50, 50), 2)
            cv2.putText(channel2, "Rotation: {:6.2f} deg".format(angle), (30+15, 540-30-16), font, font_scale_med, (0, 0, 0), font_thickness_med, cv2.LINE_AA)

        # squeeze

        if np.count_nonzero(avg_circularity) > 0:

            cv2.putText(info_img, "Avg circularity: {:5.2f}".format(np.nanmean(avg_circularity)), (10, 200), font, font_scale, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(info_img, "Squeeze: {}".format("X" if info["squeeze"] else "_"), (10, 250), font, font_scale, (255, 255, 255), 2, cv2.LINE_AA)

            if info["squeeze"]:
                cv2.rectangle(channel2, (320+15, 540-50-30), (335+140, 540-30), (255, 255, 255), -1)
                cv2.putText(channel2, "Squeeze".format(angle), (325+30, 540-30-16), font, font_scale_med, (0, 0, 0), font_thickness_med, cv2.LINE_AA)

        # press

        if np.count_nonzero(neighbour_distances) > 0:

            cv2.putText(info_img, "Distances: {:5.0f} | {:5.0f} | {:5.0f}".format(
                np.nanmin(neighbour_distances), 
                np.nanmax(neighbour_distances), 
                np.nanmean(neighbour_distances)), (10, 350), font, font_scale, (255, 255, 255), 2, cv2.LINE_AA)
            cv2.putText(info_img, "Press: {}".format("X" if info["press"] else "_"), (10, 400), font, font_scale, (255, 255, 255), 2, cv2.LINE_AA)

            if info["press"]:
                cv2.rectangle(channel2, (320+15, 540-50-30), (335+140, 540-30), (255, 255, 255), -1)
                cv2.putText(channel2, "Press".format(angle), (325+50, 540-30-16), font, font_scale_med, (0, 0, 0), font_thickness_med, cv2.LINE_AA)

            # debug
            for i in range(0, keypoints.shape[0]):
                if not np.isnan(neighbour_distances[i]):

                    val = None
                    qrs = rotation_pos[i, rot_values[i]]
                    val = neighbour_distances_diffratio[i] * 100

                    if val is not None and abs(val) > 5:
                        cv2.putText(image_with_keypoints, "{:3.0f}".format(val), 
                            (int(keypoints[i, 0]-18), int(keypoints[i, 1]+5)), font, font_scale_small, (0, 0, 0), 1+5, cv2.LINE_AA)
                        cv2.putText(image_with_keypoints, "{:3.0f}".format(val), 
                            (int(keypoints[i, 0]-18), int(keypoints[i, 1]+5)), font, font_scale_small, (255, 255, 255), 1, cv2.LINE_AA)

        # push

        if info["push"] is not None:
            if abs(info["push"][0])+abs(info["push"][1]) > 0.2 and (args["show"] or args["write"]):
                cv2.line(channel2, 
                    (960//2, 540//2), 
                    (int(960/2 + pos[0]*960/2), int(540/2 + pos[1]*960/2)), 
                    (0, 0, 255), thickness=10)

        output_frame = prepare_output_frame(channel1, channel2, channel3, channel4)

    if args["svg"] is True:
        write_svg(keypoints, rotation_pos, rotation_pos_valid, rot_values)

    for key in map_data["data"]:
        if key in map_detected:
            info["found_patterns"].append(key)

    return output_frame, info


def pointy_hex_to_pixel(q, r, s, hex_size=1, center=[0, 0]):
    x = hex_size * (math.sqrt(3) * q + math.sqrt(3)/2 * r)
    y = hex_size * (3./2 * r)
    return (x + center[0], y + center[1])


def find_in_table(values):

    try:
        key = " ".join([str(int(x)) for x in values])
        return lookup[key]
    except KeyError as ke:
        return None


def get_rot(x, y, offset=(0, 0)): # returns turn (1 = full rotation)
    deg = 0

    # y = ((offset[0]*2)-y - offset[1]) # flip Y axis to bottom 0
    y = (y - offset[1])
    x = (x - offset[0])

    turn = math.atan2(y, x) - math.pi # atan2 [PI, -PI]
    return -(turn / math.tau)


def get_neighbours(q, r, s):
    return [
        [q+1, r-1, s+0], # top right (1 o'clock)
        [q+1, r+0, s-1], # right (3 o'clock)
        [q+0, r+1, s-1], # ...
        [q-1, r+1, s+0],
        [q-1, r+0, s+1],
        [q+0, r-1, s+1], # top left (11 o'clock)
    ]

def get_neighbours_keys(q, r, s):
    return ["{}|{}|{}".format(*qrs) for qrs in get_neighbours(q, r, s)]


def write_svg(keypoints, rotation_pos, rotation_pos_valid, rot_values):

    with open(SVG_FILE, "w") as f:

        f.write("<?xml version=\"1.0\" encoding=\"utf-8\" ?>\n")
        f.write("<?xml-stylesheet href=\"style.css\" type=\"text/css\" title=\"main_stylesheet\" alternate=\"no\" media=\"screen\" ?>\n")
        f.write("<svg baseProfile=\"tiny\" version=\"1.2\" width=\"{}{}\" height=\"{}{}\" \n".format(960, "px", 540, "px"))
        f.write("xmlns=\"http://www.w3.org/2000/svg\" xmlns:ev=\"http://www.w3.org/2001/xml-events\" xmlns:xlink=\"http://www.w3.org/1999/xlink\" \n")
        f.write("xmlns:inkscape=\"http://www.inkscape.org/namespaces/inkscape\"")
        f.write(">\n")
        f.write("<defs />\n")

        f.write("<style>\n")
        # f.write(".blob {opacity: 0.1;}")
        # for i in range(0, len(keypoints)):
        #     f.write(".map-blob-{}:hover ~ .blob-{} {{opacity: 1.0;}}\n".format(i, i))
        #     f.write(".map-blob-{}:hover {{opacity: 0.0;}}\n".format(i, i))
        f.write("</style>\n")

        # layer base
        f.write("<g inkscape:groupmode=\"layer\" id=\"{}\" inkscape:label=\"{}\">\n".format("layer1", "base"))
        for i in range(0, len(keypoints)):
            p = keypoints[i]

            color = "blue"
            if p[3] == 1:
                color = "green"

            f.write("<circle cx=\"{}\" cy=\"{}\" r=\"{}\" fill=\"{}\"/>\n".format(p[0], p[1], p[2]/2, color))
        f.write("</g>")
            
        # layer keypoint ID
        f.write("<g inkscape:groupmode=\"layer\" id=\"{}\" inkscape:label=\"{}\">\n".format("layer2", "keypoint IDs"))
        for i in range(0, len(keypoints)):
            p = keypoints[i]
            f.write("<text x=\"{}\" y=\"{}\" text-anchor=\"middle\" fill=\"white\">{}</text>".format(p[0], p[1]+5, str(i)))
        f.write("</g>")

        # layer map
        f.write("<g inkscape:groupmode=\"layer\" id=\"{}\" inkscape:label=\"{}\">\n".format("layer3", "map"))

        dist = 8
        center = [960-80, 540-70]

        for key in map_data["data"].keys():
            q, r, s = [int(c) for c in key.split("|")]
            x, y = pointy_hex_to_pixel(q, r, s, hex_size=dist, center=center)

            color = "blue"
            if map_data["data"][key] == 1:
                color = "green"
            
            # cv2.circle(info_img, [offset[0]+dist*l, offset[1]+dist*k], 6, color, -1)
            f.write("<circle cx=\"{}\" cy=\"{}\" r=\"{}\" fill=\"{}\" opacity=\"0.25\" />\n".format(x, y, 4, color))

        f.write("</g>")        

        # layer map blobs
        f.write("<g inkscape:groupmode=\"layer\" id=\"{}\" inkscape:label=\"{}\" >\n".format("layer4", "map blob"))
        for i in range(0, rotation_pos.shape[0]):

            if not rotation_pos_valid[i, rot_values[i]]:
                continue

            q, r, s = rotation_pos[i, rot_values[i]]

            color="blue"
            if map_data["data"]["{}|{}|{}".format(q, r, s)]:
                color = "green"

            x, y = pointy_hex_to_pixel(q, r, s, hex_size=dist, center=center)

            f.write("<circle cx=\"{}\" cy=\"{}\" r=\"{}\" fill=\"{}\" opacity=\"1.0\" class=\"map-blob map-blob-{}\" ".format(x, y, 4, color, i))
            f.write("onmouseover=\"document.getElementById('blob-{}').style.opacity = 1.0;\" ".format(i))
            f.write("onmouseout=\"document.getElementById('blob-{}').style.opacity = 0.0;\" ".format(i))
            f.write("/>\n")

        f.write("</g>\n")

        # layer blobs
        for i in range(0, rotation_pos.shape[0]):

            if not rotation_pos_valid[i, rot_values[i]]:
                continue

            # use display:none to set the layer to disabled in inkscape
            f.write("<g inkscape:groupmode=\"layer\" id=\"blob-{}\" opacity=\"0.0\" inkscape:label=\"blob {}\" >\n".format(i, i))
            
            rot_value = rot_values[i]

            p = keypoints[i]
            f.write("<circle cx=\"{}\" cy=\"{}\" r=\"{}\" fill=\"none\" stroke-width=\"5\" stroke=\"red\" class=\"blob\" />\n".format(p[0], p[1], p[2]/2))

            q, r, s = rotation_pos[i, rot_values[i]]

            f.write("<text x=\"800\" y=\"300\" text-anchor=\"left\" fill=\"black\">rotation: {}</text>".format(rot_value))
            f.write("<text x=\"800\" y=\"320\" text-anchor=\"left\" fill=\"black\">coordinates: {:5.1f} {:5.1f}</text>".format(keypoints[i, 0], (keypoints[i, 1])))
            f.write("<text x=\"800\" y=\"340\" text-anchor=\"left\" fill=\"black\">hex: {}, {}, {}</text>".format(q, r, s))


            # correct detected snippet for info box
            dist = 22
            center = [880, 200]
            neighbours = get_neighbours(q, r, s)

            offset = pointy_hex_to_pixel(q, r, s, hex_size=dist)
            center = [center[0]-offset[0], center[1]-offset[1]]

            for c in [[q, r, s]] + neighbours:

                x, y = pointy_hex_to_pixel(*c, hex_size=dist, center=center)

                color = "blue"
                if map_data["data"]["{}|{}|{}".format(*c)] == 1:
                    color = "green"

                f.write("<circle cx=\"{}\" cy=\"{}\" r=\"{}\" fill=\"{}\" opacity=\"0.25\" />\n".format(x, y, 10, color))

             
            f.write("</g>\n")


        # layer blobs
        # for i in range(0, rotation_pos.shape[0]):

        #     if found_map_positions[i][0] is ma.masked:
        #         continue

        #     # use display:none to set the layer to disabled in inkscape
        #     f.write("<g inkscape:groupmode=\"layer\" id=\"{}\" inkscape:label=\"{}\" style=\"display:none\" >\n".format("layer{}".format(3+1+i), "blob {}".format(i)))
            
        #     # rot_value = rot_values[i]

        #     # print(found_torus_positions)
        #     # sys.exit()

        #     p = keypoints[i]
        #     f.write("<circle cx=\"{}\" cy=\"{}\" r=\"{}\" fill=\"none\" stroke-width=\"5\" stroke=\"red\"/>\n".format(p[0], p[1], p[2]/2, color))

        #     q, r, s = found_map_positions[i]

        #     color="red"

        #     dist = 10
        #     x, y = pointy_hex_to_pixel(q, r, s, hex_size=dist, center=[960-50, 540-50])

        #     f.write("<circle cx=\"{}\" cy=\"{}\" r=\"{}\" fill=\"{}\" opacity=\"0.5\" />\n".format(x, y, 3, color))

        #     f.write("</g>\n")

        # ---

        f.write("<script type=\"text/javascript\"><![CDATA[")
        with open("include.script") as external_script:
            f.write(external_script.read())
        f.write("]]></script>")

        f.write("</svg>\n")
        log.info("written to file: {}".format(SVG_FILE)) 


def send(info):

    try:
        # remove press values
        info.pop("press_values", None)
        msg = json.dumps(info).encode("utf-8")
        sock.sendto(msg, (UDP_ADDR_TX, UDP_PORT_TX))

    except Exception as e:
        log.warn("sending failed: {}".format(e))


if __name__ == "__main__":

    # create logger
    root = log.getLogger()
    root.setLevel(log.DEBUG)
    log.basicConfig(level=log.DEBUG)
    root_handler = root.handlers[0]
    formatter = log.Formatter("%(asctime)s | %(levelname)-7s | %(message)s")
    root_handler.setFormatter(formatter)

    ap = argparse.ArgumentParser()

    ap.add_argument("--input-file", default=INPUT_FILE, help="input file")
    ap.add_argument("--input-dir", default=INPUT_DIR, help="input dir")
    ap.add_argument("--output-dir", default=OUTPUT_DIR, help="output dir")

    ap.add_argument("--frame", default=None, help="only process the n-th frame of the video")
    ap.add_argument("--svg", action="store_true", default=False, help="output a debug SVG file")
    ap.add_argument("--write", action="store_true", default=False, help="write visualization to file")
    ap.add_argument("--show", action="store_true", default=False, help="show visualization on display")
    ap.add_argument("--rotate90", action="store_true", default=False, help="rotate the input by 90deg")
    ap.add_argument("--ground-truth", action="store_true", default=False, help="compare to a ground truth")
    ap.add_argument("--output-data", default=None, help="file name if write detection results should be written to a file")
    ap.add_argument("--webcam", action="store_true", default=False, help="capture live footage from a webcam")
    ap.add_argument("--stream", action="store_true", default=False, help="capture live footage from a stream")
    ap.add_argument("--keypoints", action="store_true", default=False, help="capture pre-processed keypoints from a stream")
    ap.add_argument("--virtualcam", action="store_true", default=False, help="capture live footage from a webcam (and pass on to virtual camera)")
    ap.add_argument("--stats", action="store_true", default=False, help="print performance statistics")

    args = vars(ap.parse_args())
    
    filename = args["input_file"].lower()

    if not os.path.exists(args["input_dir"]):
        os.makedirs(args["input_dir"])

    if not os.path.exists(args["output_dir"]):
        os.makedirs(args["output_dir"])

    if args["ground_truth"]:
        if os.path.exists(GROUND_TRUTH_FILE):
            with open(GROUND_TRUTH_FILE, "r") as f:
                ground_truth = json.load(f)
        else:
            log.error("can not compare to ground truth. File not found: {}".format(GROUND_TRUTH_FILE))
            sys.exit(-1)

    # create a new, empty data file
    if args["output_data"] is not None:
        open(args["output_data"], "w").close()

    timer_start = datetime.datetime.now()
    frame_counter = 0
    
    output_writer = None 
    full_output_filename = None

    if args["webcam"]:
        full_output_filename = os.path.join(args["output_dir"], "webcam_" + ".mp4") 
    elif args["stream"]:
        full_output_filename = os.path.join(args["output_dir"], "stream_" + ".mp4") 
    elif args["keypoints"]:
        full_output_filename = os.path.join(args["output_dir"], "keypoints_" + ".mp4") 
    else:
        full_output_filename = os.path.join(args["output_dir"], "processed_" + args["input_file"]) 

    if args["write"] and full_output_filename.endswith("mp4"):
        output_writer = cv2.VideoWriter(
            full_output_filename, 
            cv2.VideoWriter_fourcc(*"mp4v"), 
            OUTPUT_FRAMERATE, # Framerate of input video
            (1920, 1080)
        )
    
    if args["virtualcam"]:
        
        import pyvirtualcam

        cap = cv2.VideoCapture(1) # OSX wants to use device 1, device 0 does not work

        with pyvirtualcam.Camera(width=960, height=540, fps=20) as cam:
            log.info("Using virtual camera: {}".format(cam.device))

            try:
                while cap.isOpened():
                    ret, frame_cap = cap.read()

                    if frame_cap is not None:
                        resized = cv2.resize(frame_cap, [960, 540], interpolation=cv2.INTER_AREA)
                        # out = process(resized)
                        # cv2.imshow("webcam", frame_cap)
                        # cv2.waitKey(0)

                        cam.send(resized)
                    else:
                        cam.send(np.zeros([540, 960, 3], dtype=np.uint8))
                    cam.sleep_until_next_frame()
            except Exception as e:
                raise e
            finally:
                cap.release()

    elif args["webcam"]:

        cap = cv2.VideoCapture(0) # OSX wants to use device 1, device 0 does not work

        try:
            while cap.isOpened():
                ret, frame_cap = cap.read()
                resized = cv2.resize(frame_cap, [960, 540], interpolation=cv2.INTER_AREA)
                out, info = process(resized)

                send(info)

                if args["show"]:
                    cv2.imshow("output", out)
                    cv2.waitKey(1)
                if args["write"]:
                    output_writer.write(out)

        except Exception as e:
            raise e
        finally:
            cap.release()


    elif args["stream"]:

        os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "protocol_whitelist;file,rtp,udp|fflags;nobuffer|fflags;discardcorrupt|flags;low_delay|framedrop"

        # cap = cv2.VideoCapture("rtp://127.0.0.1:9000")
        cap = cv2.VideoCapture("stream.sdp")
        # cap.set(cv2.CAP_PROP_BUFFERSIZE, 1)

        try:
            while cap.isOpened():
                ret, frame_cap = cap.read()

                rotated = cv2.rotate(frame_cap, cv2.ROTATE_90_CLOCKWISE)
                resized = cv2.resize(rotated, [960, 540], interpolation=cv2.INTER_AREA)
                out, info = process(resized)

                send(info)

                if args["show"]:
                    cv2.imshow("output", out)
                    cv2.waitKey(1)
                if args["write"]:
                    output_writer.write(out)

        except Exception as e:
            raise e
        finally:
            cap.release()


    elif args["keypoints"]:

        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.setblocking(False)

        server_address = (UDP_ADDR_RX, UDP_PORT_RX)
        s.bind(server_address)

        try:
            while True:
        
                payload = None

                # discard all packages but the newest one
                while True:
                    try:
                        payload, address = s.recvfrom(4096)
                    except socket.error as e:
                        break

                if payload is not None:

                    data = json.loads(payload.decode("utf-8"))

                    out, info = process(None, preprocessed_keypoints=data["data"])

                    send(info)    

                    if args["show"]:
                        cv2.imshow("output", out)
                        cv2.waitKey(1)
                    if args["write"]:
                        output_writer.write(out)

        except Exception as e:
            raise e
        finally:
            s.close()


    elif filename.endswith(".mp4"):

        full_input_filename = os.path.join(args["input_dir"], args["input_file"])
        cap = cv2.VideoCapture(full_input_filename)
        
        video_file_original_creation_date = None
        video_file_fps = 30

        if args["output_data"]:
            import ffmpeg
            from fractions import Fraction
      
            metadata = ffmpeg.probe(full_input_filename)
            video_file_original_creation_date = metadata["format"]["tags"]["creation_time"] # caveat: creation date is when last frame is written
            video_file_fps = float(Fraction(metadata["streams"][0]["r_frame_rate"]))

            video_file_frames = float(metadata["streams"][0]["nb_frames"])

            # datetime expects ISO 8601 without the trailing 'Z'
            video_file_original_creation_date = datetime.datetime.fromisoformat(video_file_original_creation_date[:-1] + "+00:00") - datetime.timedelta(seconds=video_file_frames * (1/video_file_fps))


        if args["frame"] is not None:

            while(cap.isOpened()):
                _, image_cap = cap.read()

                if image_cap is None:
                    log.debug("frame {} empty".format(frame_counter))
                    break

                if not frame_counter == int(args["frame"]):
                    frame_counter += 1
                else:
           
                    out, info = process(image_cap)
                    send(info)

                    if args["write"]:
                        cv2.imwrite("output.png", out)
                        log.info("written to file: {}".format("output.png"))
                    
                    break
        else:

            found_patterns = []

            while(cap.isOpened()):
                _, image_cap = cap.read()

                if image_cap is None:
                    log.debug("frame {} empty".format(frame_counter))
                    break

                log.debug("frame: {}".format(frame_counter))

                out, info = process(image_cap)
                send(info)

                # print("found patterns: {}".format(len(info["found_patterns"])))

                if args["show"]:
                    cv2.imshow("output", out)
                    cv2.waitKey(1)

                if args["write"]:
                    output_writer.write(out)

                if args["output_data"] is not None:
                    with open(args["output_data"], "a") as f:
                        processing_data = {}
                        # processing_data["timestamp"] = datetime.datetime.now(datetime.timezone.utc).isoformat() # time when the frame is processed
                        processing_data["timestamp"] = (video_file_original_creation_date + datetime.timedelta(seconds=frame_counter * 1/video_file_fps)).isoformat() # time when the frame was captured
                        processing_data["found_patterns"] = info["found_patterns"]
                        json.dump(processing_data, f)
                        f.write("\n")

                if args["stats"]:
                    found_patterns.append(len(info["found_patterns"]))

                frame_counter += 1

            if args["stats"]:
                p = np.asarray(found_patterns)
                p_nonzero = p[p > 0]
                log.info("found patterns per frame: {:5.2f} | only non-zero frames: {:5.2f}".format(np.mean(p), np.mean(p_nonzero)))
                log.info("frames without patterns:  {} / {}  |  {:5.2f}%".format(frame_counter - np.count_nonzero(p), frame_counter, (frame_counter - np.count_nonzero(p))/frame_counter*100))

        cap.release()
        

    elif filename.endswith(".jpg"):

        full_input_filename = os.path.join(args["input_dir"], args["input_file"])
        img = cv2.imread(full_input_filename)

        if args["rotate90"]:
            img = cv2.rotate(img, cv2.ROTATE_90_CLOCKWISE)

        resized = cv2.resize(img, [960, 540], interpolation=cv2.INTER_AREA)

        out, info = process(resized)
        
        if args["show"]:
            cv2.imshow("output", out)
            cv2.waitKey(1)

        if args["write"]:
            filename = os.path.join(args["output_dir"], args["input_file"])
            cv2.imwrite(filename, out)
            log.info("written to file: {}".format(filename))

        if args["output_data"] is not None:
            with open(args["output_data"], "a") as f:
                processing_data = {}
                processing_data["found_patterns"] = info["found_patterns"]
                # processing_data["missing_patterns"] = info["missing_patterns"]
                json.dump(processing_data, f)
                f.write("\n")

    else:
        log.error("unknown file format: {}".format(args["input_file"]))
        sys.exit(-1)


    if output_writer is not None:
        output_writer.release()

    diff = (datetime.datetime.now() - timer_start).total_seconds()
    log.info("frames: {} | total_time: {:5.2f}s | FPS: {:5.2f}".format(frame_counter, diff, frame_counter/diff))
  
    if args["ground_truth"]:
        if len(error) == 0:
            log.error("could not compare to ground truth, error values missing.")
        else:
            with open(ERROR_FILE, "w") as f:
                json.dump(error, f, indent=4)
