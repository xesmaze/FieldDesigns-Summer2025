## Sub-block 3 - Bayer vs IL
# Re-import necessary libraries after kernel reset
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.lines import Line2D
import numpy as np

# Define plotting function with actual B variety names
def plot_subblock_actual_names(subblock_width, subblock_height, num_tracks, track_width, spacing_between_tracks,
                                new_num_blocks, spacing_between_blocks, source_A_varieties, source_B_varieties,
                                cmap_name_A="Purples", cmap_name_B="Oranges", title="Subblock Layout",
                                fixed_color_A=True):
    effective_block_length = subblock_height / new_num_blocks
    block_length = effective_block_length - spacing_between_blocks
    total_track_width = num_tracks * track_width
    remaining_width = subblock_width - total_track_width
    track_spacing = remaining_width / (num_tracks + 1)

    cmap_A = plt.get_cmap(cmap_name_A, len(source_A_varieties))
    cmap_B = plt.get_cmap(cmap_name_B, len(source_B_varieties))

    colors_A = [cmap_A(0.6)] * len(source_A_varieties) if fixed_color_A else \
               [cmap_A(i / len(source_A_varieties)) for i in range(len(source_A_varieties))]

    colors_B = [cmap_B(i / len(source_B_varieties)) for i in range(len(source_B_varieties))]

    variety_colors = {v: colors_A[i % len(colors_A)] for i, v in enumerate(source_A_varieties)}
    variety_colors.update({v: colors_B[i] for i, v in enumerate(source_B_varieties)})

    num_pairs = (new_num_blocks // 2) * num_tracks
    pairings = [(source_A_varieties[0], source_B_varieties[i % len(source_B_varieties)])
                for i in range(num_pairs)]

    fig, ax = plt.subplots(figsize=(7, 15))
    ax.add_patch(patches.Rectangle((0, 0), subblock_width, subblock_height,
                                   linewidth=2, edgecolor='black', facecolor='none'))

    pair_index = 0
    for t in range(num_tracks):
        x_start = track_spacing + t * (track_width + track_spacing)
        block_indices = range(0, new_num_blocks, 2)
        source_order = ("A", "B") if t % 2 == 0 else ("B", "A")

        for b in block_indices:
            if pair_index >= len(pairings):
                break

            y1 = b * effective_block_length
            y2 = (b + 1) * effective_block_length
            varA, varB = pairings[pair_index]
            pair_index += 1

            var_top = varA if source_order[0] == "A" else varB
            var_bottom = varB if source_order[0] == "A" else varA

            rect_bottom = patches.Rectangle((x_start, y1), track_width, block_length,
                                            linewidth=1, edgecolor='black', facecolor=variety_colors[var_bottom])
            ax.add_patch(rect_bottom)
            ax.text(x_start + track_width / 2, y1 + block_length / 2, var_bottom,
                    ha='center', va='center', fontsize=6)

            rect_top = patches.Rectangle((x_start, y2), track_width, block_length,
                                         linewidth=1, edgecolor='black', facecolor=variety_colors[var_top])
            ax.add_patch(rect_top)
            ax.text(x_start + track_width / 2, y2 + block_length / 2, var_top,
                    ha='center', va='center', fontsize=6)

    ax.set_xlim(0, subblock_width)
    ax.set_ylim(0, subblock_height)
    ax.set_aspect('equal')
    ax.set_title(title)
    ax.set_xlabel('Width (ft)')
    ax.set_ylabel('Height (ft)')
    plt.grid(False)

    legend_elements = [Line2D([0], [0], marker='s', color='w',
                              label=v, markerfacecolor=variety_colors[v], markersize=8)
                       for v in variety_colors]
    ax.legend(handles=legend_elements, title="Varieties", bbox_to_anchor=(1.05, 1), loc='upper left')

    plt.tight_layout()
    plt.show()

# Execute the plotting function with actual variety names
plot_subblock_actual_names(
    subblock_width=35,
    subblock_height=94,
    num_tracks=5,
    track_width=5,
    spacing_between_tracks=2,
    new_num_blocks=12,
    spacing_between_blocks=1,
    source_A_varieties=["A1"],
    source_B_varieties=["AG29XF4", "AG29XF5", "AG34XF6", "AG35XF5", "AG36XF4", "AG38XF6", "AG40XFF5"],
    title="Subblock 3: A1 vs Actual B Varieties (7 Total, Alternating)"
)
