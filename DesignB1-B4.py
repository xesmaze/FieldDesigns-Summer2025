
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import random
import pandas as pd

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

# === Entry Definitions ===
designs = {
    1: {
        'A': ["AG29XF4", "AG29XF5", "AG34XF6", "AG35XF5", "AG36XF4", "AG38XF6", "AG40XFF5"],
        'B': ["LG3216"],
        'A_COLOR': '#c6dbef',
        'B_COLOR': '#c7e9c0'
    },
    2: {
        'A': [
            "LD20-4542", "LD20-4988", "LD20-4471", "LD20-5738", "LD22-4283",
            "LD11-2170", "LD20-5413", "LD21-5253", "LD21-7234"
        ],
        'B': ["AG29XF4", "AG29XF5"],
        'A_COLOR': '#f2f0f7',
        'B_COLOR': '#deebf7'
    },
    3: {
        'A': [
            "LD11-2170", "LD20-4471", "LD20-4542", "LD20-4988", "LD20-5738", "LD22-4283",
            "LD00-2817P", "LD17-10473L", "LD19-10076", "LD19-10244", "LD21-5944", "LD21-5991",
            "LD07-3395bf", "LD17-10473F", "LD20-11748", "LD20-5413", "LD21-3090", "LD21-5253",
            "LD21-5665", "LD21-7234"
        ],
        'B': ["LG3216"],
        'A_COLOR': '#fdd0a2',
        'B_COLOR': '#c7e9c0'
    },
    4: {
        'A': ["AG34XF6", "AG35XF5", "AG36XF4", "AG38XF6", "AG40XFF5"],
        'B': [
            "LD21-5253", "LD21-7234", "LD21-5665", "LD21-3090", "LD07-3395bf",
            "LD17-10473F", "LD20-11748", "LD21-5944"
        ],
        'A_COLOR': '#d0d1e6',
        'B_COLOR': '#ccebc5'
    }
}

# Recursive sampler
def recursive_sampler(pool):
    while True:
        shuffled = pool.copy()
        random.shuffle(shuffled)
        for entry in shuffled:
            yield entry

# === Drawing Layout ===
data = []
fig, ax = plt.subplots(figsize=(14, 12))
ax.add_patch(patches.Rectangle((0, 0), field_width, field_height,
                               edgecolor='black', facecolor='lightgray', linewidth=1.5))
ax.add_patch(patches.Rectangle((border_thickness, border_thickness),
                               usable_width, usable_height,
                               edgecolor='none', facecolor='white'))

design_blocks = {1: 1, 2: 2, 3: 3, 4: 4}  # Block assignments

block_id = 1
for i in range(rows):
    for j in range(cols):
        bl_x = border_thickness + j * (block_width + gap_x)
        bl_y = border_thickness + i * (block_height + gap_y)
        ax.add_patch(patches.Rectangle((bl_x, bl_y), block_width, block_height,
                                       edgecolor='black', facecolor='white', linewidth=1.5))

        design_idx = [d for d, b in design_blocks.items() if b == block_id]
        if design_idx:
            design = designs[design_idx[0]]
            a_gen = recursive_sampler(design['A'])
            b_gen = recursive_sampler(design['B'])

        for r in range(cell_rows):
            for c in range(cell_cols):
                cell_x = bl_x + c * cell_width
                cell_y = bl_y + r * cell_height

                if design_idx:
                    label = next(a_gen) if (r + c) % 2 == 0 else next(b_gen)
                    color = design['A_COLOR'] if (r + c) % 2 == 0 else design['B_COLOR']
                    ax.add_patch(patches.Rectangle((cell_x, cell_y), cell_width, cell_height,
                                                   edgecolor='lightgray', facecolor=color, linewidth=0.8))
                    ax.text(cell_x + cell_width / 2, cell_y + cell_height / 2, label,
                            ha='center', va='center', fontsize=5.5, rotation=90)
                else:
                    label = ""
                    ax.add_patch(patches.Rectangle((cell_x, cell_y), cell_width, cell_height,
                                                   edgecolor='lightgray', facecolor='none', linewidth=0.8))

                data.append({
                    "Block": f"B{block_id}",
                    "Row": r,
                    "Col": c,
                    "X": round(cell_x + cell_width / 2, 2),
                    "Y": round(cell_y + cell_height / 2, 2),
                    "Label": label
                })

        ax.text(bl_x + block_width / 2, bl_y + block_height / 2,
                f"B{block_id}", ha='center', va='center', fontsize=10, weight='bold')
        block_id += 1

# Finalize layout
ax.set_xlim(-5, field_width + 10)
ax.set_ylim(0, field_height + 40)
ax.set_aspect('equal')
ax.set_title("Field Layout: Designs 1–4 Applied to Blocks B1–B4")
ax.axis('off')
plt.tight_layout()

# Save figure and data
plt.savefig("combined_field_designs_1_to_4.png")
df = pd.DataFrame(data)
df.to_csv("combined_field_designs_1_to_4.csv", index=False)
plt.show()
