"""Main preprocessing script - process all vehicles and save trajectories."""

import json
import os
import sys
import numpy as np
import pandas as pd

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from processing.load_raw_data import load_telemetry, get_vehicle_ids, extract_signals, gps_to_xy
from processing.time_alignment import detect_race_start, align_time
from processing.interpolate_trajectories import interpolate_trajectory
from processing.generate_racing_line import compute_racing_line
from processing.generate_per_car_racing_lines import compute_per_car_racing_line

# Import section compare processing for canonical line and fastest laps
try:
    from processing.section_compare_processing import run_section_compare_processing
    SECTION_COMPARE_AVAILABLE = True
except ImportError as e:
    SECTION_COMPARE_AVAILABLE = False
    print(f"Section compare processing not available: {e}")


def generate_all_trajectories(csv_path: str, output_dir: str, progress_callback=None):
    """Process all vehicles and save trajectories.

    Args:
        csv_path: Path to raw telemetry CSV
        output_dir: Output directory (e.g., 'data/processed')
        progress_callback: Optional callback(message, percent) for progress reporting
    """
    def report_progress(message, current_job, total_jobs):
        """Report progress with job counter."""
        percent = current_job / total_jobs if total_jobs > 0 else 0
        progress_msg = f"{message} ({current_job}/{total_jobs})"
        print(progress_msg)
        if progress_callback:
            progress_callback(progress_msg, percent)

    # Create output directories
    trajectories_dir = os.path.join(output_dir, 'trajectories')
    os.makedirs(trajectories_dir, exist_ok=True)

    # Job 1: Load raw data
    current_job = 1
    # Calculate total jobs after we know vehicle count
    # For now, report loading
    if progress_callback:
        progress_callback("Loading telemetry data...", 0.0)

    df = load_telemetry(csv_path)
    vehicle_ids = get_vehicle_ids(df)
    num_vehicles = len(vehicle_ids)

    # Calculate total jobs:
    # 1 (load) + 1 (count) + N*5 (per-vehicle processing) + 1 (racing line) + N (per-car lines) + 1 (metadata)
    # = 3 + 6N
    total_jobs = 3 + (num_vehicles * 6)

    # Job 2: Report vehicle count
    current_job = 2
    report_progress(f"Found {num_vehicles} vehicles", current_job, total_jobs)

    print(f"Found {len(vehicle_ids)} vehicles")

    trajectories = {}
    bounds = {'x_min': np.inf, 'x_max': -np.inf, 'y_min': np.inf, 'y_max': -np.inf}
    max_duration = 0

    for i, car_id in enumerate(vehicle_ids):
        print(f"Processing {car_id}...")
        vehicle_base_job = 2 + (i * 5)  # Jobs 3-7 for first vehicle, 8-12 for second, etc.

        try:
            # Step 1: Extract signals
            current_job = vehicle_base_job + 1
            report_progress(f"{car_id} - Extracting signals", current_job, total_jobs)
            signals_df = extract_signals(df, car_id)

            if len(signals_df) < 100:
                print(f"  Skipping {car_id}: insufficient data ({len(signals_df)} rows)")
                # Still count the remaining jobs for this vehicle
                current_job = vehicle_base_job + 5
                continue

            # Step 2: Convert GPS to XY
            current_job = vehicle_base_job + 2
            report_progress(f"{car_id} - Converting GPS coordinates", current_job, total_jobs)
            x, y = gps_to_xy(signals_df['lat'].values, signals_df['lon'].values)
            signals_df['x'] = x
            signals_df['y'] = y

            # Step 3: Detect race start and align time
            current_job = vehicle_base_job + 3
            report_progress(f"{car_id} - Detecting race start", current_job, total_jobs)
            race_start = detect_race_start(signals_df)
            signals_df = align_time(signals_df, race_start)

            if len(signals_df) < 100:
                print(f"  Skipping {car_id}: insufficient data after alignment")
                current_job = vehicle_base_job + 5
                continue

            # Step 4: Interpolate to 10ms grid
            current_job = vehicle_base_job + 4
            report_progress(f"{car_id} - Interpolating trajectory", current_job, total_jobs)
            trajectory, time_grid = interpolate_trajectory(signals_df)

            if trajectory is None:
                print(f"  Skipping {car_id}: interpolation failed")
                current_job = vehicle_base_job + 5
                continue

            # Step 5: Save trajectory
            current_job = vehicle_base_job + 5
            traj_path = os.path.join(trajectories_dir, f'{car_id}.npy')
            np.save(traj_path, trajectory)
            trajectories[car_id] = trajectory

            # Update bounds
            bounds['x_min'] = min(bounds['x_min'], float(trajectory[:, 0].min()))
            bounds['x_max'] = max(bounds['x_max'], float(trajectory[:, 0].max()))
            bounds['y_min'] = min(bounds['y_min'], float(trajectory[:, 1].min()))
            bounds['y_max'] = max(bounds['y_max'], float(trajectory[:, 1].max()))

            # Track max duration (10ms per sample)
            duration_ms = len(trajectory) * 10
            max_duration = max(max_duration, duration_ms)

            report_progress(f"{car_id} - Saved {len(trajectory)} samples", current_job, total_jobs)
            print(f"  Saved {car_id}: {len(trajectory)} samples, {duration_ms/1000:.1f}s")

        except Exception as e:
            print(f"  Error processing {car_id}: {e}")
            continue

    if len(trajectories) == 0:
        print("ERROR: No vehicles processed successfully")
        return None

    # Calculate job number for racing line phase
    # After all vehicles: 2 + (num_vehicles * 5)
    racing_line_job = 2 + (num_vehicles * 5) + 1

    # Generate racing line (verified method)
    print("\nGenerating racing line...")
    report_progress("Generating global racing line", racing_line_job, total_jobs)
    racing_line = compute_racing_line(trajectories, n_points=1500)
    racing_line_path = os.path.join(output_dir, 'racing_line.npy')
    np.save(racing_line_path, racing_line)
    print(f"Saved racing line: {len(racing_line)} points")

    # Generate per-car racing lines (30,000 points)
    print("\nGenerating per-car racing lines...")
    racing_lines_dir = os.path.join(output_dir, 'racing_lines')
    os.makedirs(racing_lines_dir, exist_ok=True)

    racing_line_metadata = {}
    processed_vehicles = list(trajectories.keys())
    for j, car_id in enumerate(processed_vehicles):
        current_job = racing_line_job + 1 + j
        report_progress(f"Generating racing line for {car_id}", current_job, total_jobs)
        try:
            racing_line_car, lap_length = compute_per_car_racing_line(trajectories[car_id], n_points=30000)
            save_path = os.path.join(racing_lines_dir, f'{car_id}_racing_line.npy')
            np.save(save_path, racing_line_car)
            racing_line_metadata[car_id] = {'lap_length_m': float(lap_length)}
        except Exception as e:
            print(f"  Error generating racing line for {car_id}: {e}")
            continue

    print(f"Saved per-car racing lines for {len(racing_line_metadata)} vehicles")

    # Assign colors
    colors = {}
    color_palette = [
        [255, 68, 68],    # Red
        [68, 255, 68],    # Green
        [68, 68, 255],    # Blue
        [255, 255, 68],   # Yellow
        [255, 68, 255],   # Magenta
        [68, 255, 255],   # Cyan
        [255, 136, 68],   # Orange
        [136, 255, 68],   # Lime
        [255, 136, 255],  # Pink
        [136, 68, 255],   # Purple
        [255, 200, 68],   # Gold
        [68, 200, 255],   # Sky blue
        [200, 68, 255],   # Violet
        [255, 68, 136],   # Rose
        [68, 255, 136],   # Mint
        [136, 136, 255],  # Periwinkle
        [255, 136, 136],  # Salmon
        [136, 255, 255],  # Aqua
    ]
    for i, car_id in enumerate(trajectories.keys()):
        colors[car_id] = color_palette[i % len(color_palette)]

    # Save metadata (directly in data/processed/)
    # Final job: save metadata
    report_progress("Saving metadata", total_jobs, total_jobs)

    metadata = {
        'bounds': bounds,
        'total_duration_ms': int(max_duration),
        'sample_rate_ms': 10,
        'car_ids': list(trajectories.keys()),
        'colors': colors,
        'per_car_racing_lines': True,
        'racing_line_points': 30000,
        'racing_line_metadata': racing_line_metadata,
        'trajectory_columns': 11,
        'separate_brake_channels': True
    }

    metadata_path = os.path.join(output_dir, 'metadata.json')
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)

    print(f"\n{'='*60}")
    print(f"TRAJECTORY PROCESSING COMPLETE")
    print(f"{'='*60}")
    print(f"Processed: {len(trajectories)} vehicles")
    print(f"Duration: {max_duration/1000:.1f} seconds")
    print(f"Bounds: x=[{bounds['x_min']:.1f}, {bounds['x_max']:.1f}], y=[{bounds['y_min']:.1f}, {bounds['y_max']:.1f}]")
    print(f"Output: {output_dir}")

    # Run section compare processing for canonical line and fastest laps
    if SECTION_COMPARE_AVAILABLE:
        print(f"\n{'='*60}")
        print("RUNNING SECTION COMPARE PROCESSING")
        print(f"{'='*60}")

        if progress_callback:
            progress_callback("Running section compare processing...", 0.85)

        try:
            canonical_line, stats = run_section_compare_processing(
                raw_csv_path=csv_path,
                output_dir=output_dir,
                n_sectors=3
            )

            print(f"\nSection compare complete:")
            print(f"  Track length: {stats.track_length_m:.1f} m")
            print(f"  Ideal lap time: {stats.ideal_lap_time_s:.3f} s")
            print(f"  Fastest lap exports: {stats.fastest_lap_exports}")
            print(f"  Per-car exports: {stats.per_car_exports}")

            if progress_callback:
                progress_callback("Section compare processing complete", 0.95)

        except Exception as e:
            print(f"Error in section compare processing: {e}")
            import traceback
            traceback.print_exc()
    else:
        print("\nSkipping section compare processing (not available)")

    print(f"\n{'='*60}")
    print(f"ALL PREPROCESSING COMPLETE")
    print(f"{'='*60}")

    return metadata


if __name__ == '__main__':
    import argparse

    parser = argparse.ArgumentParser(description='Generate trajectory files from raw telemetry')
    parser.add_argument('--input', required=True, help='Path to raw telemetry CSV')
    parser.add_argument('--output', default='data/processed', help='Output directory')

    args = parser.parse_args()

    generate_all_trajectories(args.input, args.output)
