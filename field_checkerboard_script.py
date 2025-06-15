# Run gridLayout.py first
# This is for checkboard splitplot design

import matplotlib.pyplot as plt
import matplotlib.patches as patches

# === Field Setup ===
field_width = 160
field_height = 270
border_thickness = 10
cols = 4
rows = 3
gap_x = 3
gap_y = 3

# Usable area
usable_width = field_width - 2 * border_thickness
usable_height = field_height - 2 * border_thickness

# Block and cell dimensions
block_width = (usable_width - (cols - 1) * gap_x) / cols
block_height = (usable_height - (rows - 1) * gap_y) / rows
cell_cols = 5
cell_rows = 8
cell_width = block_width / cell_cols
cell_height = block_height / cell_rows

# Create figure
fig, ax = plt.subplots(figsize=(14, 12))

# Field outer border
ax.add_patch(patches.Rectangle((0, 0), field_width, field_height,
                               edgecolor='black', facecolor='lightgray', linewidth=1.5))
# Usable area
ax.add_patch(patches.Rectangle((border_thickness, border_thickness),
                               usable_width, usable_height,
                               edgecolor='none', facecolor='white'))

# Draw field corner labels
ax.text(1, 1, "(0, 0)", ha='left', va='bottom', fontsize=8, rotation=90)
ax.text(field_width - 1, 1, f"({field_width}, 0)", ha='right', va='bottom', fontsize=8, rotation=90)
ax.text(1, field_height - 1, f"(0, {field_height})", ha='left', va='top', fontsize=8, rotation=90)
ax.text(field_width - 1, field_height - 1, f"({field_width}, {field_height})", ha='right', va='top', fontsize=8, rotation=90)

# Draw blocks with alternating checkerboard pattern
block_id = 1
for i in range(rows):
    for j in range(cols):
        bl_x = border_thickness + j * (block_width + gap_x)
        bl_y = border_thickness + i * (block_height + gap_y)

        # Draw block
        ax.add_patch(patches.Rectangle((bl_x, bl_y), block_width, block_height,
                                       edgecolor='black', facecolor='white', linewidth=1.5))

        # Checkerboard pattern starting label
        base_label = 'A' if block_id % 2 == 1 else 'B'
        alt_label = 'B' if base_label == 'A' else 'A'

        # Draw internal cells
        for r in range(cell_rows):
            for c in range(cell_cols):
                cell_x = bl_x + c * cell_width
                cell_y = bl_y + r * cell_height
                label = base_label if (r + c) % 2 == 0 else alt_label
                ax.add_patch(patches.Rectangle((cell_x, cell_y), cell_width, cell_height,
                                               edgecolor='lightgray', facecolor='none', linewidth=0.8))
                ax.text(cell_x + cell_width / 2, cell_y + cell_height / 2, label,
                        ha='center', va='center', fontsize=6)

        # Block ID label
        ax.text(bl_x + block_width / 2, bl_y + block_height / 2,
                f"B{block_id}", ha='center', va='center', fontsize=10, weight='bold')
        block_id += 1

# Final layout
ax.set_xlim(-5, field_width + 10)
ax.set_ylim(0, field_height + 40)
ax.set_aspect('equal')
ax.set_title("Field Layout with Alternating Checkerboard Start per Block (8x5 cells)")
ax.axis('off')
plt.tight_layout()

# Save to file
plt.savefig("field_checkerboard_alternating_blocks.png")
