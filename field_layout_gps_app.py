
import streamlit as st
import pandas as pd
import re

# Load pre-generated CSV
@st.cache_data
def load_data():
    return pd.read_csv("combined_field_designs_1_to_4.csv")

def gps_to_feet(gps_str):
    match = re.match(r'^(\d+)[\s\-:]+(\d+)[\s\-:]+(\d+)$', gps_str.strip())
    if not match:
        return None
    degrees, minutes, seconds = map(int, match.groups())
    decimal_deg = degrees + minutes / 60 + seconds / 3600
    feet = decimal_deg * 364000
    return feet

def update_coordinates(df, gps_y_feet):
    min_y_start = df[df['Block'] == 'T0']['Y_start'].min()
    offset = gps_y_feet - min_y_start
    df['Y_start'] += offset
    df['Y_stop'] += offset
    df['Y'] += offset
    return df.round(2)

st.set_page_config(page_title="Field Layout GPS Aligner", layout="centered")
st.title("🌱 Field Layout GPS Coordinate Aligner")

df = load_data()
# Constants from the original layout
cell_height = 10  # or whatever your planted row length was
cell_width = 3.3  # estimate if unknown

# Recalculate coordinates
df['X_start'] = df['X'] - cell_width / 2
df['X_stop'] = df['X'] + cell_width / 2
df['Y_start'] = df['Y'] - cell_height / 2
df['Y_stop'] = df['Y'] + cell_height / 2

gps_input = st.text_input("Enter GPS for T0 lower-left corner (format: XX-YY-ZZ)", "40-06-54")

if st.button("Update Coordinates"):
    gps_y = gps_to_feet(gps_input)
    if gps_y is None:
        st.error("Invalid GPS format. Use XX-YY-ZZ.")
    else:
        updated_df = update_coordinates(df.copy(), gps_y)
        st.success("Coordinates updated.")
        st.dataframe(updated_df.head(10), use_container_width=True)
        csv = updated_df.to_csv(index=False).encode('utf-8')
        st.download_button("Download Updated CSV", csv, "updated_field_design.csv", "text/csv")
