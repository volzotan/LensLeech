from shapely.geometry import Point, LineString, Polygon
from shapely import affinity
from PIL import Image, ImageDraw, ImageFont
import numpy as np
import scipy.interpolate

import math
import sys
import os

SIZE                        = 40, 40
# DEBUG_IMAGE                 = "debug.png"
DEBUG_IMAGE                 = "{:05}.png"
DEBUG_IMAGE_DIR             = "images"
DEBUG_SCALE                 = 20 
IMAGE_SIZE                  = (SIZE[0] * DEBUG_SCALE, SIZE[1] * DEBUG_SCALE) # mm
LINE_SEGMENTS               = 100

GCODE_FILE                  = "output.gcode"

MOVE_SPEED                  = 280
# MOVE_RADIUS                 = [5, 0]   # movement extent in both axes
MOVE_ROT                    = 360*20   # degrees of rotation for a full cycle
GCODE_UNIT_ROT_SCALER       = 1/90     # X deg = 1 gcode unit on the rotation axis

NUM_CYCLES                  = 100

DOUBLE_EIGHT_DIST           = 12
DOUBLE_EIGHT_DIAM           = 4
DOUBLE_EIGHT_ROT            = 360/25 # deg

# ---

START_CMD           = """
G90 G94                 (abs coords)
G17                     (XY plane)
G21                     (units: mm) 
G92 X0 Y0 Z0 A0         (reset all axes)
G1 F{move_speed}     
"""

RESET_COORDS_CMD    = """
G92 X0 Y0 Z0 A0         
"""

MOVE_CMD            = """
G1 F{move_speed}
G1 X{x:.4f} Y{y:.4f} Z{z:.4f} A{a:.4f}
"""

END_CMD             = """
G1 F{move_speed}
G1 X0 Y0 Z0
G92 X0 Y0 Z0 A0         (reset all axes)
"""

# font             = ImageFont.load_default()
# font_large       = ImageFont.truetype("FiraMono-Regular.ttf", 16)
# font_large_bold  = ImageFont.truetype("FiraMono-Bold.ttf", 16)

# ---

def lerp(a: float, b: float, x: float):
    return a + (b - a) * x

def rotate(xy, center, deg):

    x = xy[0] - center[0]
    y = xy[1] - center[1]
    s = math.sin(math.radians(deg))
    c = math.cos(math.radians(deg))
    xnew = (x * c - y * s) + center[0] 
    ynew = (x * s + y * c) + center[1]    

    return (xnew, ynew)

def draw_polar(draw, pos, coords, color=[1, 1, 1]):

    global moves

    # rotate position from last move to the actual 
    # xy coordinates for this move
    xy = rotate([pos[0], pos[1]], [0, 0], pos[2])
    old = [xy[0], xy[1], pos[2]]

    # print("init pos: {}".format(pos))
    # print("init old: {}".format(old))
    # print("lerp: {} to {}".format(pos, coords))

    d = math.dist(pos[0:2], coords[0:2])
    num_segments = int(d*100)

    for i in range(1, num_segments):

        progress = float(i)/num_segments

        x = lerp(pos[0], coords[0], progress)
        y = lerp(pos[1], coords[1], progress)
        a = lerp(pos[2], coords[2]/GCODE_UNIT_ROT_SCALER, progress)

        xnew, ynew = rotate([x, y], [0, 0], a)

        # draw.line(
        #     [
        #         old[0]*DEBUG_SCALE+IMAGE_SIZE[0]/2, 
        #         old[1]*DEBUG_SCALE+IMAGE_SIZE[1]/2, 
        #         xnew*DEBUG_SCALE+IMAGE_SIZE[0]/2, 
        #         ynew*DEBUG_SCALE+IMAGE_SIZE[1]/2
        #     ], 
        #     width=10, 
        #     fill=(
        #         int(color[0]*(50+200*progress)),
        #         int(color[1]*(50+200*progress)), 
        #         int(color[2]*(50+200*progress)))
        # )

        draw.ellipse((
            xnew*DEBUG_SCALE+IMAGE_SIZE[0]/2-2, 
            ynew*DEBUG_SCALE+IMAGE_SIZE[1]/2-2, 
            xnew*DEBUG_SCALE+IMAGE_SIZE[0]/2+2, 
            ynew*DEBUG_SCALE+IMAGE_SIZE[1]/2+2
        ), 
            fill=(
                int(color[0]*(50+200*progress)),
                int(color[1]*(50+200*progress)), 
                int(color[2]*(50+200*progress))))

        old = [xnew, ynew]

        moves.append([xnew, ynew])
        if len(moves) > 1000:
            moves = moves[:-1000]
        draw_image()

def draw_image():

    return

    global image_counter

    with Image.new(mode="RGB", size=IMAGE_SIZE) as im:    
        im.paste((100, 100, 100), [0, 0, IMAGE_SIZE[0], IMAGE_SIZE[1]])
        draw = ImageDraw.Draw(im, "RGBA")

        for i in reversed(range(0, len(moves))):

            progress = float(i)/len(moves)
            xnew, ynew = moves[i]

            draw.ellipse((
                xnew*DEBUG_SCALE+IMAGE_SIZE[0]/2-2, 
                ynew*DEBUG_SCALE+IMAGE_SIZE[1]/2-2, 
                xnew*DEBUG_SCALE+IMAGE_SIZE[0]/2+2, 
                ynew*DEBUG_SCALE+IMAGE_SIZE[1]/2+2
            ), fill=(
                int(255*progress),
                int(255*progress), 
                int(255*progress)))

        im.save(os.path.join(DEBUG_IMAGE_DIR, DEBUG_IMAGE.format(image_counter)))
        image_counter += 1

moves = []
image_counter = 0

with Image.new(mode="RGB", size=IMAGE_SIZE) as im:
    im.paste((100, 100, 100), [0, 0, IMAGE_SIZE[0], IMAGE_SIZE[1]])
    draw = ImageDraw.Draw(im, "RGBA")

    draw.ellipse((
        IMAGE_SIZE[0]/2-4, 
        IMAGE_SIZE[1]/2-4, 
        IMAGE_SIZE[0]/2+4, 
        IMAGE_SIZE[1]/2+4
    ), fill='white', outline='white')

    with open(GCODE_FILE, "w") as f:

        f.write("(Lens polishing pattern - double eight / distance: {} / diameter: {} / rotation: {} / number of cycles: {})\n".format(
            DOUBLE_EIGHT_DIST, DOUBLE_EIGHT_DIAM, DOUBLE_EIGHT_ROT, NUM_CYCLES
        ))

        f.write(START_CMD.format(
            move_speed=MOVE_SPEED
        ))

        pos = [0, 0, 0]

        circle = Point([-DOUBLE_EIGHT_DIST/2, 0]).buffer(DOUBLE_EIGHT_DIAM/2)
        sequence = [p for p in circle.exterior.coords if p[0] < -DOUBLE_EIGHT_DIST/2 - 1e-10]
        sequence.insert(0, [0, 0])
        sequence.insert(1, [-DOUBLE_EIGHT_DIST/2+DOUBLE_EIGHT_DIST/20, -DOUBLE_EIGHT_DIAM*0.47])
        sequence.append([-DOUBLE_EIGHT_DIST/2+DOUBLE_EIGHT_DIST/20, +DOUBLE_EIGHT_DIAM*0.47])
        sequence.append([0, 0])

        # mirror along Y axis
        sequence_mirrored = [[p[0]*-1, p[1]] for p in sequence]

        sequence += sequence_mirrored
        sequence = LineString(sequence)
        sequence = sequence.simplify(0.01)

        sequence_length = sequence.length
        r = DOUBLE_EIGHT_ROT

        print("total cycles:            {}".format(NUM_CYCLES))
        print("revolutions per cycle:   {:4.2f}".format(MOVE_ROT/360))
        print("total revolutions:       {} revs".format(int((MOVE_ROT/360)*NUM_CYCLES)))
        print("rotation per cycle:      {:4.2f} deg".format(r))
        print("sum of all rotations:    {} deg".format(int(r*NUM_CYCLES)))
        print("total time:              {:4.2f}min".format(MOVE_ROT*NUM_CYCLES*GCODE_UNIT_ROT_SCALER/MOVE_SPEED))

        for i in range(0, NUM_CYCLES):

            sequence_rotated = affinity.rotate(sequence, r*i, origin=(0, 0))

            for p in range(1, len(sequence_rotated.coords)):

                segment = [sequence_rotated.coords[p-1], sequence_rotated.coords[p]]
                d = math.dist(segment[0], segment[1])/sequence_length

                coords = [
                    sequence_rotated.coords[p][0],
                    sequence_rotated.coords[p][1],
                    pos[2]+MOVE_ROT*d*GCODE_UNIT_ROT_SCALER
                ]

                f.write(MOVE_CMD.format(
                    x=coords[0], y=coords[1], z=0, a=coords[2], 
                    move_speed=MOVE_SPEED)) 

                draw_polar(draw, pos, coords, color=[1, 0, 0])
                pos = coords


        # for i in range(0, NUM_CYCLES):

        #     # left
        #     coords = [
        #         -MOVE_RADIUS[0],
        #         -MOVE_RADIUS[1],
        #         pos[2] + (MOVE_ROT/4) * 1
        #     ]
        #     f.write(MOVE_CMD.format(
        #         x=coords[0], y=coords[1], z=0, a=coords[2]*GCODE_UNIT_ROT_SCALER, 
        #         move_speed=MOVE_SPEED))        

        #     draw_polar(draw, pos, coords, color=[1, 0, 0])
        #     pos = coords

        #     # right
        #     coords = [
        #         +MOVE_RADIUS[0],
        #         +MOVE_RADIUS[1],
        #         pos[2] + (MOVE_ROT/4) * 2
        #     ]
        #     f.write(MOVE_CMD.format(
        #         x=coords[0], y=coords[1], z=0, a=coords[2]*GCODE_UNIT_ROT_SCALER, 
        #         move_speed=MOVE_SPEED))        

        #     draw_polar(draw, pos, coords, color=[0, 1, 0])
        #     pos = coords

        #     # center
        #     coords = [
        #         0,
        #         0,
        #         pos[2] + (MOVE_ROT/4) * 1
        #     ]
        #     f.write(MOVE_CMD.format(
        #         x=coords[0], y=coords[1], z=0, a=coords[2]*GCODE_UNIT_ROT_SCALER, 
        #         move_speed=MOVE_SPEED))    

        #     draw_polar(draw, pos, coords, color=[0, 0, 1])
        #     pos = coords

        #     # TODO: disabled
        #     # reset for next cycle 
        #     # f.write(RESET_COORDS_CMD)        

        f.write(
            END_CMD.format(
                move_speed=MOVE_SPEED
        ))

        print("-- written to file.".format())

    im.save(DEBUG_IMAGE.format(0))
