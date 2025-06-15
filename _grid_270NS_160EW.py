import matplotlib.pyplot as plt
import matplotlib.patches as patches

# Constants
field_width = 160
field_height = 270
replicate_rows = 3
subblock_cols = 4

# Subblock dimensions
subblock_width = field_width / subblock_cols  # 40 ft
subblock_height = field_height / replicate_rows  # 90 ft

# Cell height and row spacing (N/S)
cell_height = 7
row_spacing = 2
cell_total_height = cell_height + row_spacing
num_cell_rows = int(subblock_height // cell_total_height)  # 10 rows

# Adjusted cell width to allow 30" (2.5') between subblocks
inter_subblock_spacing = 2.5  # feet
usable_width = subblock_width - 2 * inter_subblock_spacing
num_cell_cols = int(usable_width // 5)
cell_width = usable_width / num_cell_cols

# Global cell grid dimensions
total_cols = subblock_cols * num_cell_cols
total_rows = replicate_rows * num_cell_rows

# Create figure
fig, ax = plt.subplots(figsize=(12, 10))
block_id = 1

# Track the lowest and highest cell Y values for adjusting plot bounds later
min_y = float('inf')
max_y = float('-inf')

for r in range(replicate_rows):
    for c in range(subblock_cols):
        origin_x = c * subblock_width
        origin_y = field_height - (r + 1) * subblock_height

        # Draw subblock frame
        ax.add_patch(patches.Rectangle((origin_x, origin_y), subblock_width, subblock_height,
                                       edgecolor='black', facecolor='none', linewidth=1))
        ax.text(origin_x + subblock_width / 2, origin_y + subblock_height / 2,
                f"SB{block_id}", ha='center', va='center', fontsize=8)
        block_id += 1

        # Draw cells
        for i in range(num_cell_rows):
            for j in range(num_cell_cols):
                global_row = r * num_cell_rows + i
                global_col = c * num_cell_cols + j

                cell_x = origin_x + inter_subblock_spacing + j * cell_width
                cell_y = origin_y + i * cell_total_height

                min_y = min(min_y, cell_y)
                max_y = max(max_y, cell_y + cell_height)

                # Identify field-level border cells
                is_border = (global_row == 0 or global_row == total_rows - 1 or
                             global_col == 0 or global_col == total_cols - 1)

                facecolor = 'gray' if is_border else 'lightblue'
                edgecolor = 'black' if is_border else 'blue'

                ax.add_patch(patches.Rectangle((cell_x, cell_y), cell_width, cell_height,
                                               edgecolor=edgecolor, facecolor=facecolor, linewidth=0.5))

# Final layout settings
ax.set_xlim(0, field_width)
ax.set_ylim(min_y - 2, max_y + 2)
ax.set_aspect('equal')
ax.set_title("Field Layout with Full Perimeter Border Cells and 30\" Internal Spacing")
ax.axis('off')
plt.tight_layout()
plt.show()
