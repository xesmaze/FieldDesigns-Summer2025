# Updated script with random seed control for reproducibility

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


# --- Helper Functions ---
def generate_pairings(source_A, source_B, num_pairs):
    return [(source_A[i % len(source_A)], source_B[i % len(source_B)]) for i in range(num_pairs)]


def add_subblock(ax, x_offset, y_offset, A_vars, B_vars, colorA, colorB):
    effective_block_length = subblock_height / new_num_blocks
    block_length = effective_block_length - spacing_between_blocks
    total_track_width = num_tracks * track_width
    remaining_width = subblock_width - total_track_width
    track_spacing = remaining_width / (num_tracks + 1)

    pairings = generate_pairings(A_vars, B_vars, (new_num_blocks // 2) * num_tracks)
    pair_index = 0

    for t in range(num_tracks):
        x_start = x_offset + track_spacing + t * (track_width + track_spacing)
        order = ("A", "B") if t % 2 == 0 else ("B", "A")

        for b in range(0, new_num_blocks, 2):
            if pair_index >= len(pairings):
                break
            varA, varB = pairings[pair_index]
            pair_index += 1
            var_top = varA if order[0] == "A" else varB
            var_bottom = varB if order[0] == "A" else varA

            y1 = y_offset + b * (subblock_height / new_num_blocks)
            y2 = y_offset + (b + 1) * (subblock_height / new_num_blocks)

            ax.add_patch(patches.Rectangle((x_start, y1), track_width, block_length,
                                           edgecolor='black',
                                           facecolor=colorA.get(var_bottom, colorB.get(var_bottom, 'gray')),
                                           linewidth=0.5))
            ax.add_patch(patches.Rectangle((x_start, y2), track_width, block_length,
                                           edgecolor='black',
                                           facecolor=colorA.get(var_top, colorB.get(var_top, 'gray')), linewidth=0.5))


def generate_non_adjacent_row_pattern(seed=None):
    if seed is not None:
        random.seed(seed)
    idx = [0, 1, 2, 3]
    valid_perms = [p for p in permutations(idx) if all(p[i] != p[i + 1] for i in range(3))]
    return [random.choice(valid_perms) for _ in range(rows)]


# === Set Seed for Reproducibility ===
seed_value = 123  # Change this number for different randomized layouts
row_patterns = generate_non_adjacent_row_pattern(seed=seed_value)

# Shuffle middle row separately with new seed
random.seed(seed_value + 1)
middle_row = row_patterns[1]
alt_perms = [p for p in permutations([0, 1, 2, 3]) if
             all(p[i] != p[i + 1] for i in range(3)) and p != tuple(middle_row)]
if alt_perms:
    row_patterns[1] = random.choice(alt_perms)

# === Plot the Final Layout ===
fig, ax = plt.subplots(figsize=(14, 18))
ax.set_xlim(0, field_width)
ax.set_ylim(0, field_height)
ax.set_aspect('equal')
legend_all = {}

for r in range(rows):
    layout = row_patterns[r]
    for c in range(cols):
        sb_idx = layout[c]
        A, B, colorA, colorB = subblock_defs_row_pattern[sb_idx]
        x_off = c * (subblock_width + block_spacing_x)
        y_off = r * (subblock_height + block_spacing_y)
        add_subblock(ax, x_off, y_off, A, B, colorA, colorB)
        legend_all.update(colorA)
        legend_all.update(colorB)

# --- Legend ---
ax.set_title(f"Finalized Trial Layout (Seed = {seed_value})", fontsize=14)
ax.set_xlabel("Width (ft)")
ax.set_ylabel("Height (ft)")
plt.grid(False)

legend_elements = [Line2D([0], [0], marker='s', color='w',
                          label=v, markerfacecolor=legend_all[v], markersize=6)
                   for v in legend_all]
ax.legend(handles=legend_elements, title="Varieties", bbox_to_anchor=(1.05, 1), loc='upper left', fontsize=6)

plt.tight_layout()
plt.show()
plt.savefig("full_field_seed 123.png")
