"""Density map rendering for track visualization.

Uses 2D histogram of all trajectory points to create a density map
that naturally shows the track shape without polyline artifacts.
"""

import numpy as np
import dearpygui.dearpygui as dpg

try:
    from scipy.ndimage import gaussian_filter
    HAS_SCIPY = True
except ImportError:
    HAS_SCIPY = False
    import math


def _gaussian_kernel_1d(sigma, size=None):
    """Create 1D Gaussian kernel for manual convolution."""
    if size is None:
        size = int(6 * sigma + 1)
        if size % 2 == 0:
            size += 1

    x = np.arange(size) - size // 2
    kernel = np.exp(-x**2 / (2 * sigma**2))
    return kernel / kernel.sum()


def _gaussian_blur_manual(image, sigma):
    """Apply Gaussian blur using separable convolution (fallback if no scipy)."""
    kernel = _gaussian_kernel_1d(sigma)

    # Horizontal pass
    result = np.zeros_like(image, dtype=float)
    pad = len(kernel) // 2
    padded = np.pad(image, pad, mode='reflect')

    for i in range(image.shape[0]):
        for j in range(image.shape[1]):
            result[i, j] = np.sum(padded[i + pad, j:j + len(kernel)] * kernel)

    # Vertical pass
    padded = np.pad(result, pad, mode='reflect')
    final = np.zeros_like(image, dtype=float)

    for i in range(image.shape[0]):
        for j in range(image.shape[1]):
            final[i, j] = np.sum(padded[i:i + len(kernel), j + pad] * kernel)

    return final


def build_density_map(world, bins=400, sigma=2.0):
    """Build density map from all trajectory points.

    Args:
        world: WorldModel instance with trajectories and bounds
        bins: Number of histogram bins per dimension
        sigma: Gaussian smoothing sigma

    Returns:
        Tuple of (density_image, bounds) where:
        - density_image: uint8 numpy array (bins x bins)
        - bounds: dict with x_min, x_max, y_min, y_max
    """
    # Collect all X,Y points from all trajectories
    all_points = []

    for car_id, traj in world.trajectories.items():
        # Trajectory columns: [x, y, speed, lapdist, ...]
        x = traj[:, 0]
        y = traj[:, 1]
        points = np.column_stack([x, y])
        all_points.append(points)

    if len(all_points) == 0:
        print("Warning: No trajectory points for density map")
        return None, None

    # Combine all points
    all_points = np.vstack(all_points)
    print(f"Building density map from {len(all_points):,} points")

    # Get world bounds
    bounds = world.bounds
    x_min, x_max = bounds['x_min'], bounds['x_max']
    y_min, y_max = bounds['y_min'], bounds['y_max']

    # Add small margin
    margin = 10.0
    x_min -= margin
    x_max += margin
    y_min -= margin
    y_max += margin

    # Create 2D histogram
    histogram, x_edges, y_edges = np.histogram2d(
        all_points[:, 0], all_points[:, 1],
        bins=bins,
        range=[[x_min, x_max], [y_min, y_max]]
    )

    # Transpose and flip for correct screen orientation
    # histogram2d returns [x, y] but we want [row, col] with y increasing downward for screen
    histogram = histogram.T
    histogram = np.flipud(histogram)  # Flip vertically for screen coordinates

    # Apply Gaussian smoothing
    if HAS_SCIPY:
        smoothed = gaussian_filter(histogram, sigma=sigma)
    else:
        smoothed = _gaussian_blur_manual(histogram, sigma)

    # Normalize to 0-255
    if smoothed.max() > 0:
        normalized = (smoothed / smoothed.max() * 255).astype(np.uint8)
    else:
        normalized = np.zeros((bins, bins), dtype=np.uint8)

    # Store actual bounds used
    actual_bounds = {
        'x_min': x_min,
        'x_max': x_max,
        'y_min': y_min,
        'y_max': y_max
    }

    print(f"Density map created: {normalized.shape}, range [{normalized.min()}, {normalized.max()}]")

    return normalized, actual_bounds


def density_map_to_texture(image, tag="density_texture"):
    """Convert density map to DearPyGUI texture.

    Args:
        image: 2D uint8 numpy array (grayscale density)
        tag: Tag for the texture

    Returns:
        Texture tag string
    """
    height, width = image.shape

    # Convert grayscale to RGBA
    # Map intensity to color and alpha
    # Low intensity = transparent, high intensity = visible gray
    rgba = np.zeros((height, width, 4), dtype=np.float32)

    # Normalize to 0-1 for DearPyGUI
    normalized = image.astype(np.float32) / 255.0

    # Color channels (gray)
    rgba[:, :, 0] = normalized * 0.4  # R - subtle gray
    rgba[:, :, 1] = normalized * 0.4  # G
    rgba[:, :, 2] = normalized * 0.45  # B - slight blue tint

    # Alpha channel - more transparent for low density
    rgba[:, :, 3] = np.clip(normalized * 1.5, 0, 1)

    # Flatten for DearPyGUI
    flat_data = rgba.flatten().tolist()

    # Create texture in DearPyGUI
    with dpg.texture_registry():
        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)

        dpg.add_dynamic_texture(
            width=width,
            height=height,
            default_value=flat_data,
            tag=tag
        )

    return tag
