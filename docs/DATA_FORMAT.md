# Data Format Specification

## Input Format

### Raw Telemetry CSV

The application expects TRD telemetry data in long format CSV with the following columns:

| Column | Type | Description |
|--------|------|-------------|
| timestamp | datetime | ISO 8601 timestamp |
| vehicle_id | string | Unique vehicle identifier (e.g., "GR86-016-55") |
| lap | integer | Lap number |
| telemetry_name | string | Name of telemetry channel |
| telemetry_value | float | Value of telemetry channel |

### Required Telemetry Channels

| Channel Name | Unit | Description |
|--------------|------|-------------|
| VBOX_Lat_Min | degrees | GPS latitude |
| VBOX_Long_Minutes | degrees | GPS longitude |
| speed | km/h | Vehicle speed |
| pbrake_f | bar | Front brake pressure |
| pbrake_r | bar | Rear brake pressure |
| aps | % | Accelerator pedal position |
| Steering_Angle | degrees | Steering wheel angle |
| gear | - | Current gear |
| nmot | rpm | Engine RPM |
| accx_can | g | Longitudinal acceleration |
| accy_can | g | Lateral acceleration |
| Laptrigger_lapdist_dls | m | Distance along lap |

## Processed Data Format

After preprocessing, data is stored in `data/processed/`:

### metadata.json

```json
{
  "bounds": {
    "x_min": -500.0,
    "x_max": 500.0,
    "y_min": -300.0,
    "y_max": 300.0
  },
  "total_duration_ms": 180000,
  "sample_rate_ms": 10,
  "car_ids": ["GR86-016-55", "GR86-040-3", ...],
  "colors": {
    "GR86-016-55": [255, 68, 68],
    ...
  },
  "per_car_racing_lines": true,
  "racing_line_points": 30000,
  "trajectory_columns": 11,
  "separate_brake_channels": true
}
```

### Trajectory Files

Each car has a `.npy` file in `trajectories/`:

```
trajectories/
├── GR86-016-55.npy
├── GR86-040-3.npy
└── ...
```

Each file is a NumPy array with shape `(N, 11)`:

| Column | Index | Description |
|--------|-------|-------------|
| x | 0 | X position (meters) |
| y | 1 | Y position (meters) |
| speed | 2 | Speed (m/s) |
| brake_front | 3 | Front brake pressure |
| brake_rear | 4 | Rear brake pressure |
| throttle | 5 | Throttle position |
| steering | 6 | Steering angle |
| gear | 7 | Gear number |
| rpm | 8 | Engine RPM |
| accel_x | 9 | Longitudinal acceleration |
| accel_y | 10 | Lateral acceleration |

### Racing Line Files

Global racing line:
- `racing_line.npy` - Shape `(1500, 2)` - [x, y] positions

Per-car racing lines in `racing_lines/`:
- `{car_id}_racing_line.npy` - Shape `(30000, 2)` - [x, y] positions

### Canonical Racing Line (Optional)

For delta speed analysis:

- `canonical_racing_line.csv` - Track centerline with curvature
- `speed_profile.csv` - Reference and ideal speeds
- `ideal_lap_profile.csv` - Ideal lap timing

### Fastest Laps (Optional)

In `fastest_laps/lap_csv/`:

```
fastest_laps/
└── lap_csv/
    ├── fastest_lap_GR86-016-55_lap4.csv
    └── ...
```

Each contains: `timestamp_dt`, `dist_m`, `x_m`, `y_m`, `speed_ms`

### Delta Speed Trails (Optional)

In `trails/`:

```
trails/
├── trail_GR86-016-55_fastestlap_15s_ref.csv
└── ...
```

Columns: `vehicle_id`, `timestamp_dt`, `t_rel_s`, `x_m`, `y_m`, `delta_kmh`

## Coordinate System

- **Origin**: First GPS point of reference lap
- **X-axis**: East (positive = east)
- **Y-axis**: North (positive = north)
- **Units**: Meters

The GPS coordinates are converted to local ENU (East-North-Up) coordinates using WGS84 ellipsoid parameters.
