Execute with PyPy for a 20-25% speedup.

```pypy3 generate.py```

![Debug output for a generated pattern](/media/2678_output_3_i-1725881.png)

Hexagons are handled in the QRS coordinate system. Refer to https://www.redblobgames.com/grids/hexagons/ for a detailed overview.

All hexagons in "pointy top" orientation.

PIL coordinate system origin is top-left.

All dimensions in mm, except when drawing on PIL's canvas.

We want a DeBruijn-like 2D map of hexagons, ie. each hexagonal sliding window should show a pattern of points (one center, 6 in the ring) that is unique in the whole map. Wording: "pattern" = 7 points, all points = "map". A perfect map would contain unique patterns that can only be found once and have no duplicates if rotated. A good map contains only unique patterns or patterns that need to be rotated more than one position forward or backward to create a duplicate.

General procedure:

 *  make a list of a all possible combinations of colors that 
    can be a pattern (ie. 2 colors = 2^7=128 patterns)

 *  shuffle that list

 *  pick the first pattern from the list and assign to center hex

 *  iteratively test and assign patterns from the list to all 
    neighbouring hexes that match up with the already assigned 
    patterns

 *  if all hexes are filled successful calculate penalty (low 
    penalty for duplicated that require more than one rotation, 
    very high penalty for +1/-1 rot duplicates. Increase penalty
    for duplicates close to the center of the map

 *  shuffle the pattern list and repeat