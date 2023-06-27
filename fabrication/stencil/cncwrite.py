import math
import json
import argparse

import cv2
import numpy as np
from shapely.geometry import Point
from PIL import Image, ImageDraw, ImageFont


SIZE                        = 60, 60
INNER_CIRCLE_DIAM           = 28

HOLE_SPACING                = 0
HOLE_SIZE                   = 0.800     # only used for debug output

SPHERICAL_DOME_MODE         = True
SPHERE_RADIUS               = 60/2
SPHERE_DIST                 = 25.055 # measured from work position zero

SPIRAL_SORT                 = False

DEBUG_IMAGE                 = "debug.png"
DEBUG_SCALE                 = 20
IMAGE_SIZE                  = (SIZE[0] * DEBUG_SCALE, SIZE[1] * DEBUG_SCALE) # mm

SVG_SCALE                   = 3.78
SVG_OFFSET                  = [-SIZE[0]/2*SVG_SCALE, -SIZE[1]/2*SVG_SCALE]

GCODE_FILE                  = "output.gcode"
SVG_FILE                    = "output.svg"

TRAVEL_SPEED                = 600
RAISE_SPEED                 = 400
DRILL_SPEED                 = 80

DRILL_START                 = -2
DRILL_DEPTH                 = -3 -6 -1

SAFE_HEIGHT                 = 6        # at the start
SAFE_HEIGHT_LOW             = 1        # used within the area

# ---

# TORUS

TORUS_FILE                  = "debruijn_torus_16_32_3_3.npy"
HOLE_SPACING                = 1.60 
# TORUS_FILTER_INVERT         = False # RED
TORUS_FILTER_INVERT         = True # GREEN

# HEXMAP

HEXMAP_FILE                 = "2678_data_3_i-1725881.json"
# HEXMAP_FILE                 = "2633_data_0_i-1303443.json"
HOLE_SPACING                = 2.00 
# HEXMAP_FILTER_VALUE         = 0
HEXMAP_FILTER_VALUE         = 1

# ---

MODE_HEXMAP                 = "hexmap"
MODE_TORUS                  = "torus"
MODE_GRID                   = "grid"

# ---

START_CMD       = """
G90                     (abs coords)
G21                     (units: mm)
G1 F{travel_speed}      
G1 Z{z:.4f}             (move to safe height)
G1 X0 Y0 Z{z:.4f}       (move to zero)
G92 X0 Y0 Z{z:.4f} A0   (reset extruder axis)
"""

# MOVE_CMD        = """
# M03 S{power}
# G4 P0
# G1 F{move_speed}
# G1  X{x} Y{y}
# """

MOVE_CMD        = """
G1 F{travel_speed}
G1 X{x:.4f} Y{y:.4f} Z{z:.4f}
"""

END_CMD         = """
G4 P0 
G1 F{travel_speed}
G1 Z{z:.4f}
G1 X0 Y0 Z{z:.4f}
"""

def cut_poly(f, poly):

    coords = poly.exterior.coords

    # move to start of polygon
    f.write(MOVE_CMD.format(
        x=coords[0][0], y=coords[0][1], 
        travel_speed=TRAVEL_SPEED))

    f.write(CUT_CMD.format(
        x=coords[0][0], y=coords[0][1], 
        power=LASER_CUT,
        cut_speed=CUT_SPEED))

    # cut
    for i in range(1, len(coords)):
        p = coords[i]
        f.write(CUT_CMD.format(
            x=p[0], y=p[1], 
            power=LASER_CUT,
            cut_speed=CUT_SPEED))

    # close last segment
    f.write(CUT_CMD.format(
        x=coords[0][0], y=coords[0][1], 
        power=LASER_CUT,
        cut_speed=CUT_SPEED))


def calculate_dome_offset(x, y, distance, radius, center=(SIZE[0]/2, SIZE[1]/2)):
    xy_dist = math.sqrt((center[0]-x)**2 + (center[0]-y)**2)
    return math.sqrt(radius**2 - xy_dist**2) - distance


def pointy_hex_to_pixel(q, r, s, center=[0, 0], hex_size=HOLE_SPACING/2):
    x = hex_size * (math.sqrt(3) * q + math.sqrt(3)/2 * r)
    y = hex_size * (3./2 * r)
    return (x + center[0], y + center[1])


# ------------------------------------------------------------------------------------------

font             = ImageFont.load_default()
font_large       = ImageFont.truetype("FiraMono-Regular.ttf", 16)
font_large_bold  = ImageFont.truetype("FiraMono-Bold.ttf", 16)

circle = Point(SIZE[0]/2, SIZE[1]/2).buffer(INNER_CIRCLE_DIAM/2)
points = []



ap = argparse.ArgumentParser()

ap.add_argument(
    "mode",
    default=MODE_HEXMAP,
    choices=[MODE_HEXMAP, MODE_TORUS, MODE_GRID], 
    help=""
)

args = vars(ap.parse_args())

if SPHERICAL_DOME_MODE:
    print("SPHERICAL DOME MODE")

if args["mode"] == MODE_HEXMAP:

    data = None
    with open(HEXMAP_FILE, "r") as f:
        data = json.load(f)

    for key in data["data"]:

        if not data["data"][key] == HEXMAP_FILTER_VALUE:
            continue

        q, r, s = [int(c) for c in key.split("|")]

        x, y = pointy_hex_to_pixel(q, r, s, center=[SIZE[0]/2, SIZE[1]/2])

        # mirror Y axis so it can be observed through the lens on the back
        y = SIZE[1] - y

        p = Point(x, y)

        if not circle.intersection(p):
            continue    

        points.append(p)

    print("generated {}/{} hexmap points".format(len(points), len(data["data"].keys())))

elif args["mode"] == MODE_TORUS:
    print("TORUS MODE")

    torus = np.load(TORUS_FILE)

    # mirror torus vertically so it can be observed through the lens on the back
    torus = np.flip(torus, axis=1)

    offset = [torus.shape[1]*HOLE_SPACING/2-HOLE_SPACING/2, torus.shape[0]*HOLE_SPACING/2-HOLE_SPACING/2]

    for i in range(torus.shape[0]):
        line = []
        for j in range(torus.shape[1]):

            if TORUS_FILTER_INVERT:
                if not torus[i, j]:
                    continue
            else:
                if torus[i, j]:
                    continue

            p = Point(SIZE[0]/2 + j*HOLE_SPACING - offset[0], SIZE[1]/2 + i*HOLE_SPACING - offset[1])

            if not circle.intersection(p):
                continue    

            line.append(p)  

        if i % 2 == 0:
            points += line
        else:
            points += reversed(line)

    print("generated {}/{} torus points".format(len(points), torus.shape[0]*torus.shape[1]))

elif args["mode"] == MODE_GRID:

    # regular grid

    # for x in np.linspace(0, SIZE[0], math.floor(SIZE[0]/HOLE_SPACING)):
    #     for y in np.linspace(0, SIZE[1], math.floor(SIZE[1]/HOLE_SPACING)):
    #         p = Point(x, y)
    #         if circle.intersection(p):
    #             points.append(Point(x, y))

    # hex grid

    print("GRID HEXAGON MODE")

    size = HOLE_SPACING
    w = math.sqrt(3) * size
    h = 2 * size
    num_x = int(SIZE[0]/w)
    num_y = int(SIZE[1]/(0.75*h))
    offset = [0, 0]
    if num_y % 2 == 0:
        offset = [SIZE[0]-num_x*w, SIZE[1]-num_y*(0.75*h)]
    else:
        offset = [SIZE[0]-num_x*w, SIZE[1]-num_y*(0.75*h)+0.75*h]

    print("hexagons - horizontal: {} | vertical: {}".format(num_x, num_y))
    print("hex offsets: {:6.3f} {:6.3f}".format(*offset))

    for y in range(0, num_y):
        line = []
        for x in range(0, num_x):

            p = None
            if y % 2 == 0:
                p = Point(offset[0]/2 + x*w,              offset[1]/2 + 0.75*h*y) # + 0.5*h)
            else:
                p = Point(offset[0]/2 + 0.5*w + x*w,      offset[1]/2 + 0.75*h*y) # + 0.5*h)

            if not circle.intersection(p):
                continue    

            line.append(p)  

            # if x == 0:
            #     print("{} {}".format(y, p))      


        if y % 2 == 0:
            points += line
        else:
            points += reversed(line)

else:
    print("mode missing")
    sys.exit(-1)


if SPIRAL_SORT:
    # spiral traversal order, naive implementation
    points_sorted = []
    center = [SIZE[0]/2, SIZE[1]/2]
    points = sorted(points, key=lambda p: math.sqrt(math.pow(center[0] - p.x, 2) + math.pow(center[1] - p.y, 2)), reverse=False)
    points_sorted.append(points[0])
    points = points[1:]

    # weighting
    while len(points) > 0:
        points = sorted(
            points, 
            key=lambda p: 
                0.45 * math.sqrt(math.pow(center[0] - p.x, 2) + math.pow(center[1] - p.y, 2)) +                      # distance to center
                0.55 * math.sqrt(math.pow(points_sorted[-1].x - p.x, 2) + math.pow(points_sorted[-1].y - p.y, 2)),   # distance to last point
            reverse=False
        )
        points_sorted.append(points[0])
        points = points[1:]

    points = list(reversed(points_sorted))

# ---

print("num points: {}".format(len(points)))

with Image.new(mode="RGB", size=IMAGE_SIZE) as im:
    draw = ImageDraw.Draw(im, "RGBA")

    for x in range(1, IMAGE_SIZE[0]//100):
        draw.line([x*100, 0, x*100, IMAGE_SIZE[1]], width=1, fill=(40, 40, 40))

    for y in range(1, IMAGE_SIZE[1]//100):
        draw.line([0, y*100, IMAGE_SIZE[0], y*100], width=1, fill=(40, 40, 40))

    draw.text((25, 5+20),           "HOLE SPACING:", (255, 255, 255), font=font_large)
    draw.text((25+170, 5+20),       " {:2.3f} mm".format(HOLE_SPACING), (255, 255, 255), font=font_large_bold)

    draw.text((25, 5+20*2),         "HOLE SIZE:", (255, 255, 255), font=font_large)
    draw.text((25+170, 5+20*2),     " {:2.3f} mm".format(HOLE_SIZE), (255, 255, 255), font=font_large_bold)

    draw.text((25, 5+20*3),         "INNER CIRCLE:", (255, 255, 255), font=font_large)
    draw.text((25+170, 5+20*3),     " {:2.2f} mm".format(INNER_CIRCLE_DIAM), (255, 255, 255), font=font_large_bold)

    draw.line([25, 10+20*4, 270, 10+20*4], width=1, fill=(80, 80, 80))

    draw.text((25, 20+20*4),         "total points:", (255, 255, 255), font=font_large)
    draw.text((25+170, 20+20*4),     " {}".format(len(points)), (255, 255, 255), font=font_large_bold)

    val = " - "
    if args["mode"] == MODE_HEXMAP:
        val = str(HEXMAP_FILTER_VALUE)
    elif args["mode"] == MODE_TORUS:
        val = str(TORUS_FILTER_INVERT)
    draw.text((25, IMAGE_SIZE[1]-30),       "FILTER VALUE:", (255, 255, 255), font=font_large)
    draw.text((25+170, IMAGE_SIZE[1]-30),   val, (255, 255, 255), font=font_large_bold)

    draw.line([0, IMAGE_SIZE[1]/2, IMAGE_SIZE[0], IMAGE_SIZE[1]/2], width=1, fill=(40, 0, 0))
    draw.line([IMAGE_SIZE[0]/2, 0, IMAGE_SIZE[0]/2, IMAGE_SIZE[1]], width=1, fill=(40, 0, 0))

    for i in range(0, len(points)-1):
        cur = points[i]
        nxt = points[i+1]

        draw.line([
            int(cur.x * DEBUG_SCALE), int(cur.y * DEBUG_SCALE), 
            int(nxt.x * DEBUG_SCALE), int(nxt.y * DEBUG_SCALE)], 
            width=4, fill=(0, 0, 150))

    for point in points:
        coords = [(int(x * DEBUG_SCALE), int(y * DEBUG_SCALE)) for x, y in point.buffer(HOLE_SIZE/2).exterior.coords]
        draw.polygon(coords, fill="white")

    coords = [(int(x * DEBUG_SCALE), int(y * DEBUG_SCALE)) for x, y in circle.exterior.coords]
    draw.polygon(coords, outline="red")

    im.save(DEBUG_IMAGE)


with open(GCODE_FILE, "w") as f:
    f.write(START_CMD.format(
        travel_speed=TRAVEL_SPEED,
        z=SAFE_HEIGHT
    ))

    # move to initial position
    f.write(MOVE_CMD.format(
            x=0, y=0, z=SAFE_HEIGHT, 
            travel_speed=TRAVEL_SPEED))

    # move to first point
    coords = list(points[0].coords)[0]
    f.write(MOVE_CMD.format(
            x=coords[0], y=coords[1], z=SAFE_HEIGHT, 
            travel_speed=TRAVEL_SPEED))

    spherical_offset = 0

    for i in range(0, len(points)):

        p = list(points[i].coords)[0]

        if SPHERICAL_DOME_MODE:
            spherical_offset = calculate_dome_offset(p[0], p[1], SPHERE_DIST, SPHERE_RADIUS)

        p = [p[0], p[1]*-1+SIZE[1]] # flip Y coordinate to convert top-left coordinate system (numpy matrix, PIL image) to bottom-left system (gcode)

        # move
        f.write(MOVE_CMD.format(
            x=p[0], y=p[1], z=SAFE_HEIGHT_LOW, 
            travel_speed=TRAVEL_SPEED))

        # lower
        f.write(MOVE_CMD.format(
            x=p[0], y=p[1], z=DRILL_START, 
            travel_speed=TRAVEL_SPEED))

        # drill
        f.write(MOVE_CMD.format(
            x=p[0], y=p[1], z=DRILL_DEPTH + spherical_offset, 
            travel_speed=DRILL_SPEED))

        # print(DRILL_DEPTH + spherical_offset)

        # raise
        f.write(MOVE_CMD.format(
            x=p[0], y=p[1], z=SAFE_HEIGHT_LOW, 
            travel_speed=RAISE_SPEED))

    f.write(
        END_CMD.format(
            travel_speed=TRAVEL_SPEED,
            z=SAFE_HEIGHT
    ))

    print("written to file: {}".format(GCODE_FILE))

with open(SVG_FILE, "w") as f:

    f.write("<?xml version=\"1.0\" encoding=\"utf-8\" ?>\n")
    f.write("<?xml-stylesheet href=\"style.css\" type=\"text/css\" title=\"main_stylesheet\" alternate=\"no\" media=\"screen\" ?>\n")
    f.write("<svg baseProfile=\"tiny\" version=\"1.2\" width=\"{}{}\" height=\"{}{}\"\n".format(SIZE[0]*SVG_SCALE, "mm", SIZE[1]*SVG_SCALE, "mm"))
    f.write("xmlns=\"http://www.w3.org/2000/svg\" xmlns:ev=\"http://www.w3.org/2001/xml-events\" xmlns:xlink=\"http://www.w3.org/1999/xlink\">\n")
    f.write("<defs />\n")

    f.write("<circle cx=\"{}\" cy=\"{}\" r=\"{}\" fill=\"none\" stroke=\"black\" />\n".format(
        SIZE[0]/2*SVG_SCALE+SVG_OFFSET[0], 
        SIZE[1]/2*SVG_SCALE+SVG_OFFSET[1], 
        INNER_CIRCLE_DIAM/2*SVG_SCALE))

    for i in range(0, len(points)):
        p = list(points[i].coords)[0]

        f.write("<circle cx=\"{}\" cy=\"{}\" r=\"{}\" />\n".format(
            p[0]*SVG_SCALE+SVG_OFFSET[0], 
            p[1]*SVG_SCALE+SVG_OFFSET[1], 
            HOLE_SIZE/2*SVG_SCALE))

    f.write("</svg>\n")

    print("written to file: {}".format(SVG_FILE))    
                