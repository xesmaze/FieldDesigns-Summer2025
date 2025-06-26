import numpy as np
import pandas as pd
from scipy.spatial.distance import cdist
import re

# === Configuration ===
field_width = 160
field_height = 270
n_samples = 100
min_distance = 15  # Minimum distance between points in feet
gps_input = "40-06-54"  # GPS anchor at bottom-left corner of T0

# === GPS Constants ===
origin_lat = 40 + 6/60 + 54/3600       # 40°06'54" N
origin_lon = -(88 + 14/60 + 50/3600)   # 88°14'50" W
origin_lat_ft = origin_lat * 364000   # feet from equator
origin_lon_ft = origin_lon * 288200   # feet from prime meridian (approximate)
origin_lon_adjusted_ft = origin_lon_ft + 160  # Adjust 160 ft east for left edge of field

# === GPS Helpers ===
def feet_to_gps_dms(feet, feet_per_deg):
    decimal_degrees = feet / feet_per_deg
    degrees = int(decimal_degrees)
    remainder = (decimal_degrees - degrees) * 60
    minutes = int(remainder)
    seconds = (remainder - minutes) * 60
    return f"{abs(degrees):02d}-{minutes:02d}-{seconds:05.2f}"

def feet_to_decimal_degrees(offset_ft, feet_per_deg):
    return offset_ft / feet_per_deg

# === Convert GPS anchor to feet ===
def gps_to_feet(gps_str):
    match = re.match(r'^(\d+)[\s\-:]+(\d+)[\s\-:]+(\d+(\.\d+)?)$', gps_str.strip())
    if not match:
        raise ValueError("GPS input must be in 'xx-yy-zz' format")
    degrees, minutes, seconds = map(float, match.groups()[:3])
    decimal_deg = degrees + minutes / 60 + seconds / 3600
    return decimal_deg * 364000

# === Rejection Sampling ===
np.random.seed(None)
accepted_points = []
attempts = 0
max_attempts = 10000

while len(accepted_points) < n_samples and attempts < max_attempts:
    x = np.random.uniform(0, field_width)
    y = np.random.uniform(0, field_height)
    point = np.array([[x, y]])
    if not accepted_points:
        accepted_points.append(point[0])
    else:
        distances = cdist(point, np.array(accepted_points))
        if distances.min() >= min_distance:
            accepted_points.append(point[0])
    attempts += 1

# === Construct DataFrame ===
points = np.array(accepted_points)
df = pd.DataFrame({
    "SampleID": [f"S{i+1:03}" for i in range(len(points))],
    "X_ft": points[:, 0].round(2),
    "Y_ft": points[:, 1].round(2)
})

# === Shift to GPS anchor Y
gps_y_feet = gps_to_feet(gps_input)
df["Y_ft"] += gps_y_feet

# === GPS Conversion
df["GPS_Latitude"] = df["Y_ft"].apply(lambda y: feet_to_gps_dms(origin_lat + (y - origin_lat_ft) / 364000, 1))
df["GPS_Longitude"] = df["X_ft"].apply(lambda x: feet_to_gps_dms(origin_lon + ((x + 160) - origin_lon_adjusted_ft) / 288200, 1))
df["Decimal_Latitude"] = (origin_lat + feet_to_decimal_degrees(df["Y_ft"] - origin_lat_ft, 364000)).round(6)
df["Decimal_Longitude"] = (origin_lon + feet_to_decimal_degrees(df["X_ft"] + 160 - origin_lon_adjusted_ft, 288200)).round(6)

# === Save CSV
df.to_csv("optimized_soil_samples_gps_aligned_dms_decimal.csv", index=False)
print("✅ Saved: optimized_soil_samples_gps_aligned_dms_decimal.csv")

# Create a map of the final sampled positions with GPS alignment for appending to script workflow
import matplotlib.pyplot as plt
optimized_shifted_samples = df

fig, ax = plt.subplots(figsize=(8, 12))
ax.add_patch(plt.Rectangle((0, optimized_shifted_samples['Y_ft'].min()),
                           field_width, field_height,
                           edgecolor='black', facecolor='lightgrey', lw=1))

ax.scatter(optimized_shifted_samples['X_ft'], optimized_shifted_samples['Y_ft'],
           c='red', s=30, edgecolors='black', label='Soil Samples')

for i, row in optimized_shifted_samples.sample(10, random_state=7).iterrows():
    ax.text(row['X_ft'], row['Y_ft'], row['SampleID'], fontsize=6, ha='left', va='bottom')

ax.set_xlim(0, 160)
ax.set_ylim(optimized_shifted_samples['Y_ft'].min(), optimized_shifted_samples['Y_ft'].min() + 270)
ax.set_aspect('auto')
ax.set_title("Optimized Soil Sampling Map (GPS-Aligned)")
ax.set_xlabel("X (ft)")
ax.set_ylabel("Y (ft)")
ax.legend()
plt.grid(True)
plt.tight_layout()

# Save image to append to workflow
map_path = "soil_sampling_map_gps_aligned.png"
plt.savefig(map_path, dpi=150)
plt.close()

map_path


# Plot settings
fig1, ax = plt.subplots(figsize=(8, 12))
ax.add_patch(plt.Rectangle((0, optimized_shifted_samples['Y_ft'].min()),
                           field_width, field_height,
                           edgecolor='black', facecolor='lightgrey', lw=1))

# Plot points
ax.scatter(optimized_shifted_samples['X_ft'], optimized_shifted_samples['Y_ft'],
           c='red', s=30, edgecolors='black', label='Soil Samples')

# Annotate with GPS coordinates (decimal degrees)
for i, row in optimized_shifted_samples.iterrows():
    label = f"{row['Decimal_Latitude']:.6f}, {row['Decimal_Longitude']:.6f}"
    ax.text(row['X_ft'], row['Y_ft'], label, fontsize=5, ha='left', va='bottom', rotation=45)

ax.set_xlim(0, 160)
ax.set_ylim(optimized_shifted_samples['Y_ft'].min(), optimized_shifted_samples['Y_ft'].min() + 270)
ax.set_aspect('auto')
ax.set_title("Optimized Soil Sampling Map with GPS Coordinates")
ax.set_xlabel("X (ft)")
ax.set_ylabel("Y (ft)")
plt.grid(True)
plt.tight_layout()

# Save image
map_with_coords_path = "soil_sampling_map_with_gps_labels.png"
plt.savefig(map_with_coords_path, dpi=150)
plt.close()

map_with_coords_path