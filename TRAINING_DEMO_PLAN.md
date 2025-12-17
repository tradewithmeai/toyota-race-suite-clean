# Training Demo Script Implementation Plan

## Overview
Create a fully automated training demo system that showcases all features of the race simulation app on first launch. The demo will use a simulated cursor with click animations and subtitle-style messages to guide viewers through all visualization and interaction capabilities.

## Key Requirements
- Fully automated playback (no user interaction during demo)
- Simulated cursor with click animations
- Subtitle-style message display (user is providing this function)
- Triggered on first-time launch
- Demonstrates all 5 custom visualizations and UI controls

## Architecture

### 1. Demo State Manager (`src/app/training_demo.py`)
New module to orchestrate the training demo with these components:

**DemoStateManager Class:**
- Manages demo playback state (running, paused, completed)
- Tracks current demo step and timing
- Coordinates cursor, messages, and UI interactions
- Provides skip/exit functionality

**Key Methods:**
- `start_demo()` - Initialize and begin demo sequence
- `update(delta_time)` - Update demo state each frame
- `execute_step(step)` - Execute current demo step
- `cleanup()` - Clean up demo artifacts and return to normal mode

### 2. Simulated Cursor System (`src/app/demo_cursor.py`)
Renders animated cursor that guides attention through the demo.

**DemoCursor Class:**
- Position interpolation (smooth movement between UI elements)
- Click animation (scale pulse + visual feedback)
- Hover state rendering
- Drawing in screen space (independent of zoom/pan)

**Visual Design:**
- Standard cursor arrow graphic
- Click animation: brief scale-up + ripple effect
- Smooth easing for movements (cubic ease-in-out)
- Always rendered on top layer

### 3. Demo Script Definition (`src/app/demo_script.py`)
Structured sequence of demo steps with timing and actions.

**Step Structure:**
```python
{
    'duration': float,  # seconds
    'message': str,  # subtitle text
    'cursor_target': tuple or None,  # (x, y) screen coords or UI element
    'actions': list,  # Actions to perform
    'camera': dict or None,  # Zoom/pan state
}
```

**Demo Sequence:**

1. **Introduction (5s)**
   - Message: "Welcome to Toyota Race Suite - Data Pipeline & Visualization System"
   - Cursor: Center screen
   - Actions: None (wait)

2. **Data Pipeline Overview (8s)**
   - Message: "This system processes telemetry data from 20 race cars"
   - Show stats: 20 cars, track bounds, total duration
   - Cursor: Gesture to track view

3. **Playback Controls (12s)**
   - Message: "Control replay with play, pause, and speed adjustment"
   - Cursor: Move to play button → click
   - Actions: Start playback
   - Cursor: Move to speed slider → adjust
   - Cursor: Move to time scrubber → scrub

4. **Quick Pause/Play (8s)**
   - Message: "Click anywhere on track for instant pause/play"
   - Actions: Play simulation
   - Cursor: Click on track → pause
   - Cursor: Click on track → resume

5. **Car Selection (10s)**
   - Message: "Click cars to select them for detailed analysis"
   - Cursor: Click car 1 → select
   - Cursor: Click car 2 → add to selection
   - Show telemetry panel updates

6. **Visualization 1: Brake Arcs (15s)**
   - Message: "Brake Arcs: Expanding semi-rings show front and rear brake pressure"
   - Message: "Front and rear arcs align with car motion for intuitive feel"
   - Cursor: Enable "Brake Arcs" checkbox
   - Actions: Enable brake visualization
   - Camera: Zoom to selected car
   - Show percentage labels (F:85%, R:65%)

7. **Visualization 2: Lateral Deviation (18s)**
   - Message: "Lateral Diff: Shows deviation from racing line as -1 to 1 metric"
   - Message: "5 bars each side with progressive animation - instant intuitive feedback"
   - Cursor: Enable "Lateral Diff" checkbox
   - Actions: Enable deviation bars
   - Show bars animating with percentage fills
   - Cursor: Change reference line dropdown

8. **Visualization 3: Steering Direction (12s)**
   - Message: "Steering Angle: Arrow shows steering input with heading"
   - Cursor: Enable "Steering Angle" checkbox
   - Actions: Enable steering visualization
   - Show arrow responding to steering input

9. **Visualization 4: Acceleration (15s)**
   - Message: "Accel Fill: Expanding circle shows acceleration intensity"
   - Message: "Two metrics combined: magnitude and direction via color"
   - Cursor: Enable "Accel Fill" checkbox
   - Actions: Enable acceleration visualization
   - Show color transitions (low→medium→high)

10. **Visualization 5: Delta Trail (20s)**
    - Message: "Delta Trail: Most insightful - shows 1-15s historical path"
    - Message: "Trail colored by speed delta from canonical racing line"
    - Cursor: Enable "Trail" checkbox
    - Cursor: Select "Delta Speed" mode
    - Actions: Enable delta trail
    - Cursor: Adjust trail length slider
    - Show color coding (blue=slower, green=optimal, red=faster)

11. **Customization (15s)**
    - Message: "Customize color and size of all visualizations"
    - Cursor: Click "Visuals - Custom" button
    - Show color customization menu
    - Cursor: Adjust brake arc size slider
    - Cursor: Change deviation bar color
    - Cursor: Close menu

12. **Multi-Car Comparison (12s)**
    - Message: "Apply trail to multiple cars for driver comparison"
    - Actions: Select 3-4 cars
    - Actions: Enable trails for all
    - Camera: Zoom out to show multiple cars with trails

13. **Zoom and Pan (15s)**
    - Message: "Zoom with scroll wheel, pan with right-click drag"
    - Actions: Demonstrate zoom in (cursor: scroll gesture)
    - Actions: Demonstrate pan (cursor: drag gesture)
    - Actions: Reset view

14. **Racing Lines (12s)**
    - Message: "Compare against canonical, global, or individual racing lines"
    - Cursor: Toggle "Racing Line" checkbox
    - Cursor: Toggle "Global Racing Line" checkbox
    - Show different line visualizations

15. **Best Lap Comparison (10s)**
    - Message: "Simulation can compare against driver's own best lap"
    - Actions: Switch lateral diff reference to "Individual Racing Lines"
    - Show individual performance comparison

16. **Conclusion (8s)**
    - Message: "Toyota Race Suite: Complete pipeline from raw data to actionable insights"
    - Cursor: Center screen
    - Actions: Fade demo overlay
    - Return to normal operation

**Total Duration: ~3.5 minutes**

### 4. Integration Points

**First-Time Launch Detection:**
- Check config file: `~/.race_replay_config.json`
- Add `demo_completed: false` flag
- Trigger demo when `demo_completed == false` and data is loaded

**Modified Files:**

**`src/app/main.py`:**
- Import training_demo module: `from app.training_demo import DemoStateManager, should_show_demo`
- Check demo flag after data loads (in `_show_replay()` at ~line 257)
- Initialize demo mode if first launch: `self.demo_manager = DemoStateManager(...)`
- Add demo update to main render loop (before `render_overlay()` at ~line 407)
- Note: Message overlay already integrated at line 407 ✅

**`src/app/app_state.py`:**
- Add `DEMO` state to AppState enum
- Track demo_mode flag in StateManager

**`src/app/world_model.py`:**
- Add demo_mode flag
- Add methods to save/load demo_completed preference

### 5. Cursor Movement System

**Screen Coordinate Mapping:**
- Map UI element identifiers to screen coordinates
- Handle dynamic elements (cars, track positions)
- Update coordinates on window resize

**Interpolation:**
```python
def interpolate_cursor(start, end, t, easing='ease_in_out'):
    # Cubic easing for smooth movement
    # t = time progress (0 to 1)
```

**Click Animation:**
- Scale: 1.0 → 1.3 → 1.0 (200ms total)
- Ripple: Expanding circle from click point (300ms fade)

### 6. Message Display Integration

**✅ IMPLEMENTED**: The message overlay system is now live on main branch!

**Location**: `src/app/message_overlay.py`

**API Interface:**
```python
from app.message_overlay import show_message, clear_all_messages

# Display a message (automatically queues if another message is active)
show_message("Your message here", duration=3.0)

# Clear all queued and active messages (for demo exit/skip)
clear_all_messages()
```

**Features:**
- Subtitle-style display at bottom-center (8% from bottom)
- Auto-fade over last 0.5 seconds
- Message queueing (no overlap - sequential display)
- White text with shadow on semi-transparent dark background
- Font size: 32-48px (viewport-responsive)
- Already integrated into main render loop at `main.py:407`

**Demo Integration:**
The training demo will simply call `show_message()` at each step. The overlay system handles all timing, fading, and queueing automatically. No additional message display code needed!

### 7. Camera Control

**Zoom Presets:**
- Overview: zoom_level = 1.0 (fit to screen)
- Car Detail: zoom_level = 3.0 (close-up)
- Smooth transitions between zoom levels

**Pan Targets:**
- Can pan to specific world coordinates
- Can follow selected car automatically

### 8. Action Execution

**UI Actions:**
- Checkbox toggling (via dpg.set_value)
- Slider adjustment (via dpg.set_value with animation)
- Button clicks (via callback invocation)
- Dropdown selection (via dpg.set_value)

**Simulation Actions:**
- Play/pause control
- Speed adjustment
- Time scrubbing
- Car selection/deselection

### 9. Skip/Exit Functionality

**Skip Demo:**
- ESC key or "Skip Demo" button
- Mark demo as completed
- Return to normal operation

**Progress Indicator:**
- Small progress bar showing demo completion (e.g., "Step 5/16")
- Positioned in corner of screen

## Implementation Order

1. **Phase 1: Core Infrastructure**
   - Create DemoCursor class with basic rendering
   - Create DemoStateManager with step sequencing
   - Add demo mode detection to main.py

2. **Phase 2: Demo Script**
   - Define complete demo_script.py with all steps
   - Implement cursor movement interpolation
   - Test step timing and transitions

3. **Phase 3: Actions**
   - Implement all UI action handlers
   - Implement camera control system
   - Test action execution

4. **Phase 4: Integration**
   - Integrate message display function
   - Add first-launch detection
   - Add skip/exit functionality
   - Test complete demo flow

5. **Phase 5: Polish**
   - Smooth timing adjustments
   - Add progress indicator
   - Handle edge cases (window resize, etc.)
   - Final testing

## Critical Files to Modify

1. **New Files:**
   - `src/app/training_demo.py` - Main demo orchestrator (DemoStateManager, ActionExecutor, CameraController, helper functions)
   - `src/app/demo_cursor.py` - Cursor rendering and animation
   - `src/app/demo_script.py` - Step definitions and complete demo sequence

2. **Modified Files:**
   - `src/app/main.py` - Add demo initialization and update loop (~20 lines total)
   - `src/app/app_state.py` - Add DEMO state to AppState enum
   - `src/app/world_model.py` - Add demo config persistence methods

3. **Existing Files (Already Implemented):**
   - ✅ `src/app/message_overlay.py` - Message display system (no changes needed)
   - Note: Demo cursor renders directly on canvas, no gpu_renderer.py changes needed

## Testing Strategy

1. Test each demo step in isolation
2. Test complete demo sequence
3. Test skip functionality
4. Test with different window sizes
5. Test demo repeat (manual trigger)
6. Verify first-launch detection works correctly

## Notes

- Demo runs in "god mode" - can control UI programmatically
- Cursor is purely visual (doesn't actually move system cursor)
- All visualizations must be enabled programmatically
- Camera movements should be smooth and purposeful
- Message timing is critical for comprehension
- Demo should feel professional and polished

---

## Message Overlay System (Already Implemented ✅)

### Implementation Details
The message overlay system has been successfully implemented and merged to main branch. Key details:

**File**: `src/app/message_overlay.py` (166 lines)

**Integration Points**:
- Line 24 in `main.py`: `from app.message_overlay import init_message_overlay, render_overlay`
- Line 324 in `main.py`: `init_message_overlay("canvas")` (called in `_show_replay()`)
- Line 407 in `main.py`: `render_overlay()` (called in render loop, after telemetry update)

**Key Features for Demo**:
1. **Automatic Queueing**: Multiple `show_message()` calls queue automatically - no overlap
2. **Smart Fade**: Last 0.5 seconds fade from alpha 255 → 0
3. **Clean API**: Just call `show_message(text, duration)` - that's it!
4. **Cleanup**: Call `clear_all_messages()` when demo exits/skips

**Usage in Demo Steps**:
```python
# In demo_script.py step definitions:
{
    'id': 'intro',
    'duration': 5.0,
    'message': 'Welcome to Toyota Race Suite',
    # ... other fields
}

# In DemoStateManager._begin_step():
if step.get('message'):
    show_message(step['message'], duration=step['duration'])
```

**Rendering Order** (bottom to top):
1. Track/density map (static layer)
2. Racing lines (static layer)
3. Car trails (dynamic layer)
4. Cars and visualizations (dynamic layer)
5. Telemetry HUD panels (UI layer)
6. **Message overlay** ← Line 407
7. **Demo cursor** ← Will be added after message overlay

This ensures the demo cursor appears on top of messages, and both appear on top of all simulation elements.

### Why This Integration Works Perfectly

1. **Zero Conflicts**: Messages and cursor are independent - message at bottom, cursor anywhere
2. **Performance**: Message overlay tested with zero FPS impact
3. **Timing**: Message overlay uses `time.time()` (same as demo will use)
4. **Visual Clarity**: Subtitle-style bottom-center doesn't obscure demo cursor or UI elements
5. **Queue Management**: Automatic queueing means demo script just calls `show_message()` - no timing logic needed

### Example Demo Step Execution
```python
def _begin_step(self, step_index):
    step = self.script.steps[step_index]

    # Show message - handled by message_overlay
    if step.get('message'):
        show_message(step['message'], step['duration'])  # That's all!

    # Move cursor
    if step.get('cursor_target'):
        target = self._resolve_cursor_target(step['cursor_target'])
        self.cursor.move_to(target, duration=1.0)

    # Execute actions
    if step.get('actions'):
        for action in step['actions']:
            self.action_executor.execute(action)

    # Camera movement
    if step.get('camera'):
        self.camera_controller.animate_to(step['camera'])
```

The message overlay eliminates ~100 lines of subtitle rendering code from the demo implementation!
