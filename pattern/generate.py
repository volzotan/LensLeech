import math
import sys
import os
import itertools
import traceback
import copy
import datetime

from collections import deque
from collections import Counter

from random import shuffle, choice
import json

import multiprocessing

"""
Hexagons are handled in the QRS coordinate system. 
Refer to https://www.redblobgames.com/grids/hexagons/ 
for a detailed overview.

All hexagons in "pointy top" orientation.

PIL coordinate system origin is top-left.

All dimensions in mm, except when drawing on PIL's canvas.

We want a DeBruijn-like 2D map of hexagons, ie. each
hexagonal sliding window should show a pattern of 
points (one center, 6 in the ring) that is unique in
the whole map. 
Wording: "pattern" = 7 points, all points = "map".
A perfect map would contain unique patterns that can only
be found once and have no duplicates if rotated. A good map
contains only unique patterns or patterns that need to be
rotated more than one position forward or backward to create 
a duplicate.

General procedure:

 *  make a list of a all possible combinations of colors that 
    can be a pattern (ie. 2 colors = 2**7=128 patterns)

 *  shuffle that list

 *  pick the first pattern from the list and assign to center hex

 *  iteratively test and assign patterns from the list to all 
    neighbouring hexes that match up with the already assigned 
    patterns

 *  if all hexes are filled successful calculate penalty (low 
    penalty for duplicated that require more than one rotation, 
    very high penalty for +1/-1 rot duplicates. Increase penatly
    for duplicates close to the center of the map

 *  shuffle the pattern list and repeat

# Execute with PyPy for a 20-25% speedup.

pypy3 generate.py

"""

DIMENSIONS          = [40, 40] # [60, 60]
IMAGE_SCALE         = 50
OUTPUT_DIR          = os.path.join("unique_color_{}", "output_radius_{}")
OUTPUT_IMAGE        = "{penalties}_output_{prefix}_i-{iteration}.png"
OUTPUT_JSON         = "{penalties}_data_{prefix}_i-{iteration}.json"
OUTPUT_REPORT       = "report.txt"

# hexagon shape: pointy side up
HEX_SIZE            = 1.0
HEX_HORIZONTAL      = math.sqrt(3) * HEX_SIZE
HEX_VERTICAL        = 3/2 * HEX_SIZE

INNER_CIRCLE_DIAM   = 28

NUM_COLORS          = 2
COLORS              = [(0, 0, 255), (0, 255, 0), (255, 0, 0)]

GRID_RADIUS         = 6

NUM_ITERATIONS      = 1e9

WRITE_JSON          = True
WRITE_IMAGE         = True

ABORT_FAST          = False

# UNIQUE_PATTERN      = [1] * 7
UNIQUE_PATTERN      = [0, 0, 0, 0, 1, 1, 1]

if WRITE_IMAGE:
    from PIL import Image, ImageDraw, ImageFont

    font                = ImageFont.load_default()
    font_large          = ImageFont.truetype("FiraMono-Regular.ttf", 32)
    font_large_bold     = ImageFont.truetype("FiraMono-Bold.ttf", 32)

# ----------------------------------------------------------------------


def distance_from_center(q, r, s):
    return max(abs(q), abs(r), abs(s))


def sanity_check(h, lookup):

    known_patterns = []

    unique_patterns = []
    for i in range(0, 6):
        p_rot = UNIQUE_PATTERN[i:] + UNIQUE_PATTERN[:i]
        unique_patterns.append(make_lookup_key(p_rot))

    # for q, r, s in reversed(get_all_hexagons()):

    for key in h.keys():

        q, r, s = [int(x) for x in key.split("|")]

        p = [h["{}|{}|{}".format(q, r, s)]]

        neighbours = get_neighbours(q, r, s)
        for n in neighbours:
            p.append(h["{}|{}|{}".format(*n)])

        # ignore the outermost ring of hexagons
        if len(p) != 7:
            continue

        lookup_key = make_lookup_key(p)

        # print("{} {} {} --- {}".format(q, r, s, lookup_key))

        # check if the unique pattern (or any rotational duplicate of it) is found anywhere except 0|0|0
        if lookup_key in unique_patterns and [q, r, s] != [0, 0, 0]:
            raise Exception("unique pattern (rotation) duplicate! [{},{},{}]".format(q, r, s))

        if lookup_key in known_patterns:
            raise Exception("duplicate! [{},{},{}]".format(q, r, s))
        
        known_patterns.append(lookup_key)


def calculate_penalties(h, lookup):

    try:
        sanity_check(h, lookup)
    except Exception as e:
        print(e)

        info = {
            "penalties": -1,
            "iteration": 1,
            "rot_1": [],
            "rot_n": [],
            "prefix": "error"
        }

        draw_image(h, info)

        sys.exit(-1)

    penalty_points = 0
    rot_1 = []
    rot_n = []

    for key in h.keys():
        q, r, s = [int(x) for x in key.split("|")]

        p = [h["{}|{}|{}".format(q, r, s)]]

        neighbours = get_neighbours(q, r, s)
        for n in neighbours:
            p.append(h["{}|{}|{}".format(*n)])
  
        # ignore the outermost ring of hexagons
        if len(p) != 7:
            continue

        # find the pattern rotated
        for rot in range(1, 6):
            p_rot = [p[0]] + p[-rot:] + p[1:-rot]
            key_for_rotated_values = make_lookup_key(p_rot)

            if key_for_rotated_values == make_lookup_key(p):
                # false positive (pattern has only a single color on the ring)
                continue

            if key_for_rotated_values in lookup:
                pos_of_rotated_hex = lookup[key_for_rotated_values]
                if rot == 1 or rot == 5:
                    penalty_points += 10 * (GRID_RADIUS - distance_from_center(q, r, s))
                    rot_1.append("{}|{}|{}".format(q, r, s))
                    rot_1.append("{}|{}|{}".format(*pos_of_rotated_hex))
                else:
                    penalty_points += 1 * (GRID_RADIUS - distance_from_center(q, r, s))
                    rot_n.append("{}|{}|{}".format(q, r, s))
                    rot_n.append("{}|{}|{}".format(*pos_of_rotated_hex))

    print("penalty: {}".format(penalty_points))

    return penalty_points, rot_1, rot_n


# def calculate_penalties(h, lookup):

#     penalty_points = 0
#     rot_1 = []
#     rot_n = []


#     # sanity check:
#     print("h keys: {} | lookup keys {}".format(len(h.keys()), len(lookup.keys())))

#     for key in h.keys():
#         q, r, s = [int(x) for x in key.split("|")]

#         center = deque([h["{}|{}|{}".format(q, r, s)]])
#         p = deque()

#         neighbours = get_neighbours(q, r, s)
#         for n in neighbours:
#             p.append(h["{}|{}|{}".format(*n)])
  
#         # ignore the outermost ring of hexagons
#         if len(p) != 6:
#             continue

#         key_unrotated = make_lookup_key(center + p)

#         # find the pattern rotated
#         for rot in range(1, 6):
#             p.rotate(1)

#             key_for_rotated_values = make_lookup_key(center + p)

#             if key_for_rotated_values == key_unrotated:
#                 # false positive (pattern has only a single color on the ring)
#                 continue

#             if key_for_rotated_values in lookup:
#                 pos_of_rotated_hex = lookup[key_for_rotated_values]
#                 if rot == 1 or rot == 5:
#                     penalty_points += 10 * (GRID_RADIUS - distance_from_center(q, r, s))
#                     rot_1.append("{}|{}|{}".format(q, r, s))
#                     rot_1.append("{}|{}|{}".format(*pos_of_rotated_hex))
#                 else:
#                     penalty_points += 1 * (GRID_RADIUS - distance_from_center(q, r, s))
#                     rot_n.append("{}|{}|{}".format(q, r, s))
#                     rot_n.append("{}|{}|{}".format(*pos_of_rotated_hex))

#     return penalty_points, rot_1, rot_n


def get_all_hexagons_rec(l, q, r, s):

    l.append([q, r, s])

    for n in get_neighbours(q, r, s):
        if n not in l:
            get_all_hexagons_rec(l, *n)

    return l


def get_all_hexagons():

    l = []

    # ---

    # extend circular from center

    # l.append([0, 0, 0]) # center

    # for radius in range(1, GRID_RADIUS+1):

    #     # bottom (6 o'clock)
    #     for i in range(0, radius):
    #         l.append([-radius+i, radius, -i])

    #     # bottom right (4 o'clock)
    #     for i in range(0, radius):
    #         l.append([i, radius-i, -radius])

    #     # ...
    #     for i in range(0, radius):
    #         l.append([radius, -i, -radius+i])

    #     for i in range(0, radius):
    #         l.append([radius-i, -radius, i])

    #     for i in range(0, radius):
    #         l.append([-i, -radius+i, radius])

    #     for i in range(0, radius):
    #         l.append([-radius, i, radius-i])

    # ---

    # depth first 

    # l = get_all_hexagons_rec([], 0, 0, 0)

    # ---

    # linear sweep

    # for r in range(-GRID_RADIUS+1, +GRID_RADIUS):
    #     for q in range(-GRID_RADIUS+1, +GRID_RADIUS):

    #         if r+q<-GRID_RADIUS+1 or r+q>GRID_RADIUS-1:
    #             continue

    #         s = -q -r 

    #         l.append([q, r, s])

    # ---

    # custom (alternating along the q axis from center first)

    indices = [[x, -x] for x in range(1, +GRID_RADIUS)]
    indices = [0] + list(itertools.chain(*indices))

    for q in indices:
        for r in indices:

            if r+q<-GRID_RADIUS+1 or r+q>GRID_RADIUS-1:
                continue

            s = -q -r 
            l.append([q, r, s])

    return l



def init_h():

    h = {}

    for r in range(-GRID_RADIUS, +GRID_RADIUS+1):
        for q in range(-GRID_RADIUS, +GRID_RADIUS+1):

            if r+q<-GRID_RADIUS or r+q>GRID_RADIUS:
                continue

            s = -q -r 

            h["{}|{}|{}".format(q, r, s)] = None

    return h


def build_pattern_list():
    l = list(itertools.product(list(range(NUM_COLORS)), repeat=7))
    l = [list(x) for x in l] # convert list of tuples to list of lists
    return l


def match_pattern(a, b):

    if len(a) != len(b):
        raise Exception("comparison failed, pattern length do not match ({}, {})".format(len(a), len(b)))

    for i in range(0, len(a)):

        if a[i] is None or b[i] is None: # None = don't care
            continue 

        if a[i] != b[i]:
            return False

    return True


def fill(h, lookup, q, r, s, patterns, lookup_keys):
    values = get(h, q, r, s)

    rot_collision_patterns = []
    for i in range(0, len(patterns)):
        p = patterns[i]

        # check if proposed pattern matches non-None parts of existing patterns
        if not match_pattern(p, values):
            continue

        # collision
        if lookup_keys[i] in lookup:
            continue

        # rotate pattern by -1 and check for collisions
        p_rot = [p[0]] + p[-5:] + p[1:-5]
        if make_lookup_key(p_rot) in lookup:
            rot_collision_patterns.append(p)
            continue

        # rotate pattern by +1 and check for collisions
        p_rot = [p[0]] + p[-1:] + p[1:-1]
        if make_lookup_key(p_rot) in lookup:
            rot_collision_patterns.append(p)
            continue

        # no collisions and no +1/-1 rotated collisions, all good
        set(h, lookup, q, r, s, p)
        return True

    # no perfect pattern found
    if not ABORT_FAST and len(rot_collision_patterns) > 0:
        set(h, lookup, q, r, s, rot_collision_patterns[0])
        return True

    return False


def is_filled(h, q, r, s):
    values = get(h, q, r, s)

    if None in values:
        return False
    else:
        return True


def fill_all(h, lookup, all_hexagons, patterns):

    # generate all lookup keys beforehand so it won't be redone
    # during pattern matching
    lookup_keys = []
    for p in patterns:
        lookup_keys.append(make_lookup_key(p))

    for q, r, s in all_hexagons:

        if not is_filled(h, q, r, s):
            success = fill(h, lookup, q, r, s, patterns, lookup_keys)
            if not success:
                return False

    return True


def fill_random(h, lookup):

    for r in range(-GRID_RADIUS, +(GRID_RADIUS+1)):
        for q in range(-GRID_RADIUS, +(GRID_RADIUS+1)):

            if r+q<-GRID_RADIUS+1 or r+q>GRID_RADIUS-1:
                continue

            s = -q -r 

            h["{}|{}|{}".format(q, r, s)] = choice([0, 1])

    for key in h.keys():

        q, r, s = [int(x) for x in key.split("|")]

        p = [h["{}|{}|{}".format(q, r, s)]]

        neighbours = get_neighbours(q, r, s)
        for n in neighbours:
            p.append(h["{}|{}|{}".format(*n)])

        # ignore the outermost ring of hexagons
        if len(p) != 7:
            continue

        lookup_key = make_lookup_key(p)
        if lookup_key in lookup:
            return False
        else:
            lookup[lookup_key] = [q, r, s]

    return True


def get(h, q, r, s):

    values = []

    values.append(h["{}|{}|{}".format(q, r, s)])
    for n in get_neighbours(q, r, s):
        values.append(h["{}|{}|{}".format(*n)])

    return values


def make_lookup_key(values):

    # if None in values:
    #     raise Exception("None value in key")

    key = [str(x) for x in values]
    return " ".join(key)


def set(h, lookup, q, r, s, values):

    # if None in values:
    #     raise Exception("setting None values: ", values)

    n = get_neighbours(q, r, s)

    h["{}|{}|{}".format(q, r, s)]   = values[0]
    h["{}|{}|{}".format(*n[0])]     = values[1]
    h["{}|{}|{}".format(*n[1])]     = values[2]
    h["{}|{}|{}".format(*n[2])]     = values[3]
    h["{}|{}|{}".format(*n[3])]     = values[4]
    h["{}|{}|{}".format(*n[4])]     = values[5]
    h["{}|{}|{}".format(*n[5])]     = values[6]

    key = make_lookup_key(values)

    # if key in lookup:
    #     raise Exception("creating collision")

    lookup[key] = [q, r, s]


def get_neighbours(q, r, s):

    if abs(q) == GRID_RADIUS:
        return []
    if abs(r) == GRID_RADIUS:
        return []
    if abs(s) == GRID_RADIUS:
        return []

    return [
        [q+1, r-1, s+0], # top right (1 o'clock)
        [q+1, r+0, s-1], # right (3 o'clock)
        [q+0, r+1, s-1], # ...
        [q-1, r+1, s+0],
        [q-1, r+0, s+1],
        [q+0, r-1, s+1], # top left (11 o'clock)
    ]


def pointy_hex_to_pixel(q, r, s, center=[0, 0]):
    x = HEX_SIZE * (math.sqrt(3) * q + math.sqrt(3)/2 * r)
    y = HEX_SIZE * (3./2 * r)
    return (x + center[0], y + center[1])


def convert(coords):
    # scale
    coords_scaled = [c*IMAGE_SCALE for c in coords]

    # flip axis for PIL's top-left coordinate system
    # coords_scaled[1] = DIMENSIONS[1]*IMAGE_SCALE - coords_scaled[1]
    # if len(coords) == 4:
    #     coords_scaled[3] = DIMENSIONS[1]*IMAGE_SCALE - coords_scaled[3]

    return tuple(coords_scaled)


def draw_image(h, info):

    with Image.new(mode="RGB", size=[DIMENSIONS[0]*IMAGE_SCALE, DIMENSIONS[1]*IMAGE_SCALE]) as im:
        draw = ImageDraw.Draw(im, "RGBA")

        # rot_marker_radius = 0.7
        rot_1 = info["rot_1"]
        rot_n = info["rot_n"]

        # # mark all hexagons that have a rotation duplicate that requires more than one rotation step
        # for item in rot_n:
        #     q, r, s = item
        #     x, y = pointy_hex_to_pixel(q, r, s, center=[DIMENSIONS[0]/2, DIMENSIONS[1]/2])
        #     draw.ellipse(
        #         convert([x-rot_marker_radius, y+rot_marker_radius, x+rot_marker_radius, y-rot_marker_radius]), 
        #         fill=None, outline=(100, 100, 100), width=3)

        # # mark all hexagons that have a rotation duplicate with only a single rotation step difference
        # for item in rot_1:
        #     q, r, s = item
        #     x, y = pointy_hex_to_pixel(q, r, s, center=[DIMENSIONS[0]/2, DIMENSIONS[1]/2])
        #     draw.ellipse(
        #         convert([x-rot_marker_radius, y+rot_marker_radius, x+rot_marker_radius, y-rot_marker_radius]), 
        #         fill=None, outline=(255, 0, 0), width=3)


        rot_n_occurences = Counter(rot_n)
        rot_1_occurences = Counter(rot_1)

        for r in range(-GRID_RADIUS, +(GRID_RADIUS+1)):
            for q in range(-GRID_RADIUS, +(GRID_RADIUS+1)):

                if r+q<-GRID_RADIUS or r+q>GRID_RADIUS:
                    continue

                s = -q -r 
                
                x, y = pointy_hex_to_pixel(q, r, s, center=[DIMENSIONS[0]/2, DIMENSIONS[1]/2])

                # hexagon fill (sides are drawn separately since PIL creates fat, overlapping lines when the polygons have an outline)
                f = None

                c = None
                rot_marker_radius = 0.7

                key = "{}|{}|{}".format(q, r, s)
                if key in rot_n_occurences:
                    c = (40*rot_n_occurences[key], 40*rot_n_occurences[key], 40*rot_n_occurences[key])
                if key in rot_1_occurences:
                    c = (120*rot_1_occurences[key], 0, 0)

                if c is not None:
                    draw.ellipse(
                        convert([x-rot_marker_radius, y-rot_marker_radius, x+rot_marker_radius, y+rot_marker_radius]), 
                        fill=None, outline=c, width=4)

                draw.polygon([
                        convert([x,                     y+HEX_SIZE,     ]),
                        convert([x+HEX_HORIZONTAL/2,    y+HEX_VERTICAL/3]),
                        convert([x+HEX_HORIZONTAL/2,    y-HEX_VERTICAL/3]),
                        convert([x,                     y-HEX_SIZE,     ]),
                        convert([x-HEX_HORIZONTAL/2,    y-HEX_VERTICAL/3]),
                        convert([x-HEX_HORIZONTAL/2,    y+HEX_VERTICAL/3])
                    ], outline=None, fill=f)

                # rot_marker_radius = 0.8
                # draw.ellipse(convert([x-rot_marker_radius, y+rot_marker_radius, x+rot_marker_radius, y-rot_marker_radius]), fill=(0, 0, 0))

                # hexagon sides
                c = (60, 60, 60)
                draw.line(convert([x,                     y+HEX_SIZE,         x+HEX_HORIZONTAL/2, y+HEX_VERTICAL/3]), width=3, fill=c)
                draw.line(convert([x+HEX_HORIZONTAL/2,    y+HEX_VERTICAL/3,   x+HEX_HORIZONTAL/2, y-HEX_VERTICAL/3]), width=3, fill=c)
                draw.line(convert([x+HEX_HORIZONTAL/2,    y-HEX_VERTICAL/3,   x,                  y-HEX_SIZE]),       width=3, fill=c)
                draw.line(convert([x,                     y-HEX_SIZE,         x-HEX_HORIZONTAL/2, y-HEX_VERTICAL/3]), width=3, fill=c)
                draw.line(convert([x-HEX_HORIZONTAL/2,    y-HEX_VERTICAL/3,   x-HEX_HORIZONTAL/2, y+HEX_VERTICAL/3]), width=3, fill=c)
                draw.line(convert([x-HEX_HORIZONTAL/2,    y+HEX_VERTICAL/3,   x,                  y+HEX_SIZE]),       width=3, fill=c)

                c = (25, 25, 25)
                try:
                    val = h["{}|{}|{}".format(q, r, s)]
                    if val is None:
                        c = (100, 100, 100)
                    else:
                        c = COLORS[val]
                except KeyError as ke:
                    pass

                # assuming 0.8mm drill size
                draw.ellipse(convert([x-.4, y-.4, x+.4, y+.4]), fill=c, width=10)

                # QRS coordinates for each hexagon
                draw.text(convert([x-0.75, y-0.75]),    "q: {}".format(q), (120, 120, 120), font=font)
                draw.text(convert([x+0.25, y-0.25]),    "r: {}".format(r), (120, 120, 120), font=font)
                draw.text(convert([x-0.75, y+0.5]),     "s: {}".format(s), (120, 120, 120), font=font)

                draw.text((50, 5+50),           "HEX SIZE:", (255, 255, 255), font=font_large)
                draw.text((50+300, 5+50),       " {:2.3f} mm".format(HEX_SIZE), (255, 255, 255), font=font_large_bold)

                draw.text((50, 5+50*2),         "INNER CIRCLE:", (255, 255, 255), font=font_large)
                draw.text((50+300, 5+50*2),     " {:2.2f} mm".format(INNER_CIRCLE_DIAM), (255, 255, 255), font=font_large_bold)

                draw.text((50, 5+50*3),         "NUM COLORS:", (255, 255, 255), font=font_large)
                draw.text((50+300, 5+50*3),     " {}".format(NUM_COLORS), (255, 255, 255), font=font_large_bold)

                draw.text((50, 5+50*4),         "GRID RADIUS:", (255, 255, 255), font=font_large)
                draw.text((50+300, 5+50*4),     " {}".format(GRID_RADIUS), (255, 255, 255), font=font_large_bold)

                draw.line([50, 20+50*5, 350, 20+50*5], width=1, fill=(80, 80, 80))

                draw.text((50, 5+50*6),         "total points:", (255, 255, 255), font=font_large)
                draw.text((50+300, 5+50*6),     " {}".format(len(h.keys())), (255, 255, 255), font=font_large_bold)

                draw.text((50, 5+50*7),         "penalties:", (255, 255, 255), font=font_large)
                draw.text((50+300, 5+50*7),     " {}".format(info["penalties"]), (255, 255, 255), font=font_large_bold)

                draw.text((50, 5+50*8),         "iteration:", (255, 255, 255), font=font_large)
                draw.text((50+300, 5+50*8),     " {}".format(info["iteration"]), (255, 255, 255), font=font_large_bold)


        draw.ellipse(convert([
            DIMENSIONS[0]/2-INNER_CIRCLE_DIAM/2, DIMENSIONS[1]/2-INNER_CIRCLE_DIAM/2, 
            DIMENSIONS[0]/2+INNER_CIRCLE_DIAM/2, DIMENSIONS[1]/2+INNER_CIRCLE_DIAM/2]), fill=None, outline=(100, 100, 100), width=3)

        filename = OUTPUT_IMAGE.format(prefix=info["prefix"], iteration=info["iteration"], penalties=info["penalties"])
        filename = os.path.join(OUTPUT_DIR.format(NUM_COLORS, GRID_RADIUS), filename)
        im.save(filename)
        # print("image written to: {}".format(filename))


def save_to_file(h, lookup, info):

    filename = OUTPUT_JSON.format(prefix=info["prefix"], iteration=info["iteration"], penalties=info["penalties"])
    filename = os.path.join(OUTPUT_DIR.format(NUM_COLORS, GRID_RADIUS), filename)

    with open(filename, "w") as f:

        data = {
            "HEX_SIZE":         HEX_SIZE,
            "HEX_HORIZONTAL":   HEX_HORIZONTAL,
            "HEX_VERTICAL":     HEX_VERTICAL,
            "NUM_COLORS":       NUM_COLORS,
            "GRID_RADIUS":      GRID_RADIUS,
            "data":             {},                 # "-2|1|1" --> 1
            "lookup_table":     lookup              # "0 1 0 0 1 0 0"  --> "-2|1|1"
        }

        for key in h.keys():
            data["data"][key] = h[key]

        json.dump(data, f)
        print("json written to: {}".format(filename))


def run(process_name, pattern_list, iterations):

    h = {}
    lookup = {}

    all_hexagons = get_all_hexagons()

    valid_results = 0
    penalties = []

    for i in range(0, int(iterations)):
        shuffle(pattern_list)

        # beware of shuffling the order of looking at the hexagons
        # if filling the hexes is randomized, filled hexes may
        # "encircle" an unfilled one and fill it passively (without
        # collision checks and lookup table entries). Results in
        # undetected duplicates.

        # shuffle(all_hexagons)

        try:
            h = init_h()
            lookup = {} 

            # pre-fill center hexagon and neighbours
            set(h, lookup, 0, 0, 0, UNIQUE_PATTERN)

            success = fill_all(h, lookup, all_hexagons, pattern_list)
            # success = fill_random(h, lookup)

            if success:
                valid_results += 1
                penalty_points, rot_1, rot_n = calculate_penalties(h, lookup)

                # print("{} | {:6} | generated pattern {} | penalty_points: {}".format(process_name, i, valid_results, penalty_points))

                if len(penalties) > 0 and penalty_points < min(penalties):
                
                    info = {
                        "penalties": penalty_points,
                        "iteration": i,
                        "rot_1": rot_1,
                        "rot_n": rot_n,
                        "prefix": process_name
                        }

                    if WRITE_IMAGE:
                        draw_image(h, info)

                    if WRITE_JSON:
                        save_to_file(h, lookup, info)

                penalties.append(penalty_points)

                if penalty_points == 0:
                    print("{} DONE. min penalty: {}, avg penalty {:5.2f}".format(process_name, min(penalties), sum(penalties)/len(penalties)))
                    sys.exit(0)

        except Exception as e:
            print("filling failed: {}".format(e))
            exc_info = sys.exc_info()
            traceback.print_exception(*exc_info)
            sys.exit(-1)


if __name__ == '__main__':

    try:
        os.makedirs(OUTPUT_DIR.format(NUM_COLORS, GRID_RADIUS))
    except Exception as e:
        pass

    print("total number of hexagons:        {}".format(int(1 + 6 * (GRID_RADIUS**2 + GRID_RADIUS)/2)))
    print("total number of patterns:        {} / {}".format(int(1 + 6 * ((GRID_RADIUS-1)**2 + (GRID_RADIUS-1))/2), NUM_COLORS**7))
    # print("total number of permutations:    {}".format(math.factorial(NUM_COLORS**7)))
    
    pattern_list = build_pattern_list()

    # remove unique pattern (and all rotational duplicates) from pattern_list
    for i in range(0, 6):
        p_rot = UNIQUE_PATTERN[i:] + UNIQUE_PATTERN[:i]
        try:
            pattern_list.remove(p_rot)
        except Exception as e:
            pass

    timer_start = datetime.datetime.now()

    #run("0", pattern_list, NUM_ITERATIONS)

    pool = multiprocessing.Pool()

    num_processes = 4
    iterations_per_process = int(NUM_ITERATIONS/num_processes)

    print("running processes: {} / iterations per process: {}".format(num_processes, iterations_per_process))

    results = []
    for name in [str(i) for i in range(0, num_processes)]:
        results.append(pool.apply_async(run, [name, copy.deepcopy(pattern_list), iterations_per_process]))
    for res in results:
        res.get()

    timer_end = datetime.datetime.now()
    diff = timer_end - timer_start
    print("total time: {}s".format(diff.total_seconds()))

    with open(OUTPUT_REPORT, "a") as f:
        f.write("started: {} | finished {} | iterations: {} | duration: {:10.2f}s\n".format(timer_start, timer_end, int(NUM_ITERATIONS), diff.total_seconds()))
