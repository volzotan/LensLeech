from shapely.geometry import Point
from PIL import Image, ImageDraw, ImageFont

import cv2
import numpy as np
import math

SIZE                        = 50, 50
INNER_CIRCLE_DIAM           = 28

TORUS_MODE                  = False
HOLE_SPACING                = 1.5       #2.7 #12
HOLE_SIZE                   = 0.300     # only used for gerber stencil

TORUS_MODE                  = True
TORUS_FILE                  = "debruijn_torus_16_32_3_3.npy"
HOLE_SPACING                = 2.0 
TORUS_FILTER_INVERT         = False # RED
TORUS_FILTER_INVERT         = True # GREEN

SPHERICAL_DOME_MODE         = True
SPHERE_RADIUS               = 60/2
SPHERE_DIST                 = 25.055 # measured from work position zero

SPIRAL_SORT                 = False

DEBUG_IMAGE                 = "debug.png"
DEBUG_SCALE                 = 20
IMAGE_SIZE                  = (SIZE[0] * DEBUG_SCALE, SIZE[1] * DEBUG_SCALE) # mm

GCODE_FILE                  = "output.gcode"
GERBER_FILE                 = "output.gbr"

TRAVEL_SPEED                = 1000
RAISE_SPEED                 = TRAVEL_SPEED * 1.5

WAIT_TIME_AFTER_EXTRUDE     = 0.1

SAFE_HEIGHT                 = 15        # at the start
SAFE_HEIGHT_LOW             = 12        # used within the area

EXTRUDE_Z_OFFSET            = 0.0       # extrusion point relative to Z0
EXTRUDE_SPEED               = 200

# default material
EXTRUDE_DIST                =  1.000    # 1 unit distance = 0.001ml (1 microliter)
RETRACTION_DIST             = -0.500    # negative

# ---

# water-based ink
# EXTRUDE_DIST                =  0.025   
# RETRACTION_DIST             = -0.015    

# oil-based ink
# EXTRUDE_DIST                =  0.035   
# RETRACTION_DIST             = -0.015   

# silicone-based ink (no solvent, 30g needle)
EXTRUDE_DIST                =  0.150    # 1 unit distance = 0.001ml (1 microliter)
RETRACTION_DIST             = -0.050    # should be negative

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

WAIT_CMD        = """
G4 P{wait_time:.4f} 
"""

EXTRUDE_CMD     = """
G1 F{extrude_speed}
G1 A{e:.4f}
"""

TRAVEL_CMD      = """
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
    f.write(TRAVEL_CMD.format(
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

# ------------------------------------------------------------------------------------------

font             = ImageFont.load_default()
font_large       = ImageFont.truetype("FiraMono-Regular.ttf", 16)
font_large_bold  = ImageFont.truetype("FiraMono-Bold.ttf", 16)

fastener = [
    [SIZE[0]/2-30.5 , SIZE[1]/2],       # left
    [SIZE[0]/2      , SIZE[1]/2+30.5],  # top
    [SIZE[0]/2+30.5 , SIZE[1]/2],       # right
    [SIZE[0]/2      , SIZE[1]/2-30.5]   # bottom
]

circle = Point(SIZE[0]/2, SIZE[1]/2).buffer(INNER_CIRCLE_DIAM/2)
points = []

if SPHERICAL_DOME_MODE:
    print("SPHERICAL DOME MODE")

if TORUS_MODE:
    print("TORUS MODE")

    torus = np.load(TORUS_FILE)

    # mirror torus vertically so it can be observed thorugh the lens on the back
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

else:

    # regular grid

    # for x in np.linspace(0, SIZE[0], math.floor(SIZE[0]/HOLE_SPACING)):
    #     for y in np.linspace(0, SIZE[1], math.floor(SIZE[1]/HOLE_SPACING)):
    #         p = Point(x, y)
    #         if circle.intersection(p):
    #             points.append(Point(x, y))

    # hex grid

    print("HEXAGON MODE")

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

    draw.text((25, 5+20*4),         "EXTRUDE:", (255, 255, 255), font=font_large)
    draw.text((25+170, 5+20*4),     " {:2.3f} µl".format(EXTRUDE_DIST), (255, 255, 255), font=font_large_bold)

    draw.text((25, 5+20*5),         "RETRACT:", (255, 255, 255), font=font_large)
    draw.text((25+170, 5+20*5),     "{:2.3f} µl".format(RETRACTION_DIST), (255, 255, 255), font=font_large_bold)

    draw.line([25, 10+20*6, 270, 10+20*6], width=1, fill=(80, 80, 80))

    draw.text((25, 20+20*6),         "total points:", (255, 255, 255), font=font_large)
    draw.text((25+170, 20+20*6),     " {}".format(len(points)), (255, 255, 255), font=font_large_bold)

    for f in fastener:
        coords = [(int(x * DEBUG_SCALE), int(y * DEBUG_SCALE)) for x, y in Point(f).buffer(2.5).exterior.coords]
        draw.polygon(coords, fill=(40, 40, 40))

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

with open(GERBER_FILE, "w") as f:

    f.write(
"""G04 EAGLE Gerber RS-274X export*
G75*
%MOMM*%
%FSLAX34Y34*%
%LPD*%
%INSolderpaste Top*%
%IPPOS*%
%AMOC8*
5,1,8,0,0,1.08239X$1,22.5*%
G01*
""")

    f.write("%ADD10C,{:1.4f}*%\n".format(HOLE_SIZE))
    f.write("%ADD11C,2.6000*%\n")
    f.write("\n\n")

    f.write("D10*")
    f.write("\n")

    for point in points:
        # x_decimalplaces, _ = math.modf(point.x)
        # y_decimalplaces, _ = math.modf(point.y)

        # x_2 = "{:.4f}".format(x_decimalplaces)[2:]
        # y_2 = "{:.4f}".format(y_decimalplaces)[2:]

        # print("{} {}".format(point.y, y_2))

        x, decimal_x = "{:.4f}".format(point.x).split(".")
        y, decimal_y = "{:.4f}".format(point.y).split(".")

        f.write("X{}{}Y{}{}D03*\n".format(x, decimal_x, y, decimal_y))
    
    f.write("\n")
    f.write("D11*")
    f.write("\n")

    for point in fastener:

        x, decimal_x = "{:.4f}".format(point[0]).split(".")
        y, decimal_y = "{:.4f}".format(point[1]).split(".")

        f.write("X{}{}Y{}{}D03*\n".format(x, decimal_x, y, decimal_y))
    f.write("\n")        

    f.write("M02*")
    f.write("\n")

with open(GCODE_FILE, "w") as f:
    f.write(START_CMD.format(
        travel_speed=TRAVEL_SPEED,
        z=SAFE_HEIGHT
    ))

    # move to initial position
    f.write(TRAVEL_CMD.format(
            x=0, y=0, z=SAFE_HEIGHT, 
            travel_speed=TRAVEL_SPEED))

    # purge cycle (extrude n times)
    # for i in range(0, 10):

    #     f.write(TRAVEL_CMD.format(
    #         x=0, y=0, z=SAFE_HEIGHT+1, 
    #         travel_speed=TRAVEL_SPEED))


    #     f.write(TRAVEL_CMD.format(
    #         x=0, y=0, z=SAFE_HEIGHT, 
    #         travel_speed=TRAVEL_SPEED))

    #     # extrude
    #     f.write(EXTRUDE_CMD.format(
    #         e=EXTRUDE_DIST * (i + 1), 
    #         extrude_speed=EXTRUDE_SPEED))

    #     # wait
    #     f.write(WAIT_CMD.format( 
    #         wait_time=0.1))

    # purge cycle (place dots on paper)
    for j in range(0, 4):
        for i in range(0, 10):

            p = [5+HOLE_SPACING*i*1.2, -3-HOLE_SPACING*j*1.2]

            # move
            f.write(TRAVEL_CMD.format(
                x=p[0], y=p[1], z=SAFE_HEIGHT_LOW/2, 
                travel_speed=TRAVEL_SPEED))

            # lower
            f.write(TRAVEL_CMD.format(
                x=p[0], y=p[1], z=EXTRUDE_Z_OFFSET+0.4, 
                travel_speed=TRAVEL_SPEED))

            # extrude
            f.write(EXTRUDE_CMD.format(
                e=EXTRUDE_DIST * (i + 1), 
                extrude_speed=EXTRUDE_SPEED))

            # wait
            f.write(WAIT_CMD.format( 
                wait_time=WAIT_TIME_AFTER_EXTRUDE))

            # raise
            f.write(TRAVEL_CMD.format(
                x=p[0], y=p[1], z=SAFE_HEIGHT_LOW/2, 
                travel_speed=RAISE_SPEED))

    # raise and wait for manual syringe cleaning
    f.write(TRAVEL_CMD.format(
        x=0, y=0, z=SAFE_HEIGHT*3, 
        travel_speed=RAISE_SPEED))
    
    f.write(WAIT_CMD.format( 
        wait_time=3.0))

    # then START_CMD to move to (0, 0, SAFE_HEIGHT) and for e axis reset
    f.write(START_CMD.format(
        travel_speed=TRAVEL_SPEED,
        z=SAFE_HEIGHT
    ))

    # move to first point
    coords = list(points[0].coords)[0]
    f.write(TRAVEL_CMD.format(
            x=coords[0], y=coords[1], z=SAFE_HEIGHT, 
            travel_speed=TRAVEL_SPEED))

    extrude_pos = 0
    spherical_offset = 0

    for i in range(0, len(points)):

        p = list(points[i].coords)[0]

        if SPHERICAL_DOME_MODE:
            spherical_offset = calculate_dome_offset(p[0], p[1], SPHERE_DIST, SPHERE_RADIUS)

        p = [p[0], p[1]*-1+SIZE[1]] # flip Y coordinate to convert top-left coordinate system (numpy matrix, PIL image) to bottom-left system (gcode)

        # move
        f.write(TRAVEL_CMD.format(
            x=p[0], y=p[1], z=SAFE_HEIGHT_LOW + spherical_offset, 
            travel_speed=TRAVEL_SPEED))

        # lower
        f.write(TRAVEL_CMD.format(
            x=p[0], y=p[1], z=EXTRUDE_Z_OFFSET + spherical_offset, 
            travel_speed=TRAVEL_SPEED))

        extrude_pos += EXTRUDE_DIST

        # print("{:2.4f} | steps: {}".format(extrude_pos, int(710*extrude_pos)))

        # extrude_pos += EXTRUDE_DIST - EXTRUDE_DIST_REDUCER * i
        # print("{:03} | reducing extrusion distance: orig {:.4} / new {:.4}".format(i, EXTRUDE_DIST, EXTRUDE_DIST-EXTRUDE_DIST_REDUCER * i))

        # extrude
        f.write(EXTRUDE_CMD.format(
            e=extrude_pos, 
            extrude_speed=EXTRUDE_SPEED))

        # wait
        f.write(WAIT_CMD.format( 
            wait_time=WAIT_TIME_AFTER_EXTRUDE))

        # raise
        f.write(TRAVEL_CMD.format(
            x=p[0], y=p[1], z=SAFE_HEIGHT_LOW + spherical_offset, 
            travel_speed=RAISE_SPEED))

        # retract
        if abs(RETRACTION_DIST) > 0:
            f.write(EXTRUDE_CMD.format(
                e=extrude_pos + RETRACTION_DIST, 
                extrude_speed=EXTRUDE_SPEED)) 


    f.write(
        END_CMD.format(
            travel_speed=TRAVEL_SPEED,
            z=SAFE_HEIGHT
    ))

    print("written to file. extruded distance: {:.4f}".format(extrude_pos))
                