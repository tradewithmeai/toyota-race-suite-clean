# Usage Guide

## Getting Started

### Launching the Application

```bash
python -m src.app.main
```

The application will open with a loading screen ready to accept data.

### Loading Data

1. **Drag and Drop**: Drag a TRD telemetry CSV file onto the application window
2. **Processing**: The app will automatically process the raw data
3. **Visualization**: Once complete, the race replay view will appear

## Interface Overview

### Main Display

- **Track View**: Central area showing the race track with car positions
- **Telemetry Panel**: Right sidebar with detailed car data
- **Playback Controls**: Bottom bar with timeline and speed controls
- **Settings Menu**: Top-right gear icon for customization

### Car Selection

- **Click on a car**: Select it to view its telemetry
- **Ctrl+Click**: Add/remove cars from selection
- **Click empty area**: Deselect all cars

### Playback Controls

| Control | Function |
|---------|----------|
| Play/Pause button | Toggle playback |
| Timeline slider | Scrub through race |
| Speed buttons | 0.5x, 1x, 2x, 4x, 8x |
| Time display | Current race time |

### Visual Effects

Access through **Visuals - Custom** button:

- **Brake Arcs**: Show front/rear brake pressure as colored arcs
- **Brake Fill**: Fill car circle based on brake intensity
- **Trail Mode**: Fading trail behind cars
  - fade_3s, fade_5s, fade_10s
  - Delta Speed (shows speed vs reference)
  - Custom duration

### Color Customization

1. Click **Visuals - Custom** button
2. Select **Colours** tab
3. Click on a car in the grid to select it
4. Use RGB sliders or hex input to adjust color
5. Click **Apply** to save changes

### Theme

Toggle between Light and Dark themes in settings.

## Keyboard Shortcuts

| Key | Action |
|-----|--------|
| Space | Play/Pause |
| Left Arrow | Step back 1 second |
| Right Arrow | Step forward 1 second |
| R | Reset to start |
| 1-9 | Set playback speed multiplier |

## Tips

- **Performance**: For smooth playback, close other applications
- **Selection**: Selected cars are highlighted with a white ring
- **Zoom**: Use mouse scroll to zoom in on track details
- **Pan**: Click and drag to pan the view

## Troubleshooting

### App won't start
- Ensure Python 3.10+ is installed
- Verify all dependencies: `pip install -r requirements.txt`
- Check for pywin32 on Windows: `pip install pywin32`

### Slow performance
- Reduce number of visible cars
- Disable visual effects (trails, brake arcs)
- Close other GPU-intensive applications

### Data won't load
- Verify CSV format matches TRD specification
- Check console for error messages
- Ensure file is not open in another program
