"""Race start detection and time alignment using 3-second moving window."""

import numpy as np
import pandas as pd


def detect_race_start(df: pd.DataFrame) -> pd.Timestamp:
    """Detect race start using 3-second moving window.

    CORRECTED: Find first lapdist reset after 3 seconds of continuous movement.
    """
    df = df.copy()

    # Convert timestamp to datetime
    df['timestamp_dt'] = pd.to_datetime(df['timestamp'])

    # Find lapdist resets
    df['lapdist_diff'] = df['lapdist'].diff()
    reset_mask = df['lapdist_diff'] < -1000
    reset_indices = df[reset_mask].index.tolist()

    if len(reset_indices) == 0:
        # No resets found, use first timestamp
        return df['timestamp_dt'].iloc[0]

    # Find intervals where speed > 20 mph for at least 3 continuous seconds
    df['is_moving'] = df['speed'] > 20

    # Build list of timestamps where 3-second moving window is satisfied
    moving_window_starts = []
    window_size = pd.Timedelta(seconds=3)

    timestamps = df['timestamp_dt'].values
    is_moving = df['is_moving'].values

    for i in range(len(df)):
        window_start = timestamps[i]
        window_end = window_start + window_size

        # Get all points in window
        window_mask = (timestamps >= window_start) & (timestamps < window_end)
        window_moving = is_moving[window_mask]

        if len(window_moving) > 0 and window_moving.all():
            moving_window_starts.append(pd.Timestamp(window_start))

    # Find first reset that occurs after a 3-second moving window
    reset_times = df.loc[reset_indices, 'timestamp_dt'].values

    for reset_time in reset_times:
        reset_ts = pd.Timestamp(reset_time)
        for window_start in moving_window_starts:
            if reset_ts >= window_start:
                return reset_ts

    # Fallback: first reset where speed > 20
    for idx in reset_indices:
        if df.loc[idx, 'speed'] > 20:
            return df.loc[idx, 'timestamp_dt']

    # Last fallback: first reset
    return df.loc[reset_indices[0], 'timestamp_dt']


def align_time(df: pd.DataFrame, race_start: pd.Timestamp) -> pd.DataFrame:
    """Compute relative time from race start."""
    df = df.copy()

    # Convert timestamp to datetime if not already
    if 'timestamp_dt' not in df.columns:
        df['timestamp_dt'] = pd.to_datetime(df['timestamp'])

    # Ensure both are timezone-naive for subtraction
    if df['timestamp_dt'].dt.tz is not None:
        df['timestamp_dt'] = df['timestamp_dt'].dt.tz_localize(None)

    if race_start.tz is not None:
        race_start = race_start.tz_localize(None)

    # Compute relative time in seconds
    df['rel_time'] = (df['timestamp_dt'] - race_start).dt.total_seconds()

    # Filter to only positive times (after race start)
    df = df[df['rel_time'] >= 0].copy()

    return df
