# Define a function to generate a full 4x3 layout with rejection sampling to avoid adjacent identical subblocks

import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.lines import Line2D
import numpy as np
import random
from itertools import permutations

# --- Constants ---
subblock_width = 35
subblock_height = 94
num_tracks = 5
track_width = 5
spacing_between_tracks = 2
new_num_blocks = 12
spacing_between_blocks = 1
block_spacing_x = 5
block_spacing_y = 5
cols = 4
rows = 3

field_width = cols * subblock_width + (cols - 1) * block_spacing_x
field_height = rows * subblock_height + (rows - 1) * block_spacing_y

# --- Variety Definitions ---
AG = ["AG29XF4", "AG29XF5", "AG34XF6", "AG35XF5", "AG36XF4", "AG38XF6", "AG40XFF5"]
LD = [
    "LD11-2170", "LD20-4471", "LD20-4542", "LD20-4988", "LD20-5738", "LD22-4283",
    "LD00-2817P", "LD17-10473L", "LD19-10076", "LD19-10244", "LD21-5944", "LD21-5991",
    "LD07-3395bf", "LD17-10473F", "LD20-11748", "LD20-5413", "LD21-3090", "LD21-5253",
    "LD21-5665", "LD21-7234"
]
LG = ["LG3216"]

# --- Color Maps ---
cmap_AG = plt.get_cmap("Oranges", len(AG))
cmap_LD = plt.get_cmap("Greens", len(LD))
color_AG = {v: cmap_AG(i / len(AG)) for i, v in enumerate(AG)}
color_LD = {v: cmap_LD(i / len(LD)) for i, v in enumerate(LD)}
color_LG = {"LG3216": "lightblue"}

# --- Subblock Types ---
subblock_defs_row_pattern = [
    (AG, LD, color_AG, color_LD),  # AG vs LD
    (AG, LD, color_AG, color_LD),  # AG vs LD
    (AG, LG, color_AG, color_LG),  # AG vs LG3216
    (LD, LG, color_LD, color_LG)  # LD vs LG3216
]

def is_valid_grid(grid):
    for i in range(rows):
        for j in range(cols):
            current = grid[i][j]
            if i > 0 and grid[i-1][j] == current:
                return False
            if j > 0 and grid[i][j-1] == current:
                return False
    return True

def generate_full_field_layout(seed=None, max_attempts=10000):
    if seed is not None:
        random.seed(seed)
    idx = [0, 1, 2, 3]  # 4 types of subblocks
    attempts = 0
    while attempts < max_attempts:
        attempts += 1
        flat = random.choices(idx, k=rows * cols)
        grid = [flat[i*cols:(i+1)*cols] for i in range(rows)]
        if is_valid_grid(grid):
            return grid
    raise ValueError("Could not find a valid layout without adjacent duplicates after many attempts.")

# Attempt to find a valid full field layout
valid_layout = generate_full_field_layout(seed=123)

# Plot the layout with rejection-sampled block arrangement
fig, ax = plt.subplots(figsize=(14, 18))
ax.set_xlim(0, field_width)
ax.set_ylim(0, field_height)
ax.set_aspect('equal')
legend_all = {}

for r in range(rows):
    for c in range(cols):
        sb_idx = valid_layout[r][c]
        A, B, colorA, colorB = subblock_defs_row_pattern[sb_idx]
        x_off = c * (subblock_width + block_spacing_x)
        y_off = r * (subblock_height + block_spacing_y)
        add_subblock(ax, x_off, y_off, A, B, colorA, colorB)
        legend_all.update(colorA)
        legend_all.update(colorB)

# --- Legend ---
ax.set_title("4×3 Layout with No Adjacent Identical Subblocks (Rejection Sampled)", fontsize=14)
ax.set_xlabel("Width (ft)")
ax.set_ylabel("Height (ft)")
plt.grid(False)

legend_elements = [Line2D([0], [0], marker='s', color='w',
                          label=v, markerfacecolor=legend_all[v], markersize=6)
                   for v in legend_all]
ax.legend(handles=legend_elements, title="Varieties", bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=6)

plt.tight_layout()
plt.show()
