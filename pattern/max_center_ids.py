# This script brute-forces the numer of rotation-invariant patterns for a single hexagon (2 colors)

def rotate(strg, n):
    return strg[n:] + strg[:n]


def get_all_rotations(p):
    rots = {}
    for i in range(0, 6):
        r = p[0] + rotate(p[1:], i)
        rots[r] = None

    return rots.keys()

print("max number of patterns: {}".format(2**7))

all_patterns = []
rot_unique_patterns = {}

for i in range(0, 2**7):
    pattern = "{:07b}".format(i)
    rots = get_all_rotations(pattern)
    # print(pattern, len(rots))

    if len(rots) == 1:
        rot_unique_patterns[pattern] = None
    else:
        dup = False
        for r in rots:
            if r in rot_unique_patterns:
                dup = True
                break
        if not dup:
            rot_unique_patterns[pattern] = None

print("patterns:")
for p in rot_unique_patterns.keys():
    print(p)

print("number of rot unique patterns: {}".format(len(rot_unique_patterns.keys())))