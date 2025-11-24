"""Generate high-resolution per-car racing lines (30,000 points) from trajectory data."""

import numpy as np
from scipy.ndimage import gaussian_filter1d


def segment_laps_by_lapdist(lapdist: np.ndarray, reset_threshold: float = -100.0):
    """Segment trajectory into individual laps based on lapdist resets.

    Args:
        lapdist: Array of lap distance values
        reset_threshold: Threshold for detecting lap boundary (default -100m)

    Returns:
        List of (start_idx, end_idx) tuples for each lap
    """
    # Find where lapdist drops significantly (lap reset)
    diff = np.diff(lapdist)
    reset_indices = np.where(diff < reset_threshold)[0] + 1

    # Build lap boundaries
    boundaries = np.concatenate(([0], reset_indices, [len(lapdist)]))

    laps = []
    for i in range(len(boundaries) - 1):
        start = boundaries[i]
        end = boundaries[i + 1]
        # Only include laps with sufficient data points
        if end - start > 100:
            laps.append((start, end))

    return laps


def interpolate_lap_to_grid(lap_xy: np.ndarray, lap_lapdist: np.ndarray, n_points: int = 30000):
    """Interpolate a single lap onto a uniform distance grid.

    Args:
        lap_xy: Array of shape (N, 2) with x, y coordinates
        lap_lapdist: Array of shape (N,) with lap distance values
        n_points: Number of points in output grid

    Returns:
        Array of shape (n_points, 2) with interpolated x, y coordinates
    """
    # Get lap distance range
    min_dist = np.min(lap_lapdist)
    max_dist = np.max(lap_lapdist)

    if max_dist - min_dist < 100:  # Lap too short
        return None

    # Create uniform distance grid
    uniform_dist = np.linspace(min_dist, max_dist, n_points)

    # Interpolate x and y onto uniform grid
    x_interp = np.interp(uniform_dist, lap_lapdist, lap_xy[:, 0])
    y_interp = np.interp(uniform_dist, lap_lapdist, lap_xy[:, 1])

    return np.column_stack([x_interp, y_interp])


def compute_per_car_racing_line(trajectory: np.ndarray, n_points: int = 30000, min_laps: int = 3):
    """Generate high-resolution per-car racing line from trajectory data.

    Args:
        trajectory: Array of shape (N, 8) with columns:
                    [x, y, speed, lapdist, brake, gear, steering_deg, heading_rad]
        n_points: Number of points in output racing line
        min_laps: Minimum number of valid laps required

    Returns:
        Tuple of (racing_line, lap_length) where:
        - racing_line: Array of shape (n_points, 2) with x, y coordinates
        - lap_length: Single lap distance in meters
    """
    # Extract x, y, lapdist
    x = trajectory[:, 0]
    y = trajectory[:, 1]
    lapdist = trajectory[:, 3]

    xy = np.column_stack([x, y])

    # Segment into laps
    lap_boundaries = segment_laps_by_lapdist(lapdist)

    if len(lap_boundaries) < min_laps:
        raise ValueError(f"Insufficient laps: found {len(lap_boundaries)}, need {min_laps}")

    # Interpolate each lap to high-resolution grid
    interpolated_laps = []
    lap_lengths = []

    for start, end in lap_boundaries:
        lap_xy = xy[start:end]
        lap_lapdist = lapdist[start:end]

        # Skip if lap distance is not monotonically increasing (data issue)
        if not np.all(np.diff(lap_lapdist) >= 0):
            continue

        interp_lap = interpolate_lap_to_grid(lap_xy, lap_lapdist, n_points)

        if interp_lap is not None:
            interpolated_laps.append(interp_lap)
            lap_lengths.append(np.max(lap_lapdist) - np.min(lap_lapdist))

    if len(interpolated_laps) < min_laps:
        raise ValueError(f"Insufficient valid laps: found {len(interpolated_laps)}, need {min_laps}")

    # Stack laps and compute median
    stacked_laps = np.stack(interpolated_laps, axis=0)  # Shape: (num_laps, n_points, 2)
    racing_line = np.median(stacked_laps, axis=0)  # Shape: (n_points, 2)

    # Compute median lap length
    median_lap_length = np.median(lap_lengths)

    # Optional: Light Gaussian smoothing
    racing_line[:, 0] = gaussian_filter1d(racing_line[:, 0], sigma=3, mode='wrap')
    racing_line[:, 1] = gaussian_filter1d(racing_line[:, 1], sigma=3, mode='wrap')

    print(f"  Generated racing line from {len(interpolated_laps)} laps, lap length: {median_lap_length:.1f}m")

    return racing_line, median_lap_length
