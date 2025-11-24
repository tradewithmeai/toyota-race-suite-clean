# Toyota Race Suite

A high-performance desktop application for visualizing and analyzing Toyota Racing Development (TRD) telemetry data. Built for the TRD Hackathon 2024.

## Features

- **Real-time Race Replay**: Animate multiple vehicles simultaneously with smooth 60fps playback
- **Telemetry Visualization**: View speed, braking, acceleration, and steering data
- **Color Customization**: Personalize car colors and visual effects
- **Delta Speed Analysis**: Compare lap performance against reference speeds
- **Drag & Drop**: Simply drop a CSV file to begin analysis

## Quick Start

### Windows (Easiest)

1. Clone or download the repository
2. **Double-click `run.bat`**

That's it! The script will automatically set up the environment and launch the app.

### Manual Installation

1. Clone the repository:
```bash
git clone https://github.com/tradewithmeai/toyota-race-suite-clean.git
cd toyota-race-suite-clean
```

2. Create a virtual environment:
```bash
python -m venv venv
venv\Scripts\activate  # Windows
source venv/bin/activate  # macOS/Linux
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Run the application:
```bash
python -m src.app.main
```

### Usage

1. Launch the application
2. Drag and drop a TRD telemetry CSV file onto the window
3. Wait for preprocessing to complete
4. Use playback controls to replay the race
5. Click on cars to select them and view telemetry details

## System Requirements

- **OS**: Windows 10/11 (primary), macOS, Linux
- **Python**: 3.10+
- **RAM**: 8GB minimum, 16GB recommended
- **GPU**: OpenGL 3.3+ compatible

## Project Structure

```
toyota-race-suite-clean/
├── src/
│   ├── app/           # Desktop application
│   ├── processing/    # Data processing modules
│   └── utils/         # Utility functions
├── assets/            # Icons, textures, logo
├── data/
│   └── sample/        # Sample processed data
├── docs/              # Documentation
├── tests/             # Test suite
├── requirements.txt   # Python dependencies
└── README.md
```

## Documentation

- [USAGE.md](docs/USAGE.md) - Detailed usage instructions
- [DATA_FORMAT.md](docs/DATA_FORMAT.md) - Input data format specification
- [CHANGELOG.md](docs/CHANGELOG.md) - Version history

## Controls

| Control | Action |
|---------|--------|
| Space | Play/Pause |
| Click on track | Play/Pause |
| Click on car | Select car |
| Scroll | Zoom in/out |
| Drag | Pan view |
| 1-9 | Set playback speed |

## License

Proprietary - TRD Hackathon 2024

## Acknowledgments

Built for Toyota Racing Development Hackathon 2024
