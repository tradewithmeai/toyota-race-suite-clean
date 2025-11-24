# Changelog

All notable changes to Toyota Race Suite are documented here.

## [1.0.0] - 2024-11-24

### Added
- Initial production release for TRD Hackathon 2024
- Real-time race replay with multi-car visualization
- Drag-and-drop CSV file loading
- Automatic preprocessing pipeline
- Telemetry panel with live data display
- Color customization menu with RGB/hex picker
- Visual effects: brake arcs, brake fill, trails
- Delta speed trail analysis
- Light/dark theme support
- Playback speed control (0.5x - 8x)
- Car selection with telemetry focus
- Sector timing display
- Per-car racing line generation

### Fixed
- Thread safety for UI updates during preprocessing
- Color updates applying immediately
- Car highlight visibility in color menu
- Menu click propagation to track

### Technical
- DearPyGUI-based desktop application
- NumPy trajectory storage for performance
- KDTree spatial queries for racing line analysis
- Background preprocessing with progress callbacks

## [0.9.0] - 2024-11-20

### Added
- Section compare processing pipeline
- Canonical racing line with curvature
- Speed profile generation
- Fastest lap extraction

## [0.8.0] - 2024-11-15

### Added
- Loading screen with animated logo
- Intro animation sequence
- Transition effects

## [0.7.0] - 2024-11-10

### Added
- Color customization system
- Visual effects framework
- Brake visualization (arcs and fill)

## [0.6.0] - 2024-11-05

### Added
- Telemetry panel with gauges
- HUD overlay system
- Deviation bars

## [0.5.0] - 2024-10-30

### Added
- GPU-accelerated rendering
- Smooth zoom and pan
- Car trail rendering

## [0.4.0] - 2024-10-25

### Added
- Playback controls
- Timeline scrubbing
- Speed multiplier

## [0.3.0] - 2024-10-20

### Added
- Per-car racing line computation
- Lap detection
- Time alignment

## [0.2.0] - 2024-10-15

### Added
- Raw data loading
- GPS to XY conversion
- Trajectory interpolation

## [0.1.0] - 2024-10-10

### Added
- Initial project structure
- Basic DearPyGUI window
- File drop handling
