"""Interpolate trajectories to uniform 10ms grid (100 Hz)."""

import numpy as np
import pandas as pd
from scipy.interpolate import interp1d


def interpolate_trajectory(df: pd.DataFrame, dt_ms: int = 10) -> tuple:
    """Interpolate to uniform 10ms grid.

    Returns:
        trajectory: np.ndarray shape (N, 11) = [x, y, speed, lapdist, brake_front, brake_rear, gear, steering_deg, heading_rad, accel_norm, lap]
        time_grid: np.ndarray of time values in seconds
    """
    # Remove duplicate timestamps (PATCH 4)
    df = df.drop_duplicates(subset='rel_time')
    df = df.sort_values('rel_time')

    if len(df) < 2:
        return None, None

    # Build uniform timeline
    t_original = df['rel_time'].values
    dt_s = dt_ms / 1000.0  # 10ms in seconds
    global_t = np.arange(0, t_original[-1], dt_s)

    if len(global_t) < 2:
        return None, None

    # Interpolate each signal
    x_interp = interp1d(t_original, df['x'].values, kind='linear',
                        bounds_error=False, fill_value='extrapolate')(global_t)
    y_interp = interp1d(t_original, df['y'].values, kind='linear',
                        bounds_error=False, fill_value='extrapolate')(global_t)
    speed_interp = interp1d(t_original, df['speed'].values, kind='linear',
                            bounds_error=False, fill_value='extrapolate')(global_t)
    lapdist_interp = interp1d(t_original, df['lapdist'].values, kind='linear',
                              bounds_error=False, fill_value='extrapolate')(global_t)

    # LAPDIST REPAIR (PHASE 1): Fix corrupted lapdist values
    # Step 1: Detect true lap resets
    # A lap reset is when lapdist drops AND returns to near-zero (< 500m)
    # This handles multi-frame resets where drops happen gradually
    reset_indices = []
    for i in range(1, len(lapdist_interp)):
        # Detect lap reset: lapdist drops by >100m AND goes below 500m (start of new lap)
        if (lapdist_interp[i] < lapdist_interp[i-1] - 100 and
            lapdist_interp[i] < 500):
            reset_indices.append(i)

    # Add boundaries
    lap_boundaries = [0] + reset_indices + [len(lapdist_interp)]

    # Step 2: Repair lapdist within each lap segment
    max_slope = 120.0  # meters per second (≈ 432 km/h physical limit)

    for lap_idx in range(len(lap_boundaries) - 1):
        start = lap_boundaries[lap_idx]
        end = lap_boundaries[lap_idx + 1]

        # Enforce monotonic increase within lap
        for i in range(start + 1, end):
            # Monotonicity: lapdist must not decrease
            if lapdist_interp[i] < lapdist_interp[i-1]:
                lapdist_interp[i] = lapdist_interp[i-1]

            # Physical limit: clamp unrealistic speed
            diff = lapdist_interp[i] - lapdist_interp[i-1]
            max_diff = max_slope * dt_s
            if diff > max_diff:
                lapdist_interp[i] = lapdist_interp[i-1] + max_diff

    # Interpolate brake front (default to 0 if not present)
    if 'brake_front' in df.columns:
        brake_front_interp = interp1d(t_original, df['brake_front'].values, kind='linear',
                                      bounds_error=False, fill_value='extrapolate')(global_t)
    else:
        brake_front_interp = np.zeros_like(global_t)

    # Interpolate brake rear (default to 0 if not present)
    if 'brake_rear' in df.columns:
        brake_rear_interp = interp1d(t_original, df['brake_rear'].values, kind='linear',
                                     bounds_error=False, fill_value='extrapolate')(global_t)
    else:
        brake_rear_interp = np.zeros_like(global_t)

    # Interpolate gear (use nearest neighbor to avoid fractional gears, default to 0 if not present)
    if 'gear' in df.columns:
        gear_interp = interp1d(t_original, df['gear'].values, kind='nearest',
                               bounds_error=False, fill_value=0)(global_t)
    else:
        gear_interp = np.zeros_like(global_t)

    # Interpolate steering (use nearest neighbor, keep in degrees, default to 0 if not present)
    if 'steering' in df.columns:
        steering_interp = interp1d(t_original, df['steering'].values, kind='nearest',
                                   bounds_error=False, fill_value=0)(global_t)
    else:
        steering_interp = np.zeros_like(global_t)

    # Interpolate lap (use nearest neighbor to avoid fractional laps, default to 1 if not present)
    if 'lap' in df.columns:
        lap_interp = interp1d(t_original, df['lap'].values, kind='nearest',
                              bounds_error=False, fill_value=1)(global_t)
        # Normalize lap numbers to start from 1 (subtract minimum lap - 1)
        min_lap = lap_interp.min()
        if min_lap > 1:
            lap_interp = lap_interp - min_lap + 1
    else:
        lap_interp = np.ones_like(global_t)

    # Compute heading from XY velocity (raw, no smoothing)
    dx = np.diff(x_interp, append=x_interp[-1])
    dy = np.diff(y_interp, append=y_interp[-1])
    heading_interp = np.arctan2(dy, dx)  # Radians, range [-π, π]

    # Interpolate acceleration (linear, default to 0 if not present)
    if 'accx' in df.columns:
        accx_interp = interp1d(t_original, df['accx'].values, kind='linear',
                               bounds_error=False, fill_value=0)(global_t)
    else:
        accx_interp = np.zeros_like(global_t)

    if 'accy' in df.columns:
        accy_interp = interp1d(t_original, df['accy'].values, kind='linear',
                               bounds_error=False, fill_value=0)(global_t)
    else:
        accy_interp = np.zeros_like(global_t)

    # Compute normalized acceleration magnitude
    accel_mag = np.sqrt(accx_interp**2 + accy_interp**2)
    accel_clamped = np.clip(accel_mag, 0, 12.0)  # Clamp to 0-12 m/s²
    accel_norm = accel_clamped / 12.0  # Normalize to 0-1

    # Stack into trajectory array (11 columns with lap at the end)
    trajectory = np.column_stack([x_interp, y_interp, speed_interp, lapdist_interp,
                                  brake_front_interp, brake_rear_interp, gear_interp,
                                  steering_interp, heading_interp, accel_norm, lap_interp])

    return trajectory, global_t
