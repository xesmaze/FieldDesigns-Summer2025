
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.backends.backend_pdf import PdfPages

st.set_page_config(page_title="📘 Fieldbook PDF Generator", layout="centered")
st.title("📘 Generate Fieldbook PDF with GPS-Aligned Coordinates")

uploaded_file = st.file_uploader("Upload GPS-aligned CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)

    # Recalculate geometry
    cell_width = 3.3
    cell_height = 10  # planted row length
    df['X_start'] = df['X'] - cell_width / 2
    df['X_stop'] = df['X'] + cell_width / 2
    df['Y_start'] = df['Y'] - cell_height / 2
    df['Y_stop'] = df['Y'] + cell_height / 2

    blocks = sorted(df[df['Block'] != 'T0']['Block'].unique(), key=lambda x: int(x[1:]))

    a5_inches = (5.8, 8.3)
    pdf_path = "/tmp/FieldBook_A5_GPSAligned.pdf"
    pdf = PdfPages(pdf_path)

    # Page 1: Text summary
    fig, ax = plt.subplots(figsize=a5_inches)
    ax.axis('off')
    ax.text(0.1, 0.8, "Fieldbook with GPS-Aligned Coordinates", fontsize=12, weight='bold')
    ax.text(0.1, 0.6, "Each block includes updated start/stop coordinates based on the GPS-aligned T0 anchor.", fontsize=9)
    ax.text(0.1, 0.4, f"Uploaded File: {uploaded_file.name}", fontsize=8)
    pdf.savefig(fig, bbox_inches='tight')
    plt.close(fig)

    # Entry list page
    fig2, ax2 = plt.subplots(figsize=a5_inches)
    entry_list = df[df['Block'] != 'T0'][['Label']].drop_duplicates().reset_index(drop=True)
    entry_list.index = entry_list.index + 1
    ax2.axis('off')
    table_data = [["Entry#", "Label"]] + [[i, row.Label] for i, row in entry_list.iterrows()]
    table = ax2.table(cellText=table_data, loc='center', cellLoc='left', colWidths=[0.2, 0.75])
    table.auto_set_font_size(False)
    table.set_fontsize(6)
    table.scale(1.0, 1.2)
    plt.title("Entry List", fontsize=10, pad=5)
    plt.subplots_adjust(left=0.01, right=0.99, top=0.95, bottom=0.01)
    pdf.savefig(fig2, bbox_inches='tight')
    plt.close(fig2)

    for block in blocks:
        block_df = df[df['Block'] == block].copy()

        # Block layout
        fig, ax = plt.subplots(figsize=a5_inches)
        for _, row in block_df.iterrows():
            ax.add_patch(patches.Rectangle((row['X_start'], row['Y_start']),
                                           cell_width, cell_height,
                                           facecolor="#d9d9d9", edgecolor='black', linewidth=0.3))
            ax.text(row['X'], row['Y'], row['Label'], ha='center', va='center', fontsize=4, rotation=90)
        ax.set_xlim(block_df['X_start'].min() - 1, block_df['X_stop'].max() + 1)
        ax.set_ylim(block_df['Y_start'].min() - 1, block_df['Y_stop'].max() + 1)
        ax.set_aspect('equal')
        ax.axis('off')
        plt.title(f"Block {block} Layout", fontsize=10, pad=5)
        plt.subplots_adjust(left=0.01, right=0.99, top=0.95, bottom=0.01)
        pdf.savefig(fig, bbox_inches='tight')
        plt.close(fig)

        # Block coordinate table
        fig_table, ax_table = plt.subplots(figsize=a5_inches)
        ax_table.axis('off')
        coords_data = block_df[['Row', 'Col', 'Label', 'X_start', 'Y_start', 'X_stop', 'Y_stop']]
        coords_data = coords_data.sort_values(by=['Row', 'Col']).round(2)
        headers = ["Row", "Col", "Label", "X_start", "Y_start", "X_stop", "Y_stop"]
        table_vals = [headers] + coords_data.values.tolist()
        table = ax_table.table(cellText=table_vals, loc='center', cellLoc='left',
                               colWidths=[0.08, 0.08, 0.3, 0.14, 0.14, 0.14, 0.14])
        table.auto_set_font_size(False)
        table.set_fontsize(5.5)
        table.scale(1.0, 1.3)
        plt.title(f"Block {block} Plot Coordinates", fontsize=10, pad=5)
        plt.subplots_adjust(left=0.01, right=0.99, top=0.95, bottom=0.01)
        pdf.savefig(fig_table, bbox_inches='tight')
        plt.close(fig_table)

    pdf.close()

    with open(pdf_path, "rb") as f:
        st.download_button("📥 Download Fieldbook PDF", f.read(), "FieldBook_A5_GPSAligned.pdf", "application/pdf")
