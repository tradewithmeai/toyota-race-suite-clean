"""
Trail generation pipeline for delta speed traces.

Generates 15-second trailing delta speed traces for each car's fastest lap,
mapped to the canonical racing line. Each point carries delta speed vs reference
and delta speed vs ideal.

Usage:
    from processing.trail_generation import generate_all_trails, load_canonical_line

    canonical_line = load_canonical_line()
    canon_tree = build_canonical_kdtree(canonical_line)
    ref_speed_ms = canonical_line["ref_speed_ms"].to_numpy()
    ideal_speed_ms = canonical_line["ideal_speed_ms"].to_numpy()

    meta_df = generate_all_trails(canonical_line, canon_tree, ref_speed_ms, ideal_speed_ms)
"""

import os
import glob
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree
import matplotlib.pyplot as plt


def load_canonical_line(output_dir: str = "outputs") -> pd.DataFrame:
    """
    Load and merge canonical racing line data from disk.

    Loads three CSVs and merges them on dist_m, being careful to avoid
    duplicate columns (_x/_y suffixes).

    Args:
        output_dir: Directory containing the output CSVs

    Returns:
        DataFrame with columns: dist_m, x_m, y_m, curvature,
        ref_speed_ms, ideal_speed_ms, ideal_time_s

    Raises:
        FileNotFoundError: If any required CSV is missing
    """
    canonical_path = os.path.join(output_dir, "canonical_racing_line.csv")
    speed_path = os.path.join(output_dir, "speed_profile.csv")
    ideal_path = os.path.join(output_dir, "ideal_lap_profile.csv")

    # Check files exist
    for path in [canonical_path, speed_path, ideal_path]:
        if not os.path.exists(path):
            raise FileNotFoundError(f"Required file not found: {path}")

    # Load canonical geometry
    canonical = pd.read_csv(canonical_path)

    # Load speed profile - select only needed columns to avoid duplicates
    speed_prof = pd.read_csv(speed_path)[["dist_m", "ref_speed_ms"]]

    # Load ideal profile - select only needed columns to avoid duplicates
    ideal_prof = pd.read_csv(ideal_path)[["dist_m", "ideal_speed_ms", "ideal_time_s"]]

    # Merge on dist_m
    canonical_line = (canonical
        .merge(speed_prof, on="dist_m", how="left")
        .merge(ideal_prof, on="dist_m", how="left"))

    # Validate required columns
    required = ["dist_m", "x_m", "y_m", "curvature", "ref_speed_ms", "ideal_speed_ms"]
    missing = [col for col in required if col not in canonical_line.columns]
    if missing:
        raise ValueError(f"Canonical line missing required columns: {missing}")

    return canonical_line


def build_canonical_kdtree(canonical_line: pd.DataFrame) -> cKDTree:
    """
    Build a KDTree over canonical XY coordinates for fast nearest-neighbor queries.

    Args:
        canonical_line: DataFrame with x_m, y_m columns

    Returns:
        cKDTree built from (N_POINTS, 2) array of XY coordinates
    """
    canon_xy = canonical_line[["x_m", "y_m"]].to_numpy()
    canon_tree = cKDTree(canon_xy)
    return canon_tree


def load_fastest_lap_path(vehicle_id: str, output_dir: str = "outputs") -> str:
    """
    Locate the fastest-lap CSV file for a given vehicle.

    Args:
        vehicle_id: Vehicle identifier (e.g., "GR86-016-55")
        output_dir: Base output directory

    Returns:
        Path to the fastest lap CSV file

    Raises:
        FileNotFoundError: If no matching file is found
    """
    pattern = os.path.join(output_dir, "fastest_laps", "lap_csv",
                          f"fastest_lap_{vehicle_id}_lap*.csv")
    matches = glob.glob(pattern)

    if len(matches) == 0:
        raise FileNotFoundError(
            f"No fastest lap CSV found for vehicle {vehicle_id}. "
            f"Pattern: {pattern}"
        )

    # If multiple matches (shouldn't happen), sort and take first for determinism
    if len(matches) > 1:
        matches.sort()

    return matches[0]


def project_lap_to_canonical(
    lap_csv_path: str,
    canonical_line: pd.DataFrame,
    canon_tree: cKDTree,
    ref_speed_ms: np.ndarray,
    ideal_speed_ms: np.ndarray
) -> pd.DataFrame:
    """
    Project a fastest-lap CSV onto the canonical racing line.

    For each point in the lap, finds the nearest point on the canonical line
    and computes delta speeds vs reference and ideal.

    Args:
        lap_csv_path: Path to the fastest lap CSV
        canonical_line: Canonical racing line DataFrame
        canon_tree: KDTree built from canonical XY coordinates
        ref_speed_ms: Reference speed array aligned to canonical_line
        ideal_speed_ms: Ideal speed array aligned to canonical_line

    Returns:
        DataFrame with original lap data plus projection info and deltas

    Raises:
        ValueError: If required columns are missing or all rows have NaT timestamps
    """
    basename = os.path.basename(lap_csv_path)

    # Load lap CSV
    lap_df = pd.read_csv(lap_csv_path)

    # Check required columns
    required_cols = ["timestamp_dt", "dist_m", "x_m", "y_m", "speed_ms"]
    missing = [col for col in required_cols if col not in lap_df.columns]
    if missing:
        raise ValueError(
            f"Lap CSV {basename} missing required columns: {missing}. "
            f"Do not recompute speed_ms here; it should already exist."
        )

    # Parse timestamp_dt if not already datetime
    if not pd.api.types.is_datetime64_any_dtype(lap_df["timestamp_dt"]):
        lap_df["timestamp_dt"] = pd.to_datetime(lap_df["timestamp_dt"], errors="coerce")

    # Handle NaT values - drop with warning, don't fail
    n_nat = lap_df["timestamp_dt"].isna().sum()
    if n_nat > 0:
        print(f"[project_lap_to_canonical] Dropped {n_nat} rows with NaT timestamp_dt in {basename}")
        lap_df = lap_df[lap_df["timestamp_dt"].notna()].copy()

    if lap_df.empty:
        raise ValueError(f"All rows dropped for NaT timestamps in {basename}")

    # Sort by time
    lap_df = lap_df.sort_values("timestamp_dt").reset_index(drop=True)

    # Extract XY and query nearest canonical points
    xy = lap_df[["x_m", "y_m"]].to_numpy()
    dists, idx = canon_tree.query(xy)

    # Attach canonical projection info
    lap_df["canon_idx"] = idx
    lap_df["canonical_dist_m"] = canonical_line["dist_m"].to_numpy()[idx]
    lap_df["ref_speed_ms_at_point"] = ref_speed_ms[idx]
    lap_df["ideal_speed_ms_at_point"] = ideal_speed_ms[idx]

    # Compute deltas
    lap_df["delta_vs_ref_ms"] = lap_df["speed_ms"] - lap_df["ref_speed_ms_at_point"]
    lap_df["delta_vs_ideal_ms"] = lap_df["speed_ms"] - lap_df["ideal_speed_ms_at_point"]

    return lap_df


def build_trail_for_car(
    vehicle_id: str,
    canonical_line: pd.DataFrame,
    canon_tree: cKDTree,
    ref_speed_ms: np.ndarray,
    ideal_speed_ms: np.ndarray,
    trail_seconds: float = 15.0,
    compare: str = "ref",
    output_dir: str = "outputs"
) -> tuple:
    """
    Build the trailing delta-speed trace for one vehicle's fastest lap.

    Args:
        vehicle_id: Vehicle identifier
        canonical_line: Canonical racing line DataFrame
        canon_tree: KDTree for canonical XY
        ref_speed_ms: Reference speed array
        ideal_speed_ms: Ideal speed array
        trail_seconds: Duration of trail to extract (default 15s)
        compare: "ref" or "ideal" for delta calculation
        output_dir: Base output directory

    Returns:
        Tuple of (trail_df, label) where label describes the comparison

    Raises:
        ValueError: If compare is invalid or lap duration is non-positive
        FileNotFoundError: If no fastest lap exists for vehicle
    """
    # Resolve and project the car's fastest lap
    lap_path = load_fastest_lap_path(vehicle_id, output_dir)
    lap_df = project_lap_to_canonical(
        lap_path, canonical_line, canon_tree, ref_speed_ms, ideal_speed_ms
    )

    # Compute relative time from lap start
    t0 = lap_df["timestamp_dt"].iloc[0]
    lap_df["t_rel_s"] = (lap_df["timestamp_dt"] - t0).dt.total_seconds()

    # Select last trail_seconds
    t_max = lap_df["t_rel_s"].max()
    if t_max <= 0:
        raise ValueError(f"Non-positive lap duration for {vehicle_id}: {t_max}s")

    mask = lap_df["t_rel_s"] >= (t_max - trail_seconds)
    trail_df = lap_df.loc[mask].copy()

    # Fallback if trail is empty (very short lap)
    if trail_df.empty:
        trail_df = lap_df.tail(50).copy()
        print(f"[build_trail_for_car] Using last 50 samples for {vehicle_id} (lap < {trail_seconds}s)")

    # Compute delta speed metric for coloring
    if compare == "ref":
        trail_df["delta_kmh"] = trail_df["delta_vs_ref_ms"] * 3.6
        label = "Δ vs ref (km/h)"
    elif compare == "ideal":
        trail_df["delta_kmh"] = trail_df["delta_vs_ideal_ms"] * 3.6
        label = "Δ vs ideal (km/h)"
    else:
        raise ValueError(f"compare must be 'ref' or 'ideal', got '{compare}'")

    # Add vehicle_id column
    trail_df["vehicle_id"] = vehicle_id

    return trail_df, label


def save_trail_for_car(
    vehicle_id: str,
    canonical_line: pd.DataFrame,
    canon_tree: cKDTree,
    ref_speed_ms: np.ndarray,
    ideal_speed_ms: np.ndarray,
    trail_seconds: float = 15.0,
    out_dir: str = "outputs/trails",
    compare: str = "ref",
    output_dir: str = "outputs"
) -> tuple:
    """
    Build and save the trailing delta-speed trace for one vehicle.

    Args:
        vehicle_id: Vehicle identifier
        canonical_line: Canonical racing line DataFrame
        canon_tree: KDTree for canonical XY
        ref_speed_ms: Reference speed array
        ideal_speed_ms: Ideal speed array
        trail_seconds: Duration of trail (default 15s)
        out_dir: Directory for trail CSVs
        compare: "ref" or "ideal"
        output_dir: Base output directory for fastest laps

    Returns:
        Tuple of (trail_df, path) for metadata collection
    """
    # Build trail
    trail_df, label = build_trail_for_car(
        vehicle_id, canonical_line, canon_tree, ref_speed_ms, ideal_speed_ms,
        trail_seconds, compare, output_dir
    )

    # Ensure output directory exists
    os.makedirs(out_dir, exist_ok=True)

    # Build filename (replace problematic chars with underscore)
    safe_vid = vehicle_id.replace("/", "_").replace("\\", "_")
    filename = f"trail_{safe_vid}_fastestlap_{int(trail_seconds)}s_{compare}.csv"
    path = os.path.join(out_dir, filename)

    # Select columns to save
    save_cols = [
        "vehicle_id",
        "timestamp_dt",
        "t_rel_s",
        "x_m", "y_m",
        "canonical_dist_m",
        "speed_ms",
        "ref_speed_ms_at_point",
        "ideal_speed_ms_at_point",
        "delta_vs_ref_ms",
        "delta_vs_ideal_ms",
        "delta_kmh"
    ]

    # Only include columns that exist
    save_cols = [c for c in save_cols if c in trail_df.columns]
    trail_df[save_cols].to_csv(path, index=False)

    print(f"Saved {len(trail_df)} trail points for {vehicle_id} to {path}")

    return trail_df, path


def generate_all_trails(
    canonical_line: pd.DataFrame,
    canon_tree: cKDTree,
    ref_speed_ms: np.ndarray,
    ideal_speed_ms: np.ndarray,
    vehicle_ids: list = None,
    trail_seconds: float = 15.0,
    compare: str = "ref",
    out_dir: str = "outputs/trails",
    output_dir: str = "outputs"
) -> pd.DataFrame:
    """
    Generate and save trails for all vehicles with fastest laps.

    Args:
        canonical_line: Canonical racing line DataFrame
        canon_tree: KDTree for canonical XY
        ref_speed_ms: Reference speed array
        ideal_speed_ms: Ideal speed array
        vehicle_ids: List of vehicle IDs (auto-detected if None)
        trail_seconds: Duration of trail (default 15s)
        compare: "ref" or "ideal"
        out_dir: Directory for trail CSVs
        output_dir: Base output directory

    Returns:
        DataFrame with metadata for all generated trails
    """
    # Auto-detect vehicle IDs if not provided
    if vehicle_ids is None:
        pattern = os.path.join(output_dir, "fastest_laps", "lap_csv", "fastest_lap_*.csv")
        files = glob.glob(pattern)

        vehicle_ids = []
        for f in files:
            base = os.path.basename(f)
            # Parse: fastest_lap_<vehicle_id>_lap<NN>.csv
            # Remove prefix
            inner = base[len("fastest_lap_"):]
            # Split on _lap to get vehicle_id
            vid = inner.split("_lap")[0]
            if vid not in vehicle_ids:
                vehicle_ids.append(vid)

        vehicle_ids.sort()
        print(f"Auto-detected {len(vehicle_ids)} vehicles with fastest laps")

    # Generate trails for each vehicle
    records = []
    for vid in vehicle_ids:
        try:
            trail_df, path = save_trail_for_car(
                vid, canonical_line, canon_tree, ref_speed_ms, ideal_speed_ms,
                trail_seconds, out_dir, compare, output_dir
            )
            records.append({
                "vehicle_id": vid,
                "trail_path": path,
                "trail_seconds": trail_seconds,
                "compare": compare,
                "n_points": len(trail_df)
            })
        except FileNotFoundError as e:
            print(f"[generate_all_trails] Skipping {vid}: {e}")
        except ValueError as e:
            print(f"[generate_all_trails] Skipping {vid}: {e}")

    # Save index
    meta_df = pd.DataFrame(records)
    os.makedirs(out_dir, exist_ok=True)
    meta_path = os.path.join(out_dir, f"trail_index_{int(trail_seconds)}s_{compare}.csv")
    meta_df.to_csv(meta_path, index=False)

    print(f"\nGenerated {len(records)} trails")
    print(f"Index saved to: {meta_path}")

    return meta_df


def plot_trail_debug(
    trail_df: pd.DataFrame,
    vehicle_id: str,
    trail_seconds: float,
    compare_label: str
) -> None:
    """
    Debug visualization of a trail colored by delta speed.

    Args:
        trail_df: Trail DataFrame with x_m, y_m, delta_kmh columns
        vehicle_id: Vehicle identifier for title
        trail_seconds: Duration used for title
        compare_label: Label describing comparison (e.g., "Δ vs ref (km/h)")
    """
    plt.figure(figsize=(10, 10))

    scatter = plt.scatter(
        trail_df["x_m"],
        trail_df["y_m"],
        c=trail_df["delta_kmh"],
        cmap="coolwarm",
        vmin=-30,
        vmax=30,
        s=20,
        alpha=0.8
    )

    plt.colorbar(scatter, label=compare_label)
    plt.title(f"{vehicle_id} – last {trail_seconds:.0f}s trail, {compare_label}")
    plt.xlabel("x_m (East)")
    plt.ylabel("y_m (North)")
    plt.axis("equal")
    plt.grid(True, alpha=0.3)
    plt.tight_layout()
    plt.show()


# Convenience function for quick testing
def test_trail_generation(vehicle_id: str = "GR86-016-55", output_dir: str = "outputs"):
    """
    Quick test of trail generation for a single vehicle.

    Args:
        vehicle_id: Vehicle to test
        output_dir: Base output directory
    """
    print(f"Testing trail generation for {vehicle_id}...")

    # Load canonical line
    canonical_line = load_canonical_line(output_dir)
    print(f"Loaded canonical line: {len(canonical_line)} points")

    # Build KDTree
    canon_tree = build_canonical_kdtree(canonical_line)

    # Extract speed arrays
    ref_speed_ms = canonical_line["ref_speed_ms"].to_numpy()
    ideal_speed_ms = canonical_line["ideal_speed_ms"].to_numpy()

    # Build trail
    trail_df, label = build_trail_for_car(
        vehicle_id, canonical_line, canon_tree, ref_speed_ms, ideal_speed_ms,
        trail_seconds=15.0, compare="ref", output_dir=output_dir
    )

    # Validate
    assert not trail_df.empty, "Trail is empty"
    duration = trail_df["t_rel_s"].max() - trail_df["t_rel_s"].min()
    assert duration <= 16.0, f"Trail duration {duration}s exceeds 16s"

    for col in ["delta_vs_ref_ms", "delta_vs_ideal_ms", "delta_kmh"]:
        assert col in trail_df.columns, f"Missing column: {col}"

    print(f"Trail has {len(trail_df)} points, duration {duration:.1f}s")
    print(f"Delta range: {trail_df['delta_kmh'].min():.1f} to {trail_df['delta_kmh'].max():.1f} km/h")
    print("Test passed!")

    return trail_df, label
