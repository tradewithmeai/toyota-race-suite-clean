"""Load and filter raw telemetry CSV using long-format filtering (NO PIVOTING)."""

import numpy as np
import pandas as pd


def load_telemetry(csv_path: str) -> pd.DataFrame:
    """Load raw telemetry CSV file with memory optimization."""
    print(f"Loading telemetry from {csv_path}...")

    # Specify dtypes to reduce memory usage
    # Float32 is sufficient for telemetry values
    dtype_spec = {
        'telemetry_value': 'float32',
        'lap': 'int16',
    }

    # Load with optimized dtypes and low_memory mode
    df = pd.read_csv(csv_path, dtype=dtype_spec, low_memory=True)

    # Convert object columns to category where beneficial
    if 'original_vehicle_id' in df.columns:
        df['original_vehicle_id'] = df['original_vehicle_id'].astype('category')
    if 'telemetry_name' in df.columns:
        df['telemetry_name'] = df['telemetry_name'].astype('category')

    print(f"Loaded {len(df):,} rows")
    return df


def get_vehicle_ids(df: pd.DataFrame) -> list:
    """Get list of unique vehicle IDs."""
    return sorted(df['original_vehicle_id'].unique().tolist())


def extract_signals(df: pd.DataFrame, vehicle_id: str) -> pd.DataFrame:
    """Extract GPS, speed, lapdist, lap, brake, gear using long-format filtering (NO PIVOTING)."""
    # Filter vehicle
    veh_df = df[df['original_vehicle_id'] == vehicle_id].copy()

    if len(veh_df) == 0:
        return pd.DataFrame()

    # Extract each signal by filtering telemetry_name
    lat = veh_df[veh_df['telemetry_name'] == 'VBOX_Lat_Min'][['timestamp', 'telemetry_value']].copy()
    lat.columns = ['timestamp', 'lat']

    lon = veh_df[veh_df['telemetry_name'] == 'VBOX_Long_Minutes'][['timestamp', 'telemetry_value']].copy()
    lon.columns = ['timestamp', 'lon']

    lapdist = veh_df[veh_df['telemetry_name'] == 'Laptrigger_lapdist_dls'][['timestamp', 'telemetry_value']].copy()
    lapdist.columns = ['timestamp', 'lapdist']

    speed = veh_df[veh_df['telemetry_name'] == 'speed'][['timestamp', 'telemetry_value']].copy()
    speed.columns = ['timestamp', 'speed']

    # Extract lap number (authoritative from CSV)
    # Lap is stored as a column in the CSV, not as telemetry_value
    lap = veh_df[veh_df['telemetry_name'] == 'speed'][['timestamp', 'lap']].copy()
    lap.columns = ['timestamp', 'lap']

    # Extract brake data - both front and rear separately
    brake_front = None
    brake_rear = None

    # Try to extract front brake
    for brake_name in ['pbrake_f', 'brake_front', 'BrakeF']:
        brake_f_df = veh_df[veh_df['telemetry_name'] == brake_name][['timestamp', 'telemetry_value']].copy()
        if len(brake_f_df) > 0:
            brake_f_df.columns = ['timestamp', 'brake_front']
            brake_front = brake_f_df
            break

    # Try to extract rear brake
    for brake_name in ['pbrake_r', 'brake_rear', 'BrakeR']:
        brake_r_df = veh_df[veh_df['telemetry_name'] == brake_name][['timestamp', 'telemetry_value']].copy()
        if len(brake_r_df) > 0:
            brake_r_df.columns = ['timestamp', 'brake_rear']
            brake_rear = brake_r_df
            break

    # Fallback: if only generic 'brake' exists, use for both
    if brake_front is None and brake_rear is None:
        for brake_name in ['brake', 'Brake']:
            brake_df = veh_df[veh_df['telemetry_name'] == brake_name][['timestamp', 'telemetry_value']].copy()
            if len(brake_df) > 0:
                brake_df.columns = ['timestamp', 'brake_front']
                brake_front = brake_df
                brake_rear = brake_df.copy()
                brake_rear.columns = ['timestamp', 'brake_rear']
                break

    # Extract gear data (try different column names)
    gear = None
    for gear_name in ['gear', 'Gear', 'gear_position', 'GearPosition']:
        gear_df = veh_df[veh_df['telemetry_name'] == gear_name][['timestamp', 'telemetry_value']].copy()
        if len(gear_df) > 0:
            gear_df.columns = ['timestamp', 'gear']
            gear = gear_df
            break

    # Extract steering angle data (store in degrees)
    steering = None
    for steer_name in ['Steering_Angle', 'steering', 'Steering', 'steering_angle']:
        steer_df = veh_df[veh_df['telemetry_name'] == steer_name][['timestamp', 'telemetry_value']].copy()
        if len(steer_df) > 0:
            steer_df.columns = ['timestamp', 'steering']
            steering = steer_df
            break

    # Extract acceleration data (longitudinal and lateral)
    accx = None
    for accx_name in ['accx_can', 'acc_x', 'accel_x']:
        accx_df = veh_df[veh_df['telemetry_name'] == accx_name][['timestamp', 'telemetry_value']].copy()
        if len(accx_df) > 0:
            accx_df.columns = ['timestamp', 'accx']
            accx = accx_df
            break

    accy = None
    for accy_name in ['accy_can', 'acc_y', 'accel_y']:
        accy_df = veh_df[veh_df['telemetry_name'] == accy_name][['timestamp', 'telemetry_value']].copy()
        if len(accy_df) > 0:
            accy_df.columns = ['timestamp', 'accy']
            accy = accy_df
            break

    # Convert timestamps to datetime and round to nearest 100ms for matching
    # Then deduplicate BEFORE merging to prevent cartesian product explosions

    # GPS signals use median aggregation for better accuracy
    lat['timestamp'] = pd.to_datetime(lat['timestamp'])
    lat['timestamp'] = lat['timestamp'].dt.round('100ms')
    duplicate_ratio = lat['timestamp'].duplicated().mean()
    if duplicate_ratio > 0.2:
        print(f"  [WARN] High duplicate ratio in lat: {duplicate_ratio:.1%}")
    lat = lat.groupby('timestamp', as_index=False).median()

    lon['timestamp'] = pd.to_datetime(lon['timestamp'])
    lon['timestamp'] = lon['timestamp'].dt.round('100ms')
    duplicate_ratio = lon['timestamp'].duplicated().mean()
    if duplicate_ratio > 0.2:
        print(f"  [WARN] High duplicate ratio in lon: {duplicate_ratio:.1%}")
    lon = lon.groupby('timestamp', as_index=False).median()

    # Other signals use first value (drop duplicates)
    other_signals = [lapdist, speed, lap]
    if brake_front is not None:
        other_signals.append(brake_front)
    if brake_rear is not None:
        other_signals.append(brake_rear)
    if gear is not None:
        other_signals.append(gear)
    if steering is not None:
        other_signals.append(steering)
    if accx is not None:
        other_signals.append(accx)
    if accy is not None:
        other_signals.append(accy)

    for signal_df in other_signals:
        signal_df['timestamp'] = pd.to_datetime(signal_df['timestamp'])
        signal_df['timestamp'] = signal_df['timestamp'].dt.round('100ms')
        duplicate_ratio = signal_df['timestamp'].duplicated().mean()
        if duplicate_ratio > 0.2:
            col_name = signal_df.columns[1]
            print(f"  [WARN] High duplicate ratio in {col_name}: {duplicate_ratio:.1%}")
        signal_df.drop_duplicates(subset='timestamp', keep='first', inplace=True)

    # Use inner merge to avoid cartesian products
    merged = lat.merge(lon, on='timestamp', how='inner')
    merged = merged.merge(lapdist, on='timestamp', how='inner')
    merged = merged.merge(speed, on='timestamp', how='inner')
    merged = merged.merge(lap, on='timestamp', how='inner')

    # Merge brake signals if available (left join to not lose data)
    if brake_front is not None:
        merged = merged.merge(brake_front, on='timestamp', how='left')
        merged['brake_front'] = merged['brake_front'].fillna(0.0)
    else:
        merged['brake_front'] = 0.0

    if brake_rear is not None:
        merged = merged.merge(brake_rear, on='timestamp', how='left')
        merged['brake_rear'] = merged['brake_rear'].fillna(0.0)
    else:
        merged['brake_rear'] = 0.0

    # Merge gear if available (left join to not lose data)
    if gear is not None:
        merged = merged.merge(gear, on='timestamp', how='left')
        merged['gear'] = merged['gear'].fillna(0)
    else:
        merged['gear'] = 0

    # Merge steering if available (left join to not lose data)
    if steering is not None:
        merged = merged.merge(steering, on='timestamp', how='left')
        merged['steering'] = merged['steering'].fillna(0.0)
    else:
        merged['steering'] = 0.0

    # Merge acceleration if available (left join to not lose data)
    if accx is not None:
        merged = merged.merge(accx, on='timestamp', how='left')
        merged['accx'] = merged['accx'].fillna(0.0)
    else:
        merged['accx'] = 0.0

    if accy is not None:
        merged = merged.merge(accy, on='timestamp', how='left')
        merged['accy'] = merged['accy'].fillna(0.0)
    else:
        merged['accy'] = 0.0

    # Drop duplicates that may arise from rounding
    merged = merged.drop_duplicates(subset='timestamp')

    # Sort and drop NaNs (except brake and gear which are already filled)
    merged = merged.sort_values('timestamp')
    merged = merged.dropna(subset=['lat', 'lon', 'lapdist', 'speed', 'lap'])

    # Convert types
    merged['lat'] = merged['lat'].astype(float)
    merged['lon'] = merged['lon'].astype(float)
    merged['lapdist'] = merged['lapdist'].astype(float)
    merged['speed'] = merged['speed'].astype(float)
    merged['lap'] = merged['lap'].astype(int)
    merged['brake_front'] = merged['brake_front'].astype(float)
    merged['brake_rear'] = merged['brake_rear'].astype(float)
    merged['gear'] = merged['gear'].astype(int)
    merged['steering'] = merged['steering'].astype(float)
    merged['accx'] = merged['accx'].astype(float)
    merged['accy'] = merged['accy'].astype(float)

    # Normalize brake signals to 0-1 range independently
    brake_front_max = merged['brake_front'].max()
    if brake_front_max > 0:
        merged['brake_front'] = merged['brake_front'] / brake_front_max

    brake_rear_max = merged['brake_rear'].max()
    if brake_rear_max > 0:
        merged['brake_rear'] = merged['brake_rear'] / brake_rear_max

    return merged


def gps_to_xy(lat: np.ndarray, lon: np.ndarray) -> tuple:
    """Convert GPS coordinates to XY meters using equirectangular projection.

    CORRECTED: Convert to radians FIRST, then compute reference point.
    Memory-optimized to avoid large intermediate arrays.
    """
    # Convert to float32 for memory efficiency (sufficient precision for GPS)
    lat = lat.astype(np.float32, copy=False)
    lon = lon.astype(np.float32, copy=False)

    # Compute reference point from degrees (single values, no memory issue)
    lat0_deg = np.mean(lat)
    lon0_deg = np.mean(lon)

    # Convert reference points to radians (just two scalars)
    lat0 = np.deg2rad(lat0_deg)
    lon0 = np.deg2rad(lon0_deg)

    # Earth radius
    R = np.float32(6371000.0)

    # Degree to radian conversion factor
    deg2rad = np.float32(np.pi / 180.0)

    # Project to XY directly without creating intermediate radian arrays
    # x = (lon_rad - lon0) * cos(lat0) * R
    # y = (lat_rad - lat0) * R
    cos_lat0 = np.float32(np.cos(lat0))

    x = ((lon - lon0_deg) * deg2rad * cos_lat0 * R).astype(np.float32)
    y = ((lat - lat0_deg) * deg2rad * R).astype(np.float32)

    return x, y
