"""World model - load trajectories and manage simulation state."""

import json
import os
import numpy as np
import pandas as pd
from scipy.spatial import cKDTree  # PHASE 3: For spatial deviation queries
from scipy.interpolate import interp1d
from app.color_config import color_config


class WorldModel:
    """Manages all trajectory data and simulation state."""

    # Theme definitions
    THEMES = {
        'dark': {
            'bg': (20, 20, 20),
            'panel_bg': (40, 40, 40),
            'panel_bg_alpha': (40, 40, 40, 200),
            'header_bg': (60, 60, 60, 220),
            'text': (255, 255, 255),
            'text_secondary': (200, 200, 200),
            'text_muted': (150, 150, 150),
            'accent': (100, 255, 100),
            'timer_bg': (0, 0, 0, 180),
        },
        'light': {
            'bg': (200, 200, 200),
            'panel_bg': (245, 245, 245),
            'panel_bg_alpha': (245, 245, 245, 230),
            'header_bg': (230, 230, 230, 240),
            'text': (20, 20, 20),
            'text_secondary': (60, 60, 60),
            'text_muted': (100, 100, 100),
            'accent': (0, 180, 0),
            'timer_bg': (255, 255, 255, 200),
        }
    }

    def __init__(self, data_dir: str):
        self.trajectories = {}  # car_id -> np.ndarray(N, 11) = [x, y, speed, lapdist, brake_front, brake_rear, gear, steering_deg, heading_rad, accel_norm, lap]

        # Theme setting
        self.current_theme = 'dark'  # 'dark' or 'light'
        self.racing_line = None  # Track centerline
        self.global_racing_line_tree = None  # cKDTree for global racing line
        self.per_car_racing_lines = {}  # car_id -> np.ndarray(30000, 2) = [x, y]
        self.lap_lengths = {}  # car_id -> float (lap length in meters)
        self.racing_line_trees = {}  # car_id -> cKDTree for spatial queries (PHASE 3)
        self.car_ids = []
        self.colors = {}
        self.current_time_ms = 0
        self.total_duration_ms = 0
        self.bounds = {}
        self.data_dir = data_dir

        # Animation control
        self.is_paused = False  # Track click pause state

        # Driving style deviation (separate from trajectories - PATCH 6)
        self.deviation_offsets = {}  # car_id -> np.ndarray(N, 2) for x, y offset
        self.driving_mode = "Toyota"

        # Display options for visualization
        self.selected_car_ids = []  # Empty = all visible
        self.hidden_car_ids = []  # Cars to completely hide from rendering
        self.highlight_selected = True
        self.trail_mode = 'off'  # off, last_lap, fade_3s, fade_5s, fade_10s
        self.show_braking_overlay = False

        # Visual effects state (per-car effects)
        self.show_lateral_diff = False  # Deviation bars
        self.show_lateral_diff_all = False  # Apply to all cars
        self.lateral_diff_reference = 'racing_line'  # racing_line, global_racing_line, individual
        self.show_circle_glow = False  # Brake glow (same as show_braking_overlay)
        self.show_circle_glow_all = False
        self.show_circle_centre = False  # Placeholder for future
        self.show_circle_centre_all = False
        self.show_trail = False  # Trail visualization
        self.show_trail_all = False
        self.show_steering_angle = False  # Steering arrow
        self.show_steering_angle_all = False

        # Delta speed trail data (loaded from outputs/trails/)
        self.trail_data = {}  # car_id -> DataFrame with delta speed trail

        # Track display options
        self.show_density_plot = True  # Density map background
        self.show_racing_line = True  # Racing line overlay
        self.show_track_outline = False  # Future: smoothed track boundary
        self.show_global_racing_line = False  # Global canonical racing line (neon green)

        # HUD display toggles - GLOBAL defaults (used when new car is selected)
        self.hud_show_speed = True
        self.hud_show_gear = True
        self.hud_show_brake = True
        self.hud_show_lap = True
        self.hud_show_time = True
        self.hud_show_position = True
        self.hud_show_deviation = False  # Shows when Lateral Diff enabled
        self.hud_show_steering = False  # Shows when Steering Angle enabled

        # HUD panel state (per-car)
        self.hud_collapsed = {}  # car_id -> bool (collapsed state)
        self.hud_order = []  # List of car_ids in display order
        self.hud_items_visible = {}  # car_id -> dict of {item_name: bool} for per-car visibility

        # Lap counting data (DEPRECATED - kept for backward compatibility with old 9-column trajectories)
        self.lap_data = {}  # car_id -> list of lap start indices

        # Sector analysis data
        self.sector_map = None  # Loaded from sector_map.json
        self.sector_boundaries = []  # [(start_dist, end_dist), ...]
        self.ideal_speed_profile = None  # DataFrame with dist_m, ideal_speed_ms
        self.canonical_racing_line = None  # DataFrame with dist_m, x_m, y_m, curvature
        self.track_length_m = 0.0
        self.ideal_lap_time_s = 0.0

        # Per-car sector timing
        self.car_sector_times = {}  # car_id -> {lap: [s1, s2, s3]}
        self.car_lap_times = {}  # car_id -> [lap1_time, lap2_time, ...]
        self.car_best_sectors = {}  # car_id -> [best_s1, best_s2, best_s3]
        self.overall_best_sectors = [float('inf'), float('inf'), float('inf')]

        # Sector display toggles
        self.show_sector_lines = False
        self.show_speed_comparison = False

        # HUD sector toggles
        self.hud_show_sector_times = True
        self.hud_show_current_lap = True
        self.hud_show_lap_delta = True
        self.hud_show_predicted_lap = True

    def get_theme(self):
        """Get the current theme color dictionary."""
        # Use ColorConfig for customizable themes
        return color_config.get_theme(self.current_theme)

    def toggle_theme(self):
        """Toggle between dark and light themes."""
        self.current_theme = 'light' if self.current_theme == 'dark' else 'dark'
        self._save_theme_preference()
        return self.current_theme

    def load_theme_preference(self):
        """Load theme preference from config file."""
        config_file = os.path.join(os.path.expanduser("~"), ".race_replay_config.json")
        try:
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)
                    saved_theme = config.get('theme', 'dark')
                    if saved_theme in self.THEMES:
                        self.current_theme = saved_theme
        except Exception as e:
            print(f"Error loading theme preference: {e}")

    def _save_theme_preference(self):
        """Save theme preference to config file."""
        config_file = os.path.join(os.path.expanduser("~"), ".race_replay_config.json")
        try:
            # Load existing config
            config = {}
            if os.path.exists(config_file):
                with open(config_file, 'r') as f:
                    config = json.load(f)

            # Update theme
            config['theme'] = self.current_theme

            # Save
            with open(config_file, 'w') as f:
                json.dump(config, f)
        except Exception as e:
            print(f"Error saving theme preference: {e}")

    def load_trajectories(self):
        """Load all .npy files and metadata."""
        # Load metadata
        metadata_path = os.path.join(self.data_dir, 'metadata.json')
        with open(metadata_path, 'r') as f:
            metadata = json.load(f)

        self.bounds = metadata['bounds']
        self.total_duration_ms = metadata['total_duration_ms']
        self.car_ids = metadata['car_ids']
        self.colors = {k: tuple(v) for k, v in metadata['colors'].items()}

        # Load trajectories
        trajectories_dir = os.path.join(self.data_dir, 'trajectories')
        for car_id in self.car_ids:
            traj_path = os.path.join(trajectories_dir, f'{car_id}.npy')
            traj = np.load(traj_path)
            self.trajectories[car_id] = traj

            # Initialize zero deviation (PATCH 6)
            self.deviation_offsets[car_id] = np.zeros((len(traj), 2))

            # Compute lap start indices
            self._compute_lap_data(car_id)

        # Load racing line
        racing_line_path = os.path.join(self.data_dir, 'racing_line.npy')
        self.racing_line = np.load(racing_line_path)

        # Build KD-tree for global racing line
        self.global_racing_line_tree = cKDTree(self.racing_line)
        print(f"Built KD-tree for global racing line ({len(self.racing_line)} points)")

        # Load per-car racing lines if available
        racing_lines_dir = os.path.join(self.data_dir, 'racing_lines')
        if metadata.get('per_car_racing_lines', False) and os.path.exists(racing_lines_dir):
            racing_line_meta = metadata.get('racing_line_metadata', {})

            for car_id in self.car_ids:
                rl_path = os.path.join(racing_lines_dir, f'{car_id}_racing_line.npy')
                if os.path.exists(rl_path):
                    self.per_car_racing_lines[car_id] = np.load(rl_path)
                    # Load lap length from metadata
                    if car_id in racing_line_meta:
                        self.lap_lengths[car_id] = racing_line_meta[car_id]['lap_length_m']

            # PHASE 3: Build KD-trees for spatial deviation queries
            for car_id, racing_line in self.per_car_racing_lines.items():
                self.racing_line_trees[car_id] = cKDTree(racing_line)

            print(f"Loaded per-car racing lines for {len(self.per_car_racing_lines)} vehicles")
            print(f"Built {len(self.racing_line_trees)} KD-trees for spatial deviation queries")

        print(f"Loaded {len(self.car_ids)} vehicles")
        print(f"Total duration: {self.total_duration_ms / 1000:.1f} seconds")

        # Compute track boundary from all GPS points
        self.track_boundary = self._compute_track_boundary()

        # Load sector analysis data
        self._load_sector_data()

        # Compute sector times for all cars
        self._compute_all_sector_times()

        # Load delta speed trail data
        self._load_trail_data()

    def _compute_track_boundary(self):
        """Create smooth outer boundary around all trajectory points."""
        from scipy.spatial import ConvexHull

        # Collect all GPS points from all trajectories
        all_points = []
        for car_id in self.car_ids:
            traj = self.trajectories[car_id]
            # Sample every 10th point to reduce computation (still plenty of points)
            sampled = traj[::10, 0:2]  # x, y columns
            all_points.extend(sampled)

        all_points = np.array(all_points)

        if len(all_points) < 3:
            print("Warning: Not enough points to compute track boundary")
            return None

        try:
            # Compute convex hull
            hull = ConvexHull(all_points)
            boundary_points = all_points[hull.vertices]

            # Sort points by angle to ensure proper ordering
            center = boundary_points.mean(axis=0)
            angles = np.arctan2(boundary_points[:, 1] - center[1],
                               boundary_points[:, 0] - center[0])
            sorted_indices = np.argsort(angles)
            boundary_points = boundary_points[sorted_indices]

            print(f"Computed track boundary with {len(boundary_points)} points")
            return boundary_points

        except Exception as e:
            print(f"Error computing track boundary: {e}")
            return None

    def _compute_lap_data(self, car_id: str):
        """Compute lap start indices for a car based on lapdist resets."""
        traj = self.trajectories[car_id]
        lapdist = traj[:, 3]

        lap_starts = [0]
        for i in range(1, len(lapdist)):
            if lapdist[i] < lapdist[i-1] - 100:  # Lap reset (>100m drop)
                lap_starts.append(i)

        self.lap_data[car_id] = lap_starts

    def _load_sector_data(self):
        """Load sector analysis data from outputs directory."""
        # Try to find outputs in parent directory first, then data_dir
        possible_paths = [
            os.path.join(os.path.dirname(self.data_dir), 'outputs'),
            os.path.join(self.data_dir, '..', 'outputs'),
            'outputs',
        ]

        outputs_dir = None
        for path in possible_paths:
            sector_map_path = os.path.join(path, 'sector_map.json')
            if os.path.exists(sector_map_path):
                outputs_dir = path
                break

        if outputs_dir is None:
            print("Sector analysis data not found - sector features disabled")
            return

        try:
            # Load sector map
            sector_map_path = os.path.join(outputs_dir, 'sector_map.json')
            with open(sector_map_path, 'r') as f:
                self.sector_map = json.load(f)

            self.track_length_m = self.sector_map['track_length_m']
            self.ideal_lap_time_s = self.sector_map['ideal_lap_time_s']

            # Extract sector boundaries
            self.sector_boundaries = []
            for sector in self.sector_map['sectors']:
                self.sector_boundaries.append((
                    sector['start_dist_m'],
                    sector['end_dist_m']
                ))

            print(f"Loaded sector map: {len(self.sector_boundaries)} sectors, "
                  f"track length {self.track_length_m:.1f}m")

            # Load speed profile
            speed_profile_path = os.path.join(outputs_dir, 'speed_profile.csv')
            if os.path.exists(speed_profile_path):
                self.ideal_speed_profile = pd.read_csv(speed_profile_path)
                print(f"Loaded speed profile: {len(self.ideal_speed_profile)} points")

            # Load canonical racing line with curvature
            canonical_path = os.path.join(outputs_dir, 'canonical_racing_line.csv')
            if os.path.exists(canonical_path):
                self.canonical_racing_line = pd.read_csv(canonical_path)
                print(f"Loaded canonical racing line: {len(self.canonical_racing_line)} points")

        except Exception as e:
            print(f"Error loading sector data: {e}")
            self.sector_map = None

    def _compute_all_sector_times(self):
        """Compute sector times for all cars from trajectory data."""
        if not self.sector_boundaries or len(self.sector_boundaries) == 0:
            return

        for car_id in self.car_ids:
            self._compute_car_sector_times(car_id)

        # Find overall best sectors
        for car_id in self.car_ids:
            if car_id in self.car_best_sectors:
                best = self.car_best_sectors[car_id]
                for i in range(len(self.overall_best_sectors)):
                    if best[i] < self.overall_best_sectors[i]:
                        self.overall_best_sectors[i] = best[i]

        print(f"Computed sector times for {len(self.car_sector_times)} cars")
        if self.overall_best_sectors[0] < float('inf'):
            print(f"Overall best sectors: S1={self.overall_best_sectors[0]:.3f}s, "
                  f"S2={self.overall_best_sectors[1]:.3f}s, "
                  f"S3={self.overall_best_sectors[2]:.3f}s")

    def _load_trail_data(self):
        """Load delta speed trail data from trails/ directory."""
        import glob

        print("=== Loading trail data ===")

        # Try to find trails directory - check multiple locations
        # Primary location: trails/ inside the data_dir (same as other processed data)
        # Fallback: outputs/trails for backwards compatibility with notebook runs
        possible_paths = [
            os.path.join(self.data_dir, 'trails'),  # Primary: same dir as trajectories
            os.path.join(os.path.dirname(self.data_dir), 'outputs', 'trails'),
            os.path.join(self.data_dir, '..', 'outputs', 'trails'),
            os.path.join(self.data_dir, '..', '..', 'outputs', 'trails'),  # Up two levels from data/processed
            os.path.join(self.data_dir, '..', '..', '..', 'outputs', 'trails'),  # Up three levels to toyota-test/outputs
            'outputs/trails',
            # Also try absolute path from src directory
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'outputs', 'trails'),
            # Try parent of project root (toyota-test/outputs)
            os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))), 'outputs', 'trails'),
        ]

        trails_dir = None
        for path in possible_paths:
            print(f"  Checking trail path: {path} -> exists: {os.path.exists(path)}")
            if os.path.exists(path):
                trails_dir = path
                break

        if trails_dir is None:
            print("Trail data directory not found - delta speed trails disabled")
            print(f"  data_dir was: {self.data_dir}")
            return

        print(f"Found trails directory: {trails_dir}")

        # Load trail CSVs for each car
        loaded_count = 0

        # Also try loading all available trail files and match by vehicle_id in filename
        all_trail_files = glob.glob(os.path.join(trails_dir, "trail_*_fastestlap_*.csv"))
        print(f"Found {len(all_trail_files)} trail files in {trails_dir}")

        # Build a mapping from vehicle_id to trail file
        trail_file_map = {}
        for trail_file in all_trail_files:
            basename = os.path.basename(trail_file)
            # Parse: trail_<vehicle_id>_fastestlap_<duration>s_<compare>.csv
            if basename.startswith("trail_") and "_fastestlap_" in basename:
                # Extract vehicle_id between "trail_" and "_fastestlap_"
                inner = basename[len("trail_"):]
                vid = inner.split("_fastestlap_")[0]
                trail_file_map[vid] = trail_file

        print(f"Trail file vehicle IDs: {list(trail_file_map.keys())[:5]}...")
        print(f"App car IDs: {self.car_ids[:5]}...")

        not_found = []
        for car_id in self.car_ids:
            # First try exact match
            trail_path = trail_file_map.get(car_id)

            # If no exact match, try pattern matching
            if not trail_path:
                patterns = [
                    os.path.join(trails_dir, f"trail_{car_id}_fastestlap_*_ref.csv"),
                    os.path.join(trails_dir, f"trail_{car_id}_*.csv"),
                ]
                for pattern in patterns:
                    matches = glob.glob(pattern)
                    if matches:
                        trail_path = matches[0]
                        break

            if trail_path and os.path.exists(trail_path):
                try:
                    trail_df = pd.read_csv(trail_path)
                    # Validate required columns
                    required = ['x_m', 'y_m', 'delta_kmh']
                    if all(col in trail_df.columns for col in required):
                        self.trail_data[car_id] = trail_df
                        loaded_count += 1
                    else:
                        print(f"Trail CSV for {car_id} missing required columns: {trail_df.columns.tolist()}")
                except Exception as e:
                    print(f"Error loading trail for {car_id}: {e}")
            else:
                not_found.append(car_id)

        if not_found:
            print(f"No trail files found for {len(not_found)} cars: {not_found[:5]}...")

        if loaded_count > 0:
            print(f"Loaded delta speed trails for {loaded_count} vehicles")
        else:
            print("No delta speed trail data loaded")

    def get_delta_speed_trail(self, car_id: str) -> list:
        """
        Get delta speed trail data for a vehicle.

        Args:
            car_id: Vehicle identifier

        Returns:
            List of (x, y, delta_kmh) tuples, or empty list if no data
        """
        if car_id not in self.trail_data:
            return []

        trail_df = self.trail_data[car_id]
        return list(zip(
            trail_df['x_m'].values,
            trail_df['y_m'].values,
            trail_df['delta_kmh'].values
        ))

    def _compute_car_sector_times(self, car_id: str):
        """Compute sector times for a single car."""
        traj = self.trajectories[car_id]
        lap_starts = self.lap_data.get(car_id, [0])

        if len(lap_starts) < 2:
            return  # Need at least one complete lap

        self.car_sector_times[car_id] = {}
        self.car_lap_times[car_id] = []
        best_sectors = [float('inf'), float('inf'), float('inf')]

        num_sectors = len(self.sector_boundaries)

        for lap_idx in range(len(lap_starts) - 1):
            lap_start = lap_starts[lap_idx]
            lap_end = lap_starts[lap_idx + 1]
            lap_num = lap_idx + 1

            # Get lapdist and time for this lap
            lap_lapdist = traj[lap_start:lap_end, 3]
            lap_times_ms = np.arange(lap_start, lap_end) * 10  # 10ms per frame

            if len(lap_lapdist) < 10:
                continue

            # Compute sector times
            sector_times = []
            prev_sector_time = lap_times_ms[0]

            for sector_idx, (start_dist, end_dist) in enumerate(self.sector_boundaries):
                # Find first frame where lapdist crosses sector end
                sector_end_idx = None
                for i in range(len(lap_lapdist)):
                    if lap_lapdist[i] >= end_dist:
                        sector_end_idx = i
                        break

                if sector_end_idx is not None:
                    sector_time_ms = lap_times_ms[sector_end_idx] - prev_sector_time
                    sector_time_s = sector_time_ms / 1000.0
                    sector_times.append(sector_time_s)
                    prev_sector_time = lap_times_ms[sector_end_idx]

                    # Update best sector
                    if sector_time_s < best_sectors[sector_idx]:
                        best_sectors[sector_idx] = sector_time_s
                else:
                    sector_times.append(None)

            # Store if we got all sectors
            if len(sector_times) == num_sectors and all(t is not None for t in sector_times):
                self.car_sector_times[car_id][lap_num] = sector_times
                lap_time = sum(sector_times)
                self.car_lap_times[car_id].append(lap_time)

        self.car_best_sectors[car_id] = best_sectors

    def get_current_sector(self, car_id: str, time_ms: float = None) -> int:
        """Get which sector the car is currently in (1, 2, or 3)."""
        if not self.sector_boundaries:
            return 1

        if time_ms is None:
            time_ms = self.current_time_ms

        state = self.get_car_state(car_id, time_ms)
        lapdist = state['lapdist']

        for i, (start_dist, end_dist) in enumerate(self.sector_boundaries):
            if start_dist <= lapdist < end_dist:
                return i + 1

        return len(self.sector_boundaries)  # Last sector

    def get_current_sector_time(self, car_id: str) -> float:
        """Get time spent in current sector (in seconds)."""
        if not self.sector_boundaries:
            return 0.0

        traj = self.trajectories[car_id]
        current_idx = int(self.current_time_ms / 10)
        if current_idx >= len(traj):
            current_idx = len(traj) - 1

        current_lapdist = traj[current_idx, 3]
        current_sector = self.get_current_sector(car_id)
        sector_start_dist = self.sector_boundaries[current_sector - 1][0]

        # Search backwards to find when we entered this sector
        for i in range(current_idx, -1, -1):
            if traj[i, 3] < sector_start_dist:
                # Found sector entry point
                time_in_sector_ms = (current_idx - i) * 10
                return time_in_sector_ms / 1000.0

        return 0.0

    def get_best_lap_time(self, car_id: str) -> float:
        """Get best lap time for a car (in seconds)."""
        if car_id not in self.car_lap_times or not self.car_lap_times[car_id]:
            return float('inf')
        return min(self.car_lap_times[car_id])

    def get_current_lap_time(self, car_id: str) -> float:
        """Get time elapsed in current lap (in seconds)."""
        traj = self.trajectories[car_id]
        lap_starts = self.lap_data.get(car_id, [0])
        current_idx = int(self.current_time_ms / 10)

        if current_idx >= len(traj):
            current_idx = len(traj) - 1

        # Find current lap start
        current_lap_start = 0
        for lap_start in lap_starts:
            if lap_start <= current_idx:
                current_lap_start = lap_start
            else:
                break

        time_in_lap_ms = (current_idx - current_lap_start) * 10
        return time_in_lap_ms / 1000.0

    def get_sector_delta(self, car_id: str, sector: int) -> tuple:
        """Get delta to best sector time.

        Returns:
            (delta_to_personal, delta_to_overall, is_personal_best, is_overall_best)
        """
        if car_id not in self.car_best_sectors:
            return (0.0, 0.0, False, False)

        personal_best = self.car_best_sectors[car_id][sector - 1]
        overall_best = self.overall_best_sectors[sector - 1]

        # Get last completed sector time
        if car_id in self.car_sector_times:
            laps = sorted(self.car_sector_times[car_id].keys())
            if laps:
                last_lap = laps[-1]
                sectors = self.car_sector_times[car_id][last_lap]
                if sector <= len(sectors) and sectors[sector - 1] is not None:
                    current_time = sectors[sector - 1]
                    delta_personal = current_time - personal_best
                    delta_overall = current_time - overall_best
                    is_personal = abs(delta_personal) < 0.001
                    is_overall = abs(delta_overall) < 0.001
                    return (delta_personal, delta_overall, is_personal, is_overall)

        return (0.0, 0.0, False, False)

    def get_predicted_lap_time(self, car_id: str) -> float:
        """Get predicted lap time based on current sector pace."""
        if not self.sector_boundaries or car_id not in self.car_best_sectors:
            return 0.0

        current_sector = self.get_current_sector(car_id)
        current_lap_time = self.get_current_lap_time(car_id)

        # Add best sector times for remaining sectors
        predicted = current_lap_time
        for i in range(current_sector, len(self.sector_boundaries)):
            predicted += self.car_best_sectors[car_id][i]

        return predicted

    def get_ideal_speed_at_distance(self, distance_m: float) -> float:
        """Get ideal speed at a given track distance."""
        if self.ideal_speed_profile is None or len(self.ideal_speed_profile) == 0:
            return 0.0

        # Interpolate
        dist = self.ideal_speed_profile['dist_m'].to_numpy()
        speed = self.ideal_speed_profile['ideal_speed_ms'].to_numpy()

        if distance_m <= dist[0]:
            return float(speed[0])
        if distance_m >= dist[-1]:
            return float(speed[-1])

        # Find bracket
        idx = np.searchsorted(dist, distance_m)
        if idx == 0:
            return float(speed[0])

        # Linear interpolation
        t = (distance_m - dist[idx-1]) / (dist[idx] - dist[idx-1])
        return float(speed[idx-1] + t * (speed[idx] - speed[idx-1]))

    def get_sector_line_points(self, sector_idx: int) -> list:
        """Get x,y points for drawing sector boundary line on track.

        Returns list of (x, y) coordinates for the sector line perpendicular to track.
        """
        if self.canonical_racing_line is None or sector_idx >= len(self.sector_boundaries):
            return []

        # Get sector boundary distance
        if sector_idx == 0:
            boundary_dist = 0.0
        else:
            boundary_dist = self.sector_boundaries[sector_idx][0]

        # Find point on canonical racing line at this distance
        canon = self.canonical_racing_line
        dist = canon['dist_m'].to_numpy()
        x = canon['x_m'].to_numpy()
        y = canon['y_m'].to_numpy()

        # Find closest point
        idx = np.searchsorted(dist, boundary_dist)
        if idx >= len(dist):
            idx = len(dist) - 1

        cx, cy = x[idx], y[idx]

        # Compute tangent direction
        if idx < len(dist) - 1:
            tx = x[idx + 1] - x[idx]
            ty = y[idx + 1] - y[idx]
        else:
            tx = x[idx] - x[idx - 1]
            ty = y[idx] - y[idx - 1]

        # Normalize
        tlen = np.sqrt(tx**2 + ty**2)
        if tlen > 0:
            tx /= tlen
            ty /= tlen

        # Perpendicular (normal)
        nx, ny = -ty, tx

        # Create line 20m on each side of center
        half_width = 20.0
        return [
            (cx - nx * half_width, cy - ny * half_width),
            (cx + nx * half_width, cy + ny * half_width)
        ]

    def get_car_state(self, car_id: str, time_ms: float) -> dict:
        """Return x, y, speed, lapdist, brake, gear, steering, heading, lap at time_ms with deviation applied."""
        idx = int(time_ms / 10)  # 10ms sample rate
        traj = self.trajectories[car_id]

        if idx < 0:
            idx = 0
        if idx >= len(traj):
            idx = len(traj) - 1

        # Apply deviation offset (PATCH 6 - don't modify original)
        x = float(traj[idx, 0] + self.deviation_offsets[car_id][idx, 0])
        y = float(traj[idx, 1] + self.deviation_offsets[car_id][idx, 1])
        speed = float(traj[idx, 2])
        lapdist = float(traj[idx, 3])

        # Handle brake data with backward compatibility
        if traj.shape[1] >= 11:
            # New format: separate front/rear brakes
            brake_front = float(traj[idx, 4])
            brake_rear = float(traj[idx, 5])
            brake = max(brake_front, brake_rear)  # Combined brake for compatibility
            gear = int(traj[idx, 6]) if traj.shape[1] > 6 else 0
            steering = float(traj[idx, 7]) if traj.shape[1] > 7 else 0.0
            heading = float(traj[idx, 8]) if traj.shape[1] > 8 else 0.0
            accel_norm = float(traj[idx, 9]) if traj.shape[1] > 9 else 0.0
            lap_number = int(traj[idx, 10]) if traj.shape[1] > 10 else 1
        else:
            # Old format: single brake value (10 columns or less)
            brake = float(traj[idx, 4]) if traj.shape[1] > 4 else 0.0
            brake_front = brake_rear = brake  # Use same value for both
            gear = int(traj[idx, 5]) if traj.shape[1] > 5 else 0
            steering = float(traj[idx, 6]) if traj.shape[1] > 6 else 0.0
            heading = float(traj[idx, 7]) if traj.shape[1] > 7 else 0.0
            accel_norm = float(traj[idx, 8]) if traj.shape[1] > 8 else 0.0
            if traj.shape[1] >= 10:
                lap_number = int(traj[idx, 9])
            else:
                lap_number = self._get_lap_number(car_id, idx)

        # Compute deviation using FRAME INDEX (not time_ms)
        if car_id in self.per_car_racing_lines:
            dev_info = self.compute_deviation(car_id, idx)  # Pass idx, not time_ms
        else:
            dev_info = {'deviation': 0.0, 'ideal_x': 0.0, 'ideal_y': 0.0}

        return {
            'x': x, 'y': y, 'speed': speed, 'lapdist': lapdist,
            'brake': brake, 'brake_front': brake_front, 'brake_rear': brake_rear,
            'gear': gear, 'lap': lap_number,
            'steering': steering,  # Degrees
            'heading': heading,    # Radians
            'deviation': dev_info['deviation'],
            'ideal_x': dev_info['ideal_x'],
            'ideal_y': dev_info['ideal_y'],
            'accel_norm': accel_norm  # Normalized acceleration 0-1
        }

    def _get_lap_number(self, car_id: str, idx: int) -> int:
        """Get the lap number for a given trajectory index."""
        lap_starts = self.lap_data.get(car_id, [0])
        lap_number = 1
        for lap_start_idx in lap_starts:
            if idx >= lap_start_idx:
                lap_number = lap_starts.index(lap_start_idx) + 1
        return lap_number

    def get_racing_line(self, car_id: str):
        """Get racing line for a car. Returns None if not available."""
        return self.per_car_racing_lines.get(car_id, None)

    def compute_deviation(self, car_id: str, frame_idx: int) -> dict:
        """Calculate signed lateral deviation using KD-tree spatial lookup.

        PHASE 4: Spatial nearest-neighbor method (NO lapdist dependency).
        Robust to corrupted lapdist values.

        Args:
            car_id: Vehicle identifier
            frame_idx: Direct trajectory frame index

        Returns:
            dict with: deviation, ideal_x, ideal_y
        """
        # Select reference line based on user setting
        reference = self.lateral_diff_reference

        if reference == 'global_racing_line':
            # Use global racing line for all cars
            if self.global_racing_line_tree is None:
                return {'deviation': 0.0, 'ideal_x': 0.0, 'ideal_y': 0.0}
            tree = self.global_racing_line_tree
            racing_line = self.racing_line
        elif reference == 'individual':
            # Use individual racing line (placeholder - same as per-car)
            # Only works when a car is selected
            if car_id not in self.racing_line_trees:
                return {'deviation': 0.0, 'ideal_x': 0.0, 'ideal_y': 0.0}
            tree = self.racing_line_trees[car_id]
            racing_line = self.per_car_racing_lines[car_id]
        else:
            # Default: Use per-car racing line (racing_line)
            if car_id not in self.racing_line_trees:
                return {'deviation': 0.0, 'ideal_x': 0.0, 'ideal_y': 0.0}
            tree = self.racing_line_trees[car_id]
            racing_line = self.per_car_racing_lines[car_id]

        traj = self.trajectories[car_id]

        # Bounds check
        if frame_idx < 0 or frame_idx >= len(traj):
            return {'deviation': 0.0, 'ideal_x': 0.0, 'ideal_y': 0.0}

        # Get car position (raw trajectory, no deviation_offsets)
        cx = float(traj[frame_idx, 0])
        cy = float(traj[frame_idx, 1])

        # KD-tree nearest point query
        dist, idx_line = tree.query([cx, cy], k=1)

        # Get ideal point on racing line
        ix = float(racing_line[idx_line, 0])
        iy = float(racing_line[idx_line, 1])

        # Compute tangent vector
        if idx_line < len(racing_line) - 1:
            x0, y0 = racing_line[idx_line]
            x1, y1 = racing_line[idx_line + 1]
        else:
            x0, y0 = racing_line[idx_line - 1]
            x1, y1 = racing_line[idx_line]

        tx = x1 - x0
        ty = y1 - y0

        # Normalize tangent
        tlen = (tx**2 + ty**2)**0.5
        if tlen > 0:
            tx /= tlen
            ty /= tlen

        # Normal vector (90° CCW rotation)
        nx = -ty
        ny = tx

        # Vector from ideal to car
        vx = cx - ix
        vy = cy - iy

        # Signed deviation (positive = right of racing line)
        deviation = vx * nx + vy * ny

        return {
            'deviation': float(deviation),
            'ideal_x': float(ix),
            'ideal_y': float(iy)
        }

    def get_all_car_states(self, time_ms: float) -> dict:
        """Return dict of all cars' current states."""
        states = {}
        for car_id in self.car_ids:
            states[car_id] = self.get_car_state(car_id, time_ms)
        return states

    def get_race_order(self, time_ms: float) -> dict:
        """
        Compute full race ordering at a given time.

        Returns:
            {
                "leader_id": <car_id | None>,
                "cars": {
                    <car_id>: {
                        "position": int,
                        "lap": int,
                        "lapdist": float,
                        "is_leader": bool,
                        "on_lead_lap": bool,
                        "laps_down": int,
                    },
                    ...
                }
            }
        """
        states = self.get_all_car_states(time_ms)
        if not states:
            return {"leader_id": None, "cars": {}}

        # Sort cars by (lap, lapdist, car_id) descending.
        # - Higher lap = further in race
        # - Within same lap, higher lapdist = further ahead
        # - car_id as tie-breaker to keep order deterministic
        sorted_cars = sorted(
            states.items(),
            key=lambda item: (item[1]["lap"], item[1]["lapdist"], item[0]),
            reverse=True,
        )

        leader_id, leader_state = sorted_cars[0]
        leader_lap = leader_state["lap"]

        cars_info: dict = {}

        for pos, (car_id, s) in enumerate(sorted_cars, start=1):
            car_lap = s["lap"]
            lap_delta = leader_lap - car_lap

            # Data glitches can give lap_delta < 0 – clamp for safety.
            if lap_delta < 0:
                lap_delta = 0

            laps_down = max(0, lap_delta)
            on_lead_lap = (laps_down == 0)

            cars_info[car_id] = {
                "position": pos,
                "lap": car_lap,
                "lapdist": s["lapdist"],
                "is_leader": (car_id == leader_id),
                "on_lead_lap": on_lead_lap,
                "laps_down": laps_down,
            }

        return {
            "leader_id": leader_id,
            "cars": cars_info,
        }

    def get_race_positions(self, time_ms: float) -> dict:
        """Deprecated: use get_race_order instead."""
        order = self.get_race_order(time_ms)
        return {cid: info["position"] for cid, info in order["cars"].items()}

    def set_driving_mode(self, mode: str):
        """Apply driving style mode (PATCH 6 - uses deviation offset)."""
        self.driving_mode = mode

        # Define deviation scales
        scales = {
            'Toyota': 1.0,
            'Red Bull': 2.0,
            'Mercedes': 0.5,
        }

        for car_id in self.car_ids:
            traj = self.trajectories[car_id]

            if mode == 'Chaos':
                scale = np.random.uniform(0.5, 3.0)
            else:
                scale = scales.get(mode, 1.0)

            # Generate lateral deviation
            noise_x = np.random.normal(0, scale, len(traj))
            noise_y = np.random.normal(0, scale, len(traj))

            self.deviation_offsets[car_id][:, 0] = noise_x
            self.deviation_offsets[car_id][:, 1] = noise_y

        print(f"Applied driving mode: {mode}")

    def reset_deviation(self):
        """Reset all deviation offsets to zero."""
        for car_id in self.car_ids:
            self.deviation_offsets[car_id][:, :] = 0

    def get_full_trace(self, car_id: str) -> list:
        """Get full trajectory for a car (for full race trail)."""
        if car_id not in self.trajectories:
            return []
        traj = self.trajectories[car_id]
        return [(float(traj[i, 0]), float(traj[i, 1])) for i in range(len(traj))]

    def get_fading_trail(self, car_id: str, duration_s: float) -> list:
        """Get trail for last N seconds of data."""
        if car_id not in self.trajectories:
            return []

        traj = self.trajectories[car_id]
        current_idx = int(self.current_time_ms / 10)
        start_idx = max(0, current_idx - int(duration_s * 100))  # 100 samples per second

        if current_idx >= len(traj):
            current_idx = len(traj) - 1

        return [(float(traj[i, 0]), float(traj[i, 1])) for i in range(start_idx, current_idx + 1)]

    def get_last_lap_trace(self, car_id: str) -> list:
        """Get trace for the last complete lap using pre-computed lap data."""
        if car_id not in self.trajectories:
            return []

        traj = self.trajectories[car_id]
        lap_starts = self.lap_data.get(car_id, [0])

        if len(lap_starts) >= 2:
            # Get last complete lap
            last_lap_start = lap_starts[-2]
            last_lap_end = lap_starts[-1]
            return [(float(traj[i, 0]), float(traj[i, 1])) for i in range(last_lap_start, last_lap_end)]
        else:
            # Return full trace if no complete lap
            return self.get_full_trace(car_id)

    def toggle_car_selection(self, car_id: str):
        """Toggle car selection state."""
        if car_id in self.selected_car_ids:
            self.selected_car_ids.remove(car_id)
        else:
            self.selected_car_ids.append(car_id)

    def select_all_cars(self):
        """Select all cars."""
        self.selected_car_ids = list(self.car_ids)

    def select_no_cars(self):
        """Deselect all cars."""
        self.selected_car_ids = []
