1) refl_conversion.py: This assumes you have a panel image inside your tif image. You need to draw a polygon inside the panel and the code will convert the image to reflectance and also give you the factors in case you need to apply this on any other image. Refl = radiance/correction factor.

  This takes # Example usage
  file_path (path to your single image)
  output_folder (path to output folder, not file name)
  clip_size = (71, 103)  # Update this to your desired clipping dimensions according to GSD and tree/row spacing
  refl_factor = 0.5 #(using a 50% panel here)

2) refl_factors_as_input_folder.ipynb: This takes refl factors as input and works on multiple images in a folder. This will work for the biochemical parameters/structure simulation when all atmospheric conditions and solar sonditions are same. The factors can be taken from refl_conversion.py in case you ahve simulated one image only with panel, or you can take the values from QGIS as well. If QGIS, you need to multiple the panel values for each band with (1/refl_factor), so 1/0.5 if we had a 50% refl panel in the image
