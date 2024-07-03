import os
import numpy as np
import matplotlib.pyplot as plt
import rasterio
from rasterio.mask import mask
from shapely.geometry import Polygon, mapping
import matplotlib.patches as patches

class PolygonDrawer:
    def __init__(self, ax, snap_distance=5):
        self.ax = ax
        self.canvas = ax.figure.canvas
        self.poly = None
        self.verts = []
        self.cid = self.canvas.mpl_connect('button_press_event', self.on_click)
        self.cid_key = self.canvas.mpl_connect('key_press_event', self.on_key)
        self.polygon_complete = False
        self.snap_distance = snap_distance

    def on_click(self, event):
        if event.inaxes != self.ax:
            return
        if len(self.verts) > 0 and np.sqrt((event.xdata - self.verts[0][0])**2 + (event.ydata - self.verts[0][1])**2) < self.snap_distance:
            # Snap to the starting point
            self.verts.append(self.verts[0])
            self.poly.set_closed(True)
            self.polygon_complete = True
            self.canvas.draw_idle()
            self.canvas.mpl_disconnect(self.cid)
            self.canvas.mpl_disconnect(self.cid_key)
            plt.close(self.canvas.figure)
            return
        self.verts.append((event.xdata, event.ydata))
        if self.poly is None:
            self.poly = patches.Polygon(self.verts, closed=False, edgecolor='r')
            self.ax.add_patch(self.poly)
        else:
            self.poly.set_xy(self.verts)
        self.canvas.draw_idle()

    def on_key(self, event):
        if event.key == 'enter':
            self.poly.set_closed(True)
            self.polygon_complete = True
            self.canvas.draw_idle()
            self.canvas.mpl_disconnect(self.cid)
            self.canvas.mpl_disconnect(self.cid_key)
            plt.close(self.canvas.figure)

    def get_polygon(self):
        return Polygon(self.verts)

def draw_polygon_on_image(file_path):
    with rasterio.open(file_path) as src:
        data = src.read(1).astype(np.float32)  # Read the first band as float32
        data_normalized = (data - np.min(data)) / (np.max(data) - np.min(data))  # Normalize only for display

        fig, ax = plt.subplots()
        ax.imshow(data_normalized, cmap='gray', extent=(0, data.shape[1], data.shape[0], 0))

        pd = PolygonDrawer(ax)
        plt.show(block=True)

        return pd

def extract_polygon_values(file_path, polygon):
    with rasterio.open(file_path) as src:
        poly_geom = [mapping(polygon)]
        out_image, out_transform = mask(src, poly_geom, crop=True)
        print("Masked Image Shape:", out_image.shape)  # Debugging: Print shape of the masked image

        # Calculate mean of the highest 10 values for each band within the polygon
        means = []
        for i, band in enumerate(out_image):
            band_values = band[band != 0]  # Exclude zero values
            if band_values.size > 0:
                highest_values = np.sort(band_values)[-10:]  # Get the highest 10 values
                mean_value = highest_values.mean()
                refl_factors = mean_value * (1/refl_factor)
            else:
                mean_value = 0  # Avoid empty slices
            means.append(mean_value)
            print(f"Mean Value of Highest 10 Values for Band {i + 1}: {refl_factors}")  # Debugging: Print mean values for each band

        return np.array(means, dtype=np.float32)

def radiometric_correction(data, correction_factors):
    corrected_data = data.copy()
    for i in range(data.shape[0]):
        corrected_data[i] /= (correction_factors[i] * (1/refl_factor))
    return corrected_data

def save_corrected_raster(file_path, output_path, corrected_data):
    with rasterio.open(file_path) as src:
        with rasterio.open(
            output_path,
            'w',
            driver='GTiff',
            count=src.count,
            dtype='float32',
            width=src.width,
            height=src.height,
            transform=src.transform if src.transform != rasterio.Affine.identity() else None
        ) as dst:
            dst.write(corrected_data.astype(np.float32))

def save_clipped_raster(file_path, output_path, corrected_data, grid_size):
    with rasterio.open(file_path) as src:
        # Calculate the window position (centered on the image)
        start_x = (src.width - grid_size[0]) // 2
        start_y = (src.height - grid_size[1]) // 2
        window = rasterio.windows.Window(start_x, start_y, grid_size[0], grid_size[1])
        
        with rasterio.open(
            output_path,
            'w',
            driver='GTiff',
            count=src.count,
            dtype='float32',
            width=grid_size[0],
            height=grid_size[1],
            transform=rasterio.windows.transform(window, src.transform) if src.transform != rasterio.Affine.identity() else None
        ) as dst:
            clipped_data = corrected_data[:, start_y:start_y + grid_size[1], start_x:start_x + grid_size[0]]
            dst.write(clipped_data.astype(np.float32))

def process_file(file_path, output_folder, clip_size=(1600, 1300)):
    os.makedirs(output_folder, exist_ok=True)
    
    # Draw polygon and get the average values within the polygon
    pd = draw_polygon_on_image(file_path)
    polygon = pd.get_polygon()
    
    if polygon and pd.polygon_complete:
        correction_factors = extract_polygon_values(file_path, polygon)
        print("Correction factors based on polygon:", correction_factors * (1/refl_factor))
        
        with rasterio.open(file_path) as src:
            data = src.read().astype(np.float32)
        
        # Apply radiometric correction
        corrected_data = radiometric_correction(data, correction_factors)
        
        # Save the corrected full image
        corrected_output_file_path = os.path.join(output_folder, 'corrected_image.tif')
        save_corrected_raster(file_path, corrected_output_file_path, corrected_data)
        
        # Save the clipped corrected image
        clipped_output_file_path = os.path.join(output_folder, 'clipped_image.tif')
        save_clipped_raster(file_path, clipped_output_file_path, corrected_data, clip_size)
    else:
        print("No polygon was drawn or polygon drawing was not completed.")

def process_all_files(input_folder, output_base_folder, clip_size=(1600, 1300)):
    for file_name in os.listdir(input_folder):
        if file_name.endswith('.tif'):
            file_path = os.path.join(input_folder, file_name)
            output_folder = os.path.join(output_base_folder, os.path.splitext(file_name)[0])
            process_file(file_path, output_folder, clip_size)

# Example usage
input_folder =  '/home/momty/HELIOS_new_manuscript_output/04_soil/images_original/'   # Update this to your input folder
output_base_folder = '/home/momty/HELIOS_new_manuscript_output/04_soil/images_corrected/'   # Update this to your output base folder
clip_size = (71, 103)  # Update this to your desired clipping dimensions
refl_factor = 0.5  # Using a 50% panel here

process_all_files(input_folder, output_base_folder, clip_size)
