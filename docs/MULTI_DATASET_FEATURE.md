# Multi-Dataset Support

## Overview

The multi-dataset feature allows users to load and compare multiple racing sessions within the same application instance. Users can quickly switch between different sessions to analyze lap times, driving lines, and telemetry data across different races or practice sessions.

## Features

### Dataset Management
- **Load Multiple Sessions**: Load additional processed data directories while keeping existing sessions in memory
- **Quick Switching**: Click to switch between loaded datasets instantly
- **Session Information**: View car count and duration for each loaded session
- **Memory Management**: Remove datasets from memory when no longer needed
- **Comparison View**: See all loaded sessions in a comparison table

### User Interface
- **Dataset Panel**: New collapsible panel in the control sidebar showing all loaded sessions
- **Active Session Indicator**: Visual indicator (●) shows which session is currently active
- **Load Another Button**: Open file dialog to add more sessions
- **Remove Button**: Remove sessions from memory (requires at least 2 sessions loaded)
- **Clickable Session Names**: Click any session name to switch to it instantly

## How to Use

### Loading Initial Dataset
1. Start the application
2. Load a processed data directory (drag-and-drop or browse)
3. The session will appear in the Dataset panel as the active session

### Loading Additional Datasets
1. In the Dataset panel, click "Load Another"
2. Select a different processed data directory
3. The new session will be added to the list
4. Application automatically switches to the newly loaded session

### Switching Between Datasets
1. View the list of loaded sessions in the Dataset panel
2. Click on any session name to switch to it
3. The viewport, telemetry, and controls will update to show the new session

### Removing Datasets
1. Switch to the session you want to remove (it must be active)
2. Click the "Remove" button
3. Confirm the removal in the popup dialog
4. Application switches to another session automatically

## Technical Implementation

### Architecture

**DatasetManager** (`src/app/dataset_manager.py`)
- Manages multiple loaded datasets
- Tracks active dataset
- Provides session metadata and comparison data

**DatasetInfo** (`src/app/dataset_manager.py`)
- Stores information about each loaded session
- Extracts display names, duration, and car counts

**DatasetPanel** (`src/app/dataset_panel.py`)
- UI component for dataset selection
- Handles user interactions (clicks, load, remove)
- Updates display when datasets change

**WorldModel Integration** (`src/app/world_model.py`)
- Modified to accept DatasetManager in constructor
- Added `reload_from_active_dataset()` method
- Added `switch_to_dataset(dataset_id)` method
- Added `_clear_state()` method for clean reloading

### Key Methods

```python
# DatasetManager
dataset_id, info = manager.add_dataset(data_dir)
manager.set_active_dataset(dataset_id)
active = manager.get_active_dataset()
manager.remove_dataset(dataset_id)

# WorldModel
world.switch_to_dataset(dataset_id)  # Switch and reload
world.reload_from_active_dataset()   # Reload current

# DatasetPanel
panel.update_dataset_list()          # Refresh UI
```

### Data Flow

1. **Initial Load**:
   - User loads processed data directory
   - DatasetManager creates new dataset entry
   - WorldModel loads trajectories from active dataset
   - DatasetPanel displays the session

2. **Load Additional**:
   - User clicks "Load Another"
   - File dialog opens for directory selection
   - DatasetManager adds new dataset
   - WorldModel switches to new dataset
   - UI updates to show new session

3. **Switch Dataset**:
   - User clicks session name
   - DatasetManager sets new active dataset
   - WorldModel clears old data
   - WorldModel loads new trajectories
   - Telemetry panel refreshes car list
   - Playback controls reset

4. **Remove Dataset**:
   - User clicks "Remove" (confirmation dialog)
   - DatasetManager removes dataset
   - If active dataset removed, switches to another
   - WorldModel reloads from new active dataset

## Limitations

- **No Cross-Session Overlay**: Cannot overlay cars from different sessions simultaneously (would require major refactor)
- **Memory Usage**: Each loaded session consumes memory (trajectories, racing lines, etc.)
- **Single Active Session**: Only one session can be viewed at a time
- **No Session Persistence**: Loaded sessions cleared on application restart

## Future Enhancements

Potential improvements for future releases:

1. **Cross-Session Comparison**:
   - Overlay racing lines from multiple sessions
   - Compare lap times in detailed table
   - Side-by-side viewport comparison

2. **Session Persistence**:
   - Remember recently loaded sessions
   - Auto-load last used sessions
   - Session favorites/bookmarks

3. **Batch Operations**:
   - Load multiple sessions at once
   - Export comparison reports
   - Batch analysis across sessions

4. **Advanced Comparison**:
   - Lap time distribution charts
   - Sector performance comparison
   - Driver consistency metrics

## Testing Recommendations

### Manual Tests
1. **Load Multiple Sessions**: Load 3-5 different sessions and verify all appear in list
2. **Switch Between Sessions**: Click each session name, verify data loads correctly
3. **Remove Session**: Remove active session, verify switch to another works
4. **Memory Check**: Monitor memory usage with 5+ sessions loaded
5. **UI Responsiveness**: Verify switching is fast (<1 second)

### Edge Cases
- Load same session twice (should allow)
- Remove last session (should prevent)
- Switch during playback (should reset time)
- Load invalid directory (should show error)

## Files Modified

- `src/app/dataset_manager.py` (new) - Core dataset management
- `src/app/dataset_panel.py` (new) - UI panel for dataset selection
- `src/app/world_model.py` - Added dataset switching support
- `src/app/main.py` - Integrated dataset manager and panel

## Compatibility

- Compatible with all existing processed data directories
- No changes to data format required
- Works with drag-and-drop, file dialogs, and demo data
- Backward compatible with single-session workflow
