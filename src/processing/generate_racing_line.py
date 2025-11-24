"""Generate track centerline from all car trajectories."""

import numpy as np

# Debug flag for racing line diagnostics
DEBUG_RACING_LINE = False


def filter_main_track_points(points: np.ndarray, speed_threshold: float = 8.0,
                              max_deviation: float = 20.0) -> np.ndarray:
    """
    Filter out pit-lane points from the dataset.

    Uses multiple rules to identify and remove pit-lane data:
    1. Speed threshold - remove slow points (pit activity)
    2. Median deviation - remove points far from local cluster center
    3. Automatic pit-lane window detection

    Args:
        points: Nx4 array of [norm_lapdist, x, y, speed]
        speed_threshold: Minimum speed in m/s (default 8.0)
        max_deviation: Maximum distance from bin median in meters (default 20.0)

    Returns:
        Filtered points array (M x 4) with pit points removed
    """
    if len(points) == 0:
        return points

    n_original = len(points)

    # Rule 1: Filter by speed threshold
    speed_mask = points[:, 3] >= speed_threshold
    filtered = points[speed_mask]
    n_after_speed = len(filtered)

    if DEBUG_RACING_LINE:
        print(f"  Speed filter: {n_original - n_after_speed} points removed (speed < {speed_threshold} m/s)")

    if len(filtered) == 0:
        print("Warning: All points removed by speed filter")
        return filtered

    # Rule 2: Per-bin median deviation filter
    # Group points into coarse bins and remove outliers in each bin
    n_coarse_bins = 100
    bins = np.linspace(0, 1, n_coarse_bins + 1)
    bin_indices = np.digitize(filtered[:, 0], bins) - 1
    bin_indices = np.clip(bin_indices, 0, n_coarse_bins - 1)

    keep_mask = np.ones(len(filtered), dtype=bool)
    bins_with_clusters = 0

    for i in range(n_coarse_bins):
        bin_mask = bin_indices == i
        if bin_mask.sum() < 3:
            continue

        bin_points = filtered[bin_mask]
        bin_x = bin_points[:, 1]
        bin_y = bin_points[:, 2]

        # Compute median center
        median_x = np.median(bin_x)
        median_y = np.median(bin_y)

        # Compute distance from median
        distances = np.sqrt((bin_x - median_x)**2 + (bin_y - median_y)**2)

        # Check if this bin has multiple spatial clusters (potential pit lane)
        if distances.max() > max_deviation:
            bins_with_clusters += 1

        # Remove points too far from median
        bin_keep = distances <= max_deviation

        # Update global mask
        bin_global_indices = np.where(bin_mask)[0]
        for j, global_idx in enumerate(bin_global_indices):
            if not bin_keep[j]:
                keep_mask[global_idx] = False

    filtered = filtered[keep_mask]
    n_after_deviation = len(filtered)

    if DEBUG_RACING_LINE:
        print(f"  Deviation filter: {n_after_speed - n_after_deviation} points removed (> {max_deviation}m from median)")
        print(f"  Bins with potential clusters: {bins_with_clusters}")

    if len(filtered) == 0:
        print("Warning: All points removed by deviation filter")
        return filtered

    # Rule 3: Detect and remove pit-lane lapdist windows
    # Find regions where there's systematic low speed AND spatial spread
    # This catches entire pit entry/exit zones

    # Re-bin to detect pit windows
    n_window_bins = 50
    window_bins = np.linspace(0, 1, n_window_bins + 1)
    window_indices = np.digitize(filtered[:, 0], window_bins) - 1
    window_indices = np.clip(window_indices, 0, n_window_bins - 1)

    # For each window, check if it looks like pit lane
    pit_windows = []
    for i in range(n_window_bins):
        window_mask = window_indices == i
        if window_mask.sum() < 10:
            continue

        window_points = filtered[window_mask]
        window_speeds = window_points[:, 3]
        window_x = window_points[:, 1]
        window_y = window_points[:, 2]

        # Check for characteristics of pit lane:
        # - Low average speed
        # - High spatial variance (bimodal distribution)
        avg_speed = np.mean(window_speeds)
        spatial_std = np.sqrt(np.var(window_x) + np.var(window_y))

        # Pit lane detection: low speed with high spatial spread
        # Thresholds tuned for typical racing data
        if avg_speed < 15.0 and spatial_std > 30.0:
            pit_windows.append(i)

    # Remove points in detected pit windows
    if pit_windows:
        pit_mask = np.zeros(len(filtered), dtype=bool)
        for pit_idx in pit_windows:
            pit_mask |= (window_indices == pit_idx)

        filtered = filtered[~pit_mask]
        n_after_pit = len(filtered)

        if DEBUG_RACING_LINE:
            print(f"  Pit window filter: {n_after_deviation - n_after_pit} points removed")
            print(f"  Detected pit windows: {pit_windows}")

    # Final summary
    total_removed = n_original - len(filtered)
    if DEBUG_RACING_LINE:
        print(f"  Total filtered: {total_removed} points removed ({100*total_removed/n_original:.1f}%)")
        print(f"  Remaining: {len(filtered)} points")

    return filtered


def compute_racing_line(all_trajectories: dict, n_points: int = 1500) -> np.ndarray:
    """
    Compute racing line from all car trajectories.

    Uses a simpler approach: normalize all lapdist values to [0, 1] for each car,
    then bin by normalized lapdist and take median x, y for each bin.

    Includes pit-lane filtering to remove contaminated data.

    Args:
        all_trajectories: dict of car_id -> np.ndarray(N, 4) [x, y, speed, lapdist]
        n_points: number of points in output racing line

    Returns:
        racing_line: np.ndarray(n_points, 2) [x, y]
    """
    # Collect all points with normalized lapdist and speed
    all_points = []  # (norm_lapdist, x, y, speed)

    for car_id, traj in all_trajectories.items():
        lapdist = traj[:, 3]
        x = traj[:, 0]
        y = traj[:, 1]
        speed = traj[:, 2]

        # Get track length from this car's data
        ld_min = lapdist.min()
        ld_max = lapdist.max()
        ld_range = ld_max - ld_min

        if ld_range < 100:  # Skip if insufficient range
            continue

        # Normalize lapdist to [0, 1]
        norm_ld = (lapdist - ld_min) / ld_range

        # Add points with speed for filtering
        for i in range(len(traj)):
            all_points.append((norm_ld[i], x[i], y[i], speed[i]))

    if len(all_points) == 0:
        print("Warning: No valid points for racing line computation")
        return np.zeros((n_points, 2))

    # Convert to array
    all_points = np.array(all_points)
    n_raw = len(all_points)

    if DEBUG_RACING_LINE:
        print(f"Raw points collected: {n_raw}")

    # Filter out pit-lane points
    all_points = filter_main_track_points(all_points)
    n_filtered = len(all_points)

    if len(all_points) == 0:
        print("Warning: All points filtered out - cannot compute racing line")
        return np.zeros((n_points, 2))

    # Bin points by normalized lapdist
    bins = np.linspace(0, 1, n_points + 1)
    bin_indices = np.digitize(all_points[:, 0], bins) - 1
    bin_indices = np.clip(bin_indices, 0, n_points - 1)

    # Initialize with NaN to detect empty bins
    racing_line = np.full((n_points, 2), np.nan, dtype=float)

    # Fill bins that have data
    for i in range(n_points):
        mask = bin_indices == i
        if mask.sum() > 0:
            bin_x = all_points[mask, 1]
            bin_y = all_points[mask, 2]
            racing_line[i, 0] = np.median(bin_x)
            racing_line[i, 1] = np.median(bin_y)

    # Second pass: detect and remove points involved in large jumps
    max_jump = 15.0  # meters

    # Calculate all consecutive distances
    distances = np.zeros(n_points)
    for i in range(n_points):
        if np.isnan(racing_line[i, 0]):
            continue
        next_idx = (i + 1) % n_points
        if np.isnan(racing_line[next_idx, 0]):
            continue
        dx = racing_line[next_idx, 0] - racing_line[i, 0]
        dy = racing_line[next_idx, 1] - racing_line[i, 1]
        distances[i] = np.sqrt(dx**2 + dy**2)

    # Mark all points involved in large jumps for removal
    jump_outliers = 0
    for i in range(n_points):
        if np.isnan(racing_line[i, 0]):
            continue

        prev_idx = (i - 1) % n_points

        if distances[prev_idx] > max_jump or distances[i] > max_jump:
            racing_line[i] = np.nan
            jump_outliers += 1

    # Count valid bins
    valid_mask = ~np.isnan(racing_line[:, 0])
    n_valid = valid_mask.sum()

    if n_valid == 0:
        raise ValueError("No valid points in any bin - cannot compute racing line")

    # Interpolate empty bins using 1D interpolation
    idx = np.arange(n_points)
    valid_x_mask = ~np.isnan(racing_line[:, 0])
    valid_y_mask = ~np.isnan(racing_line[:, 1])

    racing_line[:, 0] = np.interp(idx, idx[valid_x_mask], racing_line[valid_x_mask, 0])
    racing_line[:, 1] = np.interp(idx, idx[valid_y_mask], racing_line[valid_y_mask, 1])

    # Third pass: Apply Gaussian smoothing for smooth track
    from scipy.ndimage import gaussian_filter1d

    racing_line[:, 0] = gaussian_filter1d(racing_line[:, 0], sigma=2, mode='wrap')
    racing_line[:, 1] = gaussian_filter1d(racing_line[:, 1], sigma=2, mode='wrap')

    # Check final loop closure distance
    loop_dist = np.sqrt((racing_line[0, 0] - racing_line[-1, 0])**2 +
                        (racing_line[0, 1] - racing_line[-1, 1])**2)
    print(f"  Final loop closure distance: {loop_dist:.1f}m (after smoothing)")

    n_interpolated = n_points - n_valid
    n_pit_removed = n_raw - n_filtered
    print(f"Computed racing line from {n_raw} raw points across {len(all_trajectories)} cars")
    print(f"  Pit-lane filter removed: {n_pit_removed} points ({100*n_pit_removed/n_raw:.1f}%)")
    print(f"  {n_valid} bins with data, {n_interpolated} bins interpolated")
    print(f"  {jump_outliers} jump outliers removed")

    return racing_line
