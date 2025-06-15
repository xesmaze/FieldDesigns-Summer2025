
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import random

# === Field Setup ===
field_width = 160
field_height = 270
border_thickness = 10
cols = 4
rows = 3
gap_x = 3
gap_y = 3
usable_width = field_width - 2 * border_thickness
usable_height = field_height - 2 * border_thickness
block_width = (usable_width - (cols - 1) * gap_x) / cols
block_height = (usable_height - (rows - 1) * gap_y) / rows
cell_cols = 5
cell_rows = 8
cell_width = block_width / cell_cols
cell_height = block_height / cell_rows

# AG entries to assign to "A" cells
ag_entries = ["AG29XF4", "AG29XF5", "AG34XF6", "AG35XF5", "AG36XF4", "AG38XF6", "AG40XFF5"]

# Recursive sampler
def recursive_sampler(pool):
    while True:
        shuffled = pool.copy()
        random.shuffle(shuffled)
        for entry in shuffled:
            yield entry

# Colors
AG_COLOR = '#c6dbef'      # light blue
LG3216_COLOR = '#c7e9c0'  # light green

# Initialize plot
fig, ax = plt.subplots(figsize=(14, 12))
ax.add_patch(patches.Rectangle((0, 0), field_width, field_height,
                               edgecolor='black', facecolor='lightgray', linewidth=1.5))
ax.add_patch(patches.Rectangle((border_thickness, border_thickness),
                               usable_width, usable_height,
                               edgecolor='none', facecolor='white'))

# Draw grid
ag_sampler = recursive_sampler(ag_entries)
block_id = 1
target_block = 1

for i in range(rows):
    for j in range(cols):
        bl_x = border_thickness + j * (block_width + gap_x)
        bl_y = border_thickness + i * (block_height + gap_y)
        ax.add_patch(patches.Rectangle((bl_x, bl_y), block_width, block_height,
                                       edgecolor='black', facecolor='white', linewidth=1.5))

        for r in range(cell_rows):
            for c in range(cell_cols):
                cell_x = bl_x + c * cell_width
                cell_y = bl_y + r * cell_height

                if block_id == target_block:
                    if (r + c) % 2 == 0:
                        label = next(ag_sampler)
                        facecolor = AG_COLOR
                    else:
                        label = "LG3216"
                        facecolor = LG3216_COLOR

                    ax.add_patch(patches.Rectangle((cell_x, cell_y), cell_width, cell_height,
                                                   edgecolor='lightgray', facecolor=facecolor, linewidth=0.8))
                    ax.text(cell_x + cell_width / 2, cell_y + cell_height / 2, label,
                            ha='center', va='center', fontsize=5.5, rotation=90)
                else:
                    ax.add_patch(patches.Rectangle((cell_x, cell_y), cell_width, cell_height,
                                                   edgecolor='lightgray', facecolor='none', linewidth=0.8))

        ax.text(bl_x + block_width / 2, bl_y + block_height / 2,
                f"B{block_id}", ha='center', va='center', fontsize=10, weight='bold')
        block_id += 1

# Final layout settings
ax.set_xlim(-5, field_width + 10)
ax.set_ylim(0, field_height + 40)
ax.set_aspect('equal')
ax.set_title("Design 1 (B1): AG vs LG3216 (Color Fill + Rotated Text)")
ax.axis('off')
plt.tight_layout()
plt.savefig("field_design1_blockB1_AG_vs_LG3216_colored_rotated.png")
plt.show()
