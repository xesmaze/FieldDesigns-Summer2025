import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Field dimensions
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

# Block dimensions
block_width = (usable_width - (cols - 1) * gap_x) / cols
block_height = (usable_height - (rows - 1) * gap_y) / rows

# Cell layout
cell_cols = 5  # E/W
cell_rows = 8  # N/S
cell_width = block_width / cell_cols
cell_height = block_height / cell_rows

# Precompute block coordinates
block_coords = []
block_id = 1
for i in range(rows):
    for j in range(cols):
        x0 = border_thickness + j * (block_width + gap_x)
        y0 = border_thickness + i * (block_height + gap_y)
        x1 = x0 + block_width
        y1 = y0 + block_height
        block_coords.append((f"B{block_id}", x0, y0, x1, y0, x0, y1, x1, y1))
        block_id += 1

# Draw the layout
fig, ax = plt.subplots(figsize=(14, 12))
ax.add_patch(patches.Rectangle((0, 0), field_width, field_height,
                               edgecolor='black', facecolor='lightgray', linewidth=1.5))
ax.add_patch(patches.Rectangle((border_thickness, border_thickness),
                               usable_width, usable_height,
                               edgecolor='none', facecolor='white'))

# Label field perimeter corners
ax.text(1, 1, "(0, 0)", ha='left', va='bottom', fontsize=8, rotation=90)
ax.text(field_width - 1, 1, f"({field_width}, 0)", ha='right', va='bottom', fontsize=8, rotation=90)
ax.text(1, field_height - 1, f"(0, {field_height})", ha='left', va='top', fontsize=8, rotation=90)
ax.text(field_width - 1, field_height - 1, f"({field_width}, {field_height})", ha='right', va='top', fontsize=8, rotation=90)

# Draw blocks and internal 5x8 cells
for block in block_coords:
    block_id, bl_x, bl_y, br_x, br_y, tl_x, tl_y, tr_x, tr_y = block
    width = br_x - bl_x
    height = tl_y - bl_y

    # Draw block outline
    ax.add_patch(patches.Rectangle((bl_x, bl_y), width, height,
                                   edgecolor='black', facecolor='white', linewidth=1.5))

    # Draw internal grid cells
    for r in range(cell_rows):
        for c in range(cell_cols):
            cell_x = bl_x + c * cell_width
            cell_y = bl_y + r * cell_height
            ax.add_patch(patches.Rectangle((cell_x, cell_y), cell_width, cell_height,
                                           edgecolor='lightgray', facecolor='none', linewidth=0.8))

    # Label corners
    ax.text(bl_x + 1, bl_y + 1, f"({int(bl_x)}, {int(bl_y)})", ha='left', va='bottom', fontsize=7, rotation=90, color='green')
    ax.text(br_x - 1, br_y + 1, f"({int(br_x)}, {int(br_y)})", ha='right', va='bottom', fontsize=7, rotation=90, color='green')
    ax.text(tl_x + 1, tl_y - 1, f"({int(tl_x)}, {int(tl_y)})", ha='left', va='top', fontsize=7, rotation=90, color='red')
    ax.text(tr_x - 1, tr_y - 1, f"({int(tr_x)}, {int(tr_y)})", ha='right', va='top', fontsize=7, rotation=90, color='red')

    # Label block ID
    ax.text(bl_x + width / 2, bl_y + height / 2, block_id, ha='center', va='center', fontsize=10, weight='bold')

# Final layout settings
ax.set_xlim(-5, field_width + 10)
ax.set_ylim(0, field_height + 40)
ax.set_aspect('equal')
ax.set_title("Standalone Field Layout with 5x8 Grid Inside Each Block")
ax.axis('off')
plt.tight_layout()
plt.savefig("field_with_5x8_cells_per_block.png")
