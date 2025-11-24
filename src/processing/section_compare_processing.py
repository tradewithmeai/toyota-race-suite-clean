"""
Section Compare Processing Pipeline

This module processes raw telemetry data to generate:
- Canonical racing line with curvature
- Ideal lap profile with speed and timing
- Sector map with timing breakdown
- Per-car racing line exports (plots and CSVs)

The pipeline follows these major steps:
1. Load and validate raw telemetry data
2. Pivot from long to wide format and compute lap statistics
3. Filter valid laps and cars
4. Convert GPS coordinates to ENU (East-North-Up) metres
5. Interpolate all laps to a fixed grid
6. Compute per-car median racing lines
7. Filter outlier cars by lap time
8. Generate canonical racing line with curvature
9. Compute speed profiles
10. Calculate ideal speed, lap time, and sectors
11. Export per-car racing line artefacts
"""

import os
import json
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d
from scipy.signal import savgol_filter
from scipy.ndimage import gaussian_filter1d

from utils.logging_utils import get_logger

logger = get_logger(__name__)

# =============================================================================
# CONSTANTS
# =============================================================================

# Core processing constants
N_POINTS = 30000        # Canonical grid length
CURV_WINDOW = 101       # Savitzky-Golay window (must be odd, < N_POINTS)
CURV_POLY = 3           # Savitzky-Golay polynomial order
SPEED_CLIP_MS = 90.0    # m/s ≈ 324 km/h

# WGS84 ellipsoid parameters
A_WGS84 = 6378137.0
E2_WGS84 = 6.69437999014e-3

# Reference lap for origin (can be configured)
DEFAULT_REF_VID = "GR86-016-55"
DEFAULT_REF_LAP = 2

# Validate constants
assert CURV_WINDOW % 2 == 1, "CURV_WINDOW must be odd"
assert CURV_WINDOW < N_POINTS, "CURV_WINDOW must be smaller than N_POINTS"


# =============================================================================
# STATS DATACLASS
# =============================================================================

@dataclass
class SectionCompareStats:
    """Statistics from section compare processing."""
    raw_rows: int
    total_cars: int
    cars_with_valid_laps: int
    clean_laps_count: int
    cars_with_median_lines: int
    cars_after_outlier_filter: int
    track_length_m: float
    ideal_lap_time_s: float
    n_sectors: int
    fastest_lap_exports: int
    per_car_exports: int


# =============================================================================
# GPS CONVERSION HELPERS
# =============================================================================

def llh_to_ecef(lat_deg: np.ndarray, lon_deg: np.ndarray, h_m: float = 0.0) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert latitude/longitude/height to ECEF coordinates."""
    lat = np.deg2rad(lat_deg)
    lon = np.deg2rad(lon_deg)
    sin_lat = np.sin(lat)
    cos_lat = np.cos(lat)
    sin_lon = np.sin(lon)
    cos_lon = np.cos(lon)

    N = A_WGS84 / np.sqrt(1.0 - E2_WGS84 * sin_lat**2)

    X = (N + h_m) * cos_lat * cos_lon
    Y = (N + h_m) * cos_lat * sin_lon
    Z = (N * (1.0 - E2_WGS84) + h_m) * sin_lat
    return X, Y, Z


def ecef_to_enu(
    X: np.ndarray, Y: np.ndarray, Z: np.ndarray,
    lat0_deg: float, lon0_deg: float, h0_m: float = 0.0
) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
    """Convert ECEF to ENU (East-North-Up) coordinates."""
    lat0 = np.deg2rad(lat0_deg)
    lon0 = np.deg2rad(lon0_deg)
    sin_lat0 = np.sin(lat0)
    cos_lat0 = np.cos(lat0)
    sin_lon0 = np.sin(lon0)
    cos_lon0 = np.cos(lon0)

    X0, Y0, Z0 = llh_to_ecef(lat0_deg, lon0_deg, h0_m)

    dX = X - X0
    dY = Y - Y0
    dZ = Z - Z0

    t = np.array([
        [-sin_lon0,              cos_lon0,               0.0],
        [-sin_lat0*cos_lon0, -sin_lat0*sin_lon0,  cos_lat0],
        [ cos_lat0*cos_lon0,  cos_lat0*sin_lon0,  sin_lat0],
    ])

    vec = np.vstack((dX, dY, dZ))
    enu = t @ vec
    return enu[0, :], enu[1, :], enu[2, :]


def add_xy_enu(lap_df: pd.DataFrame, lat0_deg: float, lon0_deg: float) -> Optional[pd.DataFrame]:
    """Add x_m, y_m columns (ENU coordinates) to lap DataFrame."""
    lap_df = lap_df.dropna(subset=['VBOX_Lat_Min', 'VBOX_Long_Minutes']).copy()
    if lap_df.empty:
        return None

    lat_deg = lap_df['VBOX_Lat_Min'].to_numpy()
    lon_deg = lap_df['VBOX_Long_Minutes'].to_numpy()

    X, Y, Z = llh_to_ecef(lat_deg, lon_deg, h_m=0.0)
    E, Nn, U = ecef_to_enu(X, Y, Z, lat0_deg, lon0_deg, h0_m=0.0)

    lap_df['x_m'] = E
    lap_df['y_m'] = Nn
    return lap_df


def add_dist_along_lap(lap_df: pd.DataFrame) -> pd.DataFrame:
    """Add cumulative distance along lap."""
    lap_df = lap_df.sort_values('timestamp_dt').copy()
    x = lap_df['x_m'].to_numpy()
    y = lap_df['y_m'].to_numpy()

    dx = np.diff(x, prepend=x[0])
    dy = np.diff(y, prepend=y[0])
    ds = np.sqrt(dx**2 + dy**2)
    lap_df['dist_m'] = ds.cumsum()
    return lap_df


# =============================================================================
# SPEED CALCULATION
# =============================================================================

def add_speed_from_xy_time(lap_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate speed from position and time derivatives."""
    lap_df = lap_df.sort_values('timestamp_dt').copy()
    t = (lap_df['timestamp_dt'] - lap_df['timestamp_dt'].iloc[0]).dt.total_seconds().to_numpy()
    x = lap_df['x_m'].to_numpy()
    y = lap_df['y_m'].to_numpy()

    N = len(t)
    if N < 3 or np.allclose(t, t[0]):
        lap_df['speed_ms'] = 0.0
        return lap_df

    dt = np.diff(t)
    dx = np.diff(x)
    dy = np.diff(y)

    positive_dt = dt[dt > 0]
    if len(positive_dt) == 0:
        lap_df['speed_ms'] = 0.0
        return lap_df

    dt_median = np.median(positive_dt)
    tiny_mask = (dt <= 0) | (dt < 0.005)

    dt_safe = dt.copy()
    dt_safe[tiny_mask] = dt_median

    v_seg = np.sqrt(dx**2 + dy**2) / dt_safe
    v = np.concatenate(([v_seg[0]], v_seg))
    v = np.nan_to_num(v, nan=0.0, posinf=0.0, neginf=0.0)
    v_smooth = gaussian_filter1d(v, sigma=2)
    v_smooth = np.clip(v_smooth, 0.0, SPEED_CLIP_MS)

    lap_df['speed_ms'] = v_smooth
    return lap_df


# =============================================================================
# MAIN PROCESSING FUNCTIONS
# =============================================================================

def load_and_validate_raw_data(raw_csv_path: str) -> pd.DataFrame:
    """Load raw telemetry CSV and validate required channels."""
    logger.info("=" * 60)
    logger.info("LOADING RAW DATA")
    logger.info("=" * 60)

    raw = pd.read_csv(raw_csv_path)
    logger.info(f"Raw data shape: {raw.shape}")

    # Parse timestamps
    raw['timestamp_dt'] = pd.to_datetime(raw['timestamp'], errors='coerce')
    nat_count = raw['timestamp_dt'].isna().sum()
    if nat_count > 0:
        raise ValueError(f"Found {nat_count} NaT values in timestamp_dt")

    # Validate telemetry channels
    expected_names = {
        'Laptrigger_lapdist_dls',
        'Steering_Angle',
        'VBOX_Lat_Min',
        'VBOX_Long_Minutes',
        'accx_can',
        'accy_can',
        'aps',
        'gear',
        'nmot',
        'pbrake_f',
        'pbrake_r',
        'speed',
    }
    actual_names = set(raw['telemetry_name'].unique())
    missing = expected_names - actual_names
    if missing:
        logger.warning(f"Missing telemetry channels: {missing}")

    logger.info(f"Found {len(actual_names)} telemetry channels")
    return raw


def pivot_to_wide_and_compute_lap_stats(raw: pd.DataFrame) -> Tuple[pd.DataFrame, pd.DataFrame]:
    """Convert long format to wide and compute lap statistics."""
    logger.info("=" * 60)
    logger.info("PIVOTING TO WIDE FORMAT")
    logger.info("=" * 60)

    # Focused telemetry frame
    tele = raw[['timestamp_dt', 'timestamp', 'vehicle_id', 'lap',
                'telemetry_name', 'telemetry_value']].copy()

    # Pivot: one row per (vehicle_id, lap, timestamp)
    df_wide = tele.pivot_table(
        index=['vehicle_id', 'lap', 'timestamp_dt'],
        columns='telemetry_name',
        values='telemetry_value',
        aggfunc='mean',
    ).reset_index()
    df_wide.columns.name = None

    # Sort & flag GPS rows
    df_wide_sorted = df_wide.sort_values(['vehicle_id', 'lap', 'timestamp_dt'])
    df_wide_sorted['gps_valid'] = (
        df_wide_sorted['VBOX_Lat_Min'].notna() &
        df_wide_sorted['VBOX_Long_Minutes'].notna()
    )

    # Per-lap stats
    lap_stats = (
        df_wide_sorted
        .groupby(['vehicle_id', 'lap'])
        .agg(
            n_rows=('timestamp_dt', 'size'),
            n_gps=('gps_valid', 'sum'),
            t_start=('timestamp_dt', 'min'),
            t_end=('timestamp_dt', 'max'),
        )
        .reset_index()
    )
    lap_stats['duration_s'] = (lap_stats['t_end'] - lap_stats['t_start']).dt.total_seconds()

    logger.info(f"Wide data shape: {df_wide_sorted.shape}")
    logger.info(f"Total laps: {len(lap_stats)}")

    return df_wide_sorted, lap_stats


def filter_valid_laps_and_build_clean_laps(
    df_wide_sorted: pd.DataFrame,
    lap_stats: pd.DataFrame
) -> Tuple[Dict[Tuple[str, Any], pd.DataFrame], pd.DataFrame]:
    """Filter valid laps and build clean_laps dictionary."""
    logger.info("=" * 60)
    logger.info("FILTERING VALID LAPS")
    logger.info("=" * 60)

    # Valid lap criteria
    lap_stats['valid_lap'] = (
        (lap_stats['lap'] != 1) &          # drop lap 1
        (lap_stats['n_gps'] >= 50) &       # enough GPS points
        (lap_stats['duration_s'] > 40.0)   # duration sanity filter
    )

    # Count valid laps per car
    car_valid_counts = (
        lap_stats
        .groupby('vehicle_id')['valid_lap']
        .sum()
        .rename('n_valid_laps')
    )
    lap_stats = lap_stats.merge(car_valid_counts, on='vehicle_id')
    lap_stats['valid_car'] = lap_stats['n_valid_laps'] >= 3

    total_cars = lap_stats['vehicle_id'].nunique()
    valid_cars = lap_stats[lap_stats['valid_car']].vehicle_id.nunique()
    logger.info(f"Total cars: {total_cars}")
    logger.info(f"Cars with >=3 valid laps: {valid_cars}")

    # Attach flags to per-row data
    lap_flags = lap_stats[['vehicle_id', 'lap', 'valid_lap', 'valid_car']].copy()
    df_merged = df_wide_sorted.merge(
        lap_flags,
        on=['vehicle_id', 'lap'],
        how='left',
        validate='m:1',
    )

    clean_df = df_merged[(df_merged['valid_car']) & (df_merged['valid_lap'])].copy()
    logger.info(f"Clean data rows: {len(clean_df)}")

    # Build clean_laps
    clean_laps = {}
    for (vid, lap), group in clean_df.groupby(['vehicle_id', 'lap']):
        lap_df = (
            group
            .sort_values('timestamp_dt')
            .drop_duplicates(subset='timestamp_dt')
        )
        clean_laps[(vid, lap)] = lap_df

    logger.info(f"Clean laps entries: {len(clean_laps)}")

    return clean_laps, lap_stats


def apply_enu_conversion(
    clean_laps: Dict[Tuple[str, Any], pd.DataFrame],
    ref_vid: str = DEFAULT_REF_VID,
    ref_lap_num: int = DEFAULT_REF_LAP
) -> Dict[Tuple[str, Any], pd.DataFrame]:
    """Convert GPS to ENU coordinates for all laps."""
    logger.info("=" * 60)
    logger.info("GPS TO ENU CONVERSION")
    logger.info("=" * 60)

    # Find reference lap for origin
    ref_keys = [k for k in clean_laps.keys()
                if (k[0] == ref_vid) and (int(k[1]) == ref_lap_num)]

    if len(ref_keys) != 1:
        # Fallback: use first available lap
        ref_key = list(clean_laps.keys())[0]
        logger.warning(f"Reference lap {ref_vid} lap {ref_lap_num} not found, using {ref_key}")
    else:
        ref_key = ref_keys[0]

    ref_lap_df = clean_laps[ref_key]
    origin_lat_deg = ref_lap_df['VBOX_Lat_Min'].median()
    origin_lon_deg = ref_lap_df['VBOX_Long_Minutes'].median()
    logger.info(f"Origin lat, lon (deg): {origin_lat_deg}, {origin_lon_deg}")

    # Apply ENU conversion to all laps
    new_clean_laps = {}
    for key, lap_df in clean_laps.items():
        projected = add_xy_enu(lap_df, origin_lat_deg, origin_lon_deg)
        if projected is None or len(projected) < 2:
            continue
        projected = add_dist_along_lap(projected)
        new_clean_laps[key] = projected

    logger.info(f"Laps with ENU + dist_m: {len(new_clean_laps)}")

    return new_clean_laps


def interpolate_laps_to_grid(
    clean_laps: Dict[Tuple[str, Any], pd.DataFrame]
) -> Dict[Tuple[str, Any], np.ndarray]:
    """Interpolate all laps to fixed N_POINTS grid."""
    logger.info("=" * 60)
    logger.info("INTERPOLATING LAPS TO GRID")
    logger.info("=" * 60)

    lap_xy_interp = {}

    for key, lap_df in clean_laps.items():
        lap_df = lap_df.sort_values('dist_m')
        dist = lap_df['dist_m'].to_numpy()
        x = lap_df['x_m'].to_numpy()
        y = lap_df['y_m'].to_numpy()

        if len(dist) < 2 or dist[-1] <= 0:
            continue

        # Remove duplicate distances
        dist_unique, idx = np.unique(dist, return_index=True)
        x_unique = x[idx]
        y_unique = y[idx]
        if len(dist_unique) < 2:
            continue

        dist_uniform = np.linspace(0.0, dist_unique[-1], N_POINTS)

        fx = interp1d(
            dist_unique, x_unique, kind='linear',
            bounds_error=False,
            fill_value=(x_unique[0], x_unique[-1]),
        )
        fy = interp1d(
            dist_unique, y_unique, kind='linear',
            bounds_error=False,
            fill_value=(y_unique[0], y_unique[-1]),
        )

        x_interp = fx(dist_uniform)
        y_interp = fy(dist_uniform)
        lap_xy_interp[key] = np.stack([x_interp, y_interp], axis=1)

    logger.info(f"Interpolated lap entries: {len(lap_xy_interp)}")

    return lap_xy_interp


def compute_car_median_lines(
    lap_xy_interp: Dict[Tuple[str, Any], np.ndarray]
) -> Dict[str, np.ndarray]:
    """Compute per-car median racing lines."""
    logger.info("=" * 60)
    logger.info("COMPUTING PER-CAR MEDIAN LINES")
    logger.info("=" * 60)

    car_median_line = {}
    car_ids = sorted({vid for (vid, lap) in lap_xy_interp.keys()})

    for vid in car_ids:
        car_laps = [lap_xy_interp[(v, l)]
                    for (v, l) in lap_xy_interp.keys()
                    if v == vid]
        if len(car_laps) < 3:
            continue
        stack = np.stack(car_laps, axis=0)   # (n_laps, N_POINTS, 2)
        median_xy = np.median(stack, axis=0)
        car_median_line[vid] = median_xy

    logger.info(f"Cars with median lines: {len(car_median_line)}")

    return car_median_line


def filter_outlier_cars(
    car_median_line: Dict[str, np.ndarray],
    lap_stats: pd.DataFrame,
    z_threshold: float = 2.5
) -> Dict[str, np.ndarray]:
    """Filter cars with outlier lap times."""
    logger.info("=" * 60)
    logger.info("FILTERING OUTLIER CARS")
    logger.info("=" * 60)

    # Lap-time stats per car from valid laps only
    valid_lap_times = lap_stats[lap_stats['valid_lap']].copy()
    car_median_lap_times = (
        valid_lap_times
        .groupby('vehicle_id')['duration_s']
        .median()
        .reset_index()
        .rename(columns={'duration_s': 'median_lap_time_s'})
    )

    mu = car_median_lap_times['median_lap_time_s'].mean()
    sigma = car_median_lap_times['median_lap_time_s'].std()
    car_median_lap_times['z_score'] = (car_median_lap_times['median_lap_time_s'] - mu) / sigma

    # Keep cars |Z| <= threshold
    good_cars = set(
        car_median_lap_times.loc[
            car_median_lap_times['z_score'].abs() <= z_threshold,
            'vehicle_id'
        ]
    )

    car_median_line_filtered = {
        vid: xy for vid, xy in car_median_line.items() if vid in good_cars
    }
    logger.info(f"Cars kept after outlier filtering: {len(car_median_line_filtered)}")

    return car_median_line_filtered


def compute_canonical_line_and_curvature(
    car_median_line_filtered: Dict[str, np.ndarray]
) -> pd.DataFrame:
    """Generate canonical racing line with curvature."""
    logger.info("=" * 60)
    logger.info("COMPUTING CANONICAL LINE AND CURVATURE")
    logger.info("=" * 60)

    # Stack car medians → global median
    car_ids_filt = sorted(car_median_line_filtered.keys())
    median_arrays = [car_median_line_filtered[vid] for vid in car_ids_filt]
    median_stack = np.stack(median_arrays, axis=0)    # (n_cars, N_POINTS, 2)

    canonical_xy = np.median(median_stack, axis=0)    # (N_POINTS, 2)
    canonical_x = canonical_xy[:, 0]
    canonical_y = canonical_xy[:, 1]

    # Distance along canonical
    dx = np.diff(canonical_x, prepend=canonical_x[0])
    dy = np.diff(canonical_y, prepend=canonical_y[0])
    canonical_ds = np.sqrt(dx**2 + dy**2)
    s_canon = canonical_ds.cumsum()

    track_length_m = float(s_canon[-1])
    logger.info(f"Canonical track length (m): {track_length_m}")

    # Canonical line DataFrame
    canonical_line = pd.DataFrame({
        "dist_m": s_canon,
        "x_m": canonical_x,
        "y_m": canonical_y,
    })

    # Curvature calculation
    x = canonical_line['x_m'].to_numpy()
    y = canonical_line['y_m'].to_numpy()

    ds_mean = np.mean(np.diff(s_canon))

    dx = savgol_filter(x, CURV_WINDOW, CURV_POLY, deriv=1, delta=ds_mean)
    dy = savgol_filter(y, CURV_WINDOW, CURV_POLY, deriv=1, delta=ds_mean)
    d2x = savgol_filter(x, CURV_WINDOW, CURV_POLY, deriv=2, delta=ds_mean)
    d2y = savgol_filter(y, CURV_WINDOW, CURV_POLY, deriv=2, delta=ds_mean)

    num = np.abs(dx * d2y - dy * d2x)
    den = (dx**2 + dy**2) ** 1.5
    curvature_raw = num / den
    curvature_raw = np.nan_to_num(curvature_raw, nan=0.0, posinf=0.0, neginf=0.0)
    curvature = gaussian_filter1d(curvature_raw, sigma=8)

    canonical_line['curvature'] = curvature

    return canonical_line


def compute_speed_profiles(
    clean_laps: Dict[Tuple[str, Any], pd.DataFrame],
    canonical_line: pd.DataFrame
) -> pd.DataFrame:
    """Compute reference speed profile from all laps."""
    logger.info("=" * 60)
    logger.info("COMPUTING SPEED PROFILES")
    logger.info("=" * 60)

    # Apply speed calculation to all laps
    for key, lap_df in list(clean_laps.items()):
        if not {'x_m', 'y_m', 'timestamp_dt'}.issubset(lap_df.columns):
            continue
        clean_laps[key] = add_speed_from_xy_time(lap_df)

    # Map speeds to canonical distance grid
    canonical_s = canonical_line['dist_m'].to_numpy()
    track_len_canon = float(canonical_s[-1])
    canonical_s_norm = canonical_s / track_len_canon

    speed_fields = []

    for (vid, lap), lap_df in clean_laps.items():
        if not {'dist_m', 'speed_ms'}.issubset(lap_df.columns):
            continue

        lap_df = lap_df.sort_values('dist_m')
        s_lap = lap_df['dist_m'].to_numpy()
        v_lap = lap_df['speed_ms'].to_numpy()

        if len(s_lap) < 2 or s_lap[-1] <= 0:
            continue

        s_lap_norm = s_lap / s_lap[-1]
        s_unique, idx = np.unique(s_lap_norm, return_index=True)
        v_unique = v_lap[idx]
        if len(s_unique) < 2:
            continue

        f_v = interp1d(
            s_unique, v_unique,
            kind='linear',
            bounds_error=False,
            fill_value=(v_unique[0], v_unique[-1]),
        )

        v_on_canon = f_v(canonical_s_norm)
        speed_fields.append(v_on_canon)

    speed_fields = np.stack(speed_fields, axis=0)
    logger.info(f"Speed fields shape: {speed_fields.shape}")

    ref_speed_ms = np.percentile(speed_fields, 95, axis=0)
    canonical_line['ref_speed_ms'] = ref_speed_ms

    return canonical_line


def compute_ideal_speed_and_sectors(
    canonical_line: pd.DataFrame,
    n_sectors: int = 3
) -> Tuple[pd.DataFrame, List[Dict[str, Any]]]:
    """Compute ideal speed, lap time, and sector breakdown."""
    logger.info("=" * 60)
    logger.info("COMPUTING IDEAL SPEED AND SECTORS")
    logger.info("=" * 60)

    # Curvature-scaled ideal speed
    curv = canonical_line['curvature'].to_numpy()
    max_curv = curv.max() if curv.max() > 0 else 1.0
    curv_scaled = curv / max_curv

    ref_v = canonical_line['ref_speed_ms'].to_numpy()
    ideal_speed_ms = ref_v * (1.0 - 0.55 * curv_scaled)
    ideal_speed_ms = np.clip(ideal_speed_ms, 15.0, None)

    canonical_line['ideal_speed_ms'] = ideal_speed_ms

    # Ideal lap time
    s = canonical_line['dist_m'].to_numpy()
    ds = np.diff(s, prepend=s[0])
    dt_seg = ds / ideal_speed_ms
    ideal_time_s = dt_seg.cumsum()
    canonical_line['ideal_time_s'] = ideal_time_s

    ideal_lap_time_s = float(ideal_time_s[-1])
    logger.info(f"Ideal lap time (s): {ideal_lap_time_s}")

    # Sectors (equal distance)
    total_dist = float(s[-1])
    sector_edges = np.linspace(0.0, total_dist, n_sectors + 1)

    sector_info = []
    for i in range(n_sectors):
        start = sector_edges[i]
        end = sector_edges[i + 1]

        if i < n_sectors - 1:
            mask = (s >= start) & (s < end)
        else:
            mask = (s >= start) & (s <= end)

        if not np.any(mask):
            sector_time = 0.0
        else:
            t_start = float(ideal_time_s[mask][0])
            t_end = float(ideal_time_s[mask][-1])
            sector_time = t_end - t_start

        sector_info.append({
            "sector": i + 1,
            "start_dist_m": float(start),
            "end_dist_m": float(end),
            "ideal_time_s": sector_time,
        })

    sector_sum = sum(sec['ideal_time_s'] for sec in sector_info)
    logger.info(f"Sector times (s): {[round(sec['ideal_time_s'], 3) for sec in sector_info]}")
    logger.info(f"Sector sum vs ideal: {sector_sum}, {ideal_lap_time_s}")

    return canonical_line, sector_info


def export_main_artefacts(
    canonical_line: pd.DataFrame,
    sector_info: List[Dict[str, Any]],
    out_dir: str
) -> None:
    """Export canonical racing line, ideal profile, speed profile, and sector map."""
    logger.info("=" * 60)
    logger.info("EXPORTING MAIN ARTEFACTS")
    logger.info("=" * 60)

    os.makedirs(out_dir, exist_ok=True)

    canonical_path = os.path.join(out_dir, "canonical_racing_line.csv")
    ideal_profile_path = os.path.join(out_dir, "ideal_lap_profile.csv")
    speed_profile_path = os.path.join(out_dir, "speed_profile.csv")
    sector_map_path = os.path.join(out_dir, "sector_map.json")

    canonical_line[['dist_m', 'x_m', 'y_m', 'curvature']].to_csv(
        canonical_path, index=False
    )
    canonical_line[['dist_m', 'ideal_speed_ms', 'ideal_time_s']].to_csv(
        ideal_profile_path, index=False
    )
    canonical_line[['dist_m', 'ref_speed_ms', 'ideal_speed_ms']].to_csv(
        speed_profile_path, index=False
    )

    total_dist = float(canonical_line['dist_m'].iloc[-1])
    ideal_lap_time_s = float(canonical_line['ideal_time_s'].iloc[-1])

    sector_payload = {
        "track_length_m": total_dist,
        "ideal_lap_time_s": ideal_lap_time_s,
        "sectors": sector_info,
    }
    with open(sector_map_path, "w") as f:
        json.dump(sector_payload, f, indent=2)

    logger.info(f"Saved: {canonical_path}")
    logger.info(f"Saved: {ideal_profile_path}")
    logger.info(f"Saved: {speed_profile_path}")
    logger.info(f"Saved: {sector_map_path}")


def collect_car_laps_xy(
    clean_laps: Dict[Tuple[str, Any], pd.DataFrame]
) -> Dict[str, List[Tuple[int, pd.DataFrame]]]:
    """Collect laps by car for plotting."""
    car_laps = defaultdict(list)
    for (vid, lap), lap_df in clean_laps.items():
        if not {'x_m', 'y_m'}.issubset(lap_df.columns):
            continue
        car_laps[vid].append((int(lap), lap_df.sort_values('timestamp_dt')))
    for vid in car_laps:
        car_laps[vid].sort(key=lambda tup: tup[0])
    return car_laps


def car_median_df(
    vid: str,
    car_median_line_filtered: Dict[str, np.ndarray],
    canonical_line: pd.DataFrame
) -> pd.DataFrame:
    """Create DataFrame for car's median line."""
    xy = car_median_line_filtered[vid]
    s_canon = canonical_line['dist_m'].to_numpy()
    s_norm = s_canon / float(s_canon[-1])

    return pd.DataFrame({
        "vehicle_id": vid,
        "dist_m": s_canon,
        "s_norm": s_norm,
        "x_m": xy[:, 0],
        "y_m": xy[:, 1],
    })


def plot_car_racing_line(
    vid: str,
    car_laps_xy: Dict[str, List[Tuple[int, pd.DataFrame]]],
    car_median_line_filtered: Dict[str, np.ndarray],
    canonical_line: pd.DataFrame,
    out_dir: str,
    show: bool = False
) -> str:
    """Plot racing line for a single car."""
    laps = car_laps_xy[vid]
    median_xy = car_median_line_filtered[vid]
    canon_x = canonical_line['x_m'].to_numpy()
    canon_y = canonical_line['y_m'].to_numpy()

    plt.figure(figsize=(6, 6))

    # All laps for this car
    for lap_num, lap_df in laps:
        plt.plot(
            lap_df['x_m'].to_numpy(),
            lap_df['y_m'].to_numpy(),
            linewidth=0.5,
            alpha=0.3,
        )

    # Car median
    plt.plot(
        median_xy[:, 0],
        median_xy[:, 1],
        linewidth=1.8,
        label=f"{vid} median",
    )

    # Canonical line
    plt.plot(
        canon_x,
        canon_y,
        "k",
        linewidth=2.0,
        label="canonical",
    )

    plt.axis('equal')
    plt.xlabel("x_m (east, m)")
    plt.ylabel("y_m (north, m)")
    plt.title(f"Racing line - {vid}")
    plt.legend(loc="best")
    plt.tight_layout()

    fname = f"racing_line_{vid}.png"
    fpath = os.path.join(out_dir, fname)
    plt.savefig(fpath)
    if show:
        plt.show()
    else:
        plt.close()

    return fpath


def export_fastest_laps(
    clean_laps: Dict[Tuple[str, Any], pd.DataFrame],
    lap_stats: pd.DataFrame,
    car_median_line_filtered: Dict[str, np.ndarray],
    out_dir: str
) -> int:
    """Export fastest lap per car to CSV files for trail generation.

    Args:
        clean_laps: Dictionary of (vehicle_id, lap) -> lap DataFrame
        lap_stats: DataFrame with lap statistics including duration_s
        car_median_line_filtered: Dictionary of filtered car median lines
        out_dir: Output directory

    Returns:
        Number of fastest laps exported
    """
    logger.info("=" * 60)
    logger.info("EXPORTING FASTEST LAPS")
    logger.info("=" * 60)

    # Create output directory
    lap_csv_dir = os.path.join(out_dir, "fastest_laps", "lap_csv")
    os.makedirs(lap_csv_dir, exist_ok=True)

    # Get valid cars (those that passed filtering)
    good_cars = set(car_median_line_filtered.keys())

    # Filter lap_stats to valid laps from good cars
    valid_laps = lap_stats[
        (lap_stats['valid_lap']) &
        (lap_stats['vehicle_id'].isin(good_cars))
    ].copy()

    if valid_laps.empty:
        logger.warning("No valid laps found for fastest lap export")
        return 0

    # Find fastest lap per car (minimum duration_s)
    idx_fastest = valid_laps.groupby('vehicle_id')['duration_s'].idxmin()
    fastest_per_car = valid_laps.loc[idx_fastest]

    logger.info(f"Found fastest laps for {len(fastest_per_car)} cars")

    export_count = 0
    export_records = []

    for _, row in fastest_per_car.iterrows():
        vid = row['vehicle_id']
        lap = int(row['lap'])
        key = (vid, lap)

        if key not in clean_laps:
            logger.warning(f"{vid} lap {lap}: not in clean_laps, skipping")
            continue

        lap_df = clean_laps[key].copy()

        # Ensure required columns exist
        cols_wanted = ["timestamp_dt", "dist_m", "x_m", "y_m", "speed_ms"]
        cols_present = [c for c in cols_wanted if c in lap_df.columns]

        if len(cols_present) < len(cols_wanted):
            missing = set(cols_wanted) - set(cols_present)
            logger.warning(f"{vid} lap {lap}: missing columns {missing}")

        # Export to CSV
        out_path = os.path.join(lap_csv_dir, f"fastest_lap_{vid}_lap{lap}.csv")
        lap_df[cols_present].to_csv(out_path, index=False)

        export_records.append({
            "vehicle_id": vid,
            "lap": lap,
            "lap_time_s": float(row['duration_s']),
            "csv_path": out_path,
            "n_points": len(lap_df)
        })

        export_count += 1
        logger.info(f"Exported fastest lap for {vid}: lap {lap} ({row['duration_s']:.2f}s)")

    # Save summary
    if export_records:
        summary_df = pd.DataFrame(export_records)
        summary_path = os.path.join(out_dir, "fastest_laps", "fastest_lap_exports.csv")
        summary_df.to_csv(summary_path, index=False)
        logger.info(f"Fastest lap summary saved to: {summary_path}")

    logger.info(f"Exported {export_count} fastest laps")
    return export_count


def export_per_car_racing_lines(
    clean_laps: Dict[Tuple[str, Any], pd.DataFrame],
    car_median_line_filtered: Dict[str, np.ndarray],
    canonical_line: pd.DataFrame,
    out_dir: str
) -> int:
    """Export per-car racing line plots and CSVs."""
    logger.info("=" * 60)
    logger.info("EXPORTING PER-CAR RACING LINES")
    logger.info("=" * 60)

    car_laps_xy = collect_car_laps_xy(clean_laps)
    logger.info(f"Cars with lap data: {sorted(car_laps_xy.keys())}")

    car_line_dir = os.path.join(out_dir, "per_car_racing_lines")
    os.makedirs(car_line_dir, exist_ok=True)

    median_csv_dir = os.path.join(car_line_dir, "median_csv")
    os.makedirs(median_csv_dir, exist_ok=True)

    export_records = []

    for vid in sorted(car_median_line_filtered.keys()):
        if vid not in car_laps_xy:
            logger.warning(f"{vid}: median line but no laps; skipping")
            continue

        logger.info(f"Processing car: {vid}")

        # Plot PNG
        png_path = plot_car_racing_line(
            vid, car_laps_xy, car_median_line_filtered, canonical_line,
            car_line_dir, show=False
        )

        # Median CSV
        df_med = car_median_df(vid, car_median_line_filtered, canonical_line)
        csv_path = os.path.join(median_csv_dir, f"median_racing_line_{vid}.csv")
        df_med.to_csv(csv_path, index=False)

        export_records.append({
            "vehicle_id": vid,
            "png_path": png_path,
            "csv_path": csv_path,
            "n_laps_used": len(car_laps_xy[vid]),
        })

    export_summary = pd.DataFrame(export_records)
    summary_path = os.path.join(car_line_dir, "per_car_racing_line_exports.csv")
    export_summary.to_csv(summary_path, index=False)

    logger.info(f"Export summary written to: {summary_path}")
    logger.info(f"Exported {len(export_records)} car racing lines")

    return len(export_records)


# =============================================================================
# MAIN ORCHESTRATOR
# =============================================================================

def run_section_compare_processing(
    raw_csv_path: str,
    output_dir: str,
    ref_vid: str = DEFAULT_REF_VID,
    ref_lap: int = DEFAULT_REF_LAP,
    n_sectors: int = 3
) -> Tuple[pd.DataFrame, SectionCompareStats]:
    """
    Run the complete section compare processing pipeline.

    Args:
        raw_csv_path: Path to raw telemetry CSV
        output_dir: Output directory for exports
        ref_vid: Reference vehicle ID for ENU origin
        ref_lap: Reference lap number for ENU origin
        n_sectors: Number of track sectors

    Returns:
        (canonical_line DataFrame, processing stats)
    """
    logger.info("=" * 60)
    logger.info("SECTION COMPARE PROCESSING PIPELINE")
    logger.info("=" * 60)
    logger.info(f"Input: {raw_csv_path}")
    logger.info(f"Output: {output_dir}")

    # Set matplotlib DPI
    plt.rcParams["figure.dpi"] = 110

    # Step 1-2: Load and validate raw data
    raw = load_and_validate_raw_data(raw_csv_path)
    raw_rows = len(raw)

    # Step 3: Pivot to wide format and compute lap stats
    df_wide_sorted, lap_stats = pivot_to_wide_and_compute_lap_stats(raw)
    total_cars = lap_stats['vehicle_id'].nunique()

    # Step 4: Filter valid laps and build clean_laps
    clean_laps, lap_stats = filter_valid_laps_and_build_clean_laps(df_wide_sorted, lap_stats)
    cars_with_valid_laps = lap_stats[lap_stats['valid_car']].vehicle_id.nunique()
    clean_laps_count = len(clean_laps)

    # Step 5: GPS → ENU conversion
    clean_laps = apply_enu_conversion(clean_laps, ref_vid, ref_lap)

    # Step 6: Interpolate laps to fixed grid
    lap_xy_interp = interpolate_laps_to_grid(clean_laps)

    # Step 7: Compute per-car median lines
    car_median_line = compute_car_median_lines(lap_xy_interp)
    cars_with_median_lines = len(car_median_line)

    # Filter outlier cars
    car_median_line_filtered = filter_outlier_cars(car_median_line, lap_stats)
    cars_after_outlier_filter = len(car_median_line_filtered)

    # Step 8: Compute canonical line and curvature
    canonical_line = compute_canonical_line_and_curvature(car_median_line_filtered)

    # Step 9: Compute speed profiles
    canonical_line = compute_speed_profiles(clean_laps, canonical_line)

    # Step 10: Compute ideal speed and sectors
    canonical_line, sector_info = compute_ideal_speed_and_sectors(canonical_line, n_sectors)

    # Export main artefacts
    export_main_artefacts(canonical_line, sector_info, output_dir)

    # Step 11: Export fastest laps for trail generation
    fastest_lap_exports = export_fastest_laps(
        clean_laps, lap_stats, car_median_line_filtered, output_dir
    )

    # Step 12: Export per-car racing lines
    per_car_exports = export_per_car_racing_lines(
        clean_laps, car_median_line_filtered, canonical_line, output_dir
    )

    # Compute stats
    track_length_m = float(canonical_line['dist_m'].iloc[-1])
    ideal_lap_time_s = float(canonical_line['ideal_time_s'].iloc[-1])

    stats = SectionCompareStats(
        raw_rows=raw_rows,
        total_cars=total_cars,
        cars_with_valid_laps=cars_with_valid_laps,
        clean_laps_count=clean_laps_count,
        cars_with_median_lines=cars_with_median_lines,
        cars_after_outlier_filter=cars_after_outlier_filter,
        track_length_m=track_length_m,
        ideal_lap_time_s=ideal_lap_time_s,
        n_sectors=n_sectors,
        fastest_lap_exports=fastest_lap_exports,
        per_car_exports=per_car_exports,
    )

    logger.info("=" * 60)
    logger.info("PROCESSING COMPLETE")
    logger.info("=" * 60)
    logger.info(f"Track length: {track_length_m:.1f} m")
    logger.info(f"Ideal lap time: {ideal_lap_time_s:.3f} s")
    logger.info(f"Per-car exports: {per_car_exports}")

    return canonical_line, stats


# =============================================================================
# CLI ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Section Compare Processing Pipeline")
    parser.add_argument(
        "--input", "-i",
        required=True,
        help="Path to raw telemetry CSV"
    )
    parser.add_argument(
        "--output", "-o",
        default="outputs",
        help="Output directory (default: outputs)"
    )
    parser.add_argument(
        "--ref-vid",
        default=DEFAULT_REF_VID,
        help=f"Reference vehicle ID for ENU origin (default: {DEFAULT_REF_VID})"
    )
    parser.add_argument(
        "--ref-lap",
        type=int,
        default=DEFAULT_REF_LAP,
        help=f"Reference lap number for ENU origin (default: {DEFAULT_REF_LAP})"
    )
    parser.add_argument(
        "--sectors",
        type=int,
        default=3,
        help="Number of track sectors (default: 3)"
    )

    args = parser.parse_args()

    canonical_line, stats = run_section_compare_processing(
        raw_csv_path=args.input,
        output_dir=args.output,
        ref_vid=args.ref_vid,
        ref_lap=args.ref_lap,
        n_sectors=args.sectors,
    )

    print("\nProcessing Statistics:")
    print(f"  Raw rows: {stats.raw_rows}")
    print(f"  Total cars: {stats.total_cars}")
    print(f"  Cars with valid laps: {stats.cars_with_valid_laps}")
    print(f"  Clean laps: {stats.clean_laps_count}")
    print(f"  Cars with median lines: {stats.cars_with_median_lines}")
    print(f"  Cars after filtering: {stats.cars_after_outlier_filter}")
    print(f"  Track length: {stats.track_length_m:.1f} m")
    print(f"  Ideal lap time: {stats.ideal_lap_time_s:.3f} s")
    print(f"  Fastest lap exports: {stats.fastest_lap_exports}")
    print(f"  Per-car exports: {stats.per_car_exports}")
