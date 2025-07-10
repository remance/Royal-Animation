Animation

This folder contains list of animation for each direction.

The animation file need to be in this structure:
Animation name, each p*number* (upto p4) parts, effect, frame and animation properties

Animation name should be like this

Each animation part need to be in this format:
race/type, part name, position x, position y, angle, flip (0=none, 1=horizontal), layer, width scale, height scale (1
for default), do dmg

THERE MUST BE NO SPACE BETWEEN COMMA IN ANY VALUE

The position is based on the default side (right direction).

layer value is similar to pygame layer, the higher value get drew first and lower value get drew later and above the
higher value layer. Layer must start from 0.
