"""Main entry point for Race Replay desktop application."""

import os
import sys
import time

# Set working directory to the executable's location for PyInstaller compatibility
if getattr(sys, 'frozen', False):
    # Running as compiled executable
    application_path = os.path.dirname(sys.executable)
    os.chdir(application_path)
    src_dir = application_path
else:
    # Running as script
    src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

sys.path.insert(0, src_dir)

import dearpygui.dearpygui as dpg

from app.app_state import StateManager, AppState
from app.loading_screen import LoadingScreen
from app.preprocessing_runner import PreprocessingRunner, get_default_output_dir
from app.world_model import WorldModel
from app.gpu_renderer import GPURenderer
from app.controls import PlaybackControls
from app.telemetry_panel import TelemetryPanel
# Drag-and-drop disabled for stability
# from app.win32_drop import Win32DropHandler
from app.intro_animation import IntroAnimation
from app.transitions import TransitionManager, AnimatedProgress
from app.message_overlay import init_message_overlay, render_overlay
from app.training_demo import DemoStateManager, should_show_demo

# Trail generation for delta speed visualization
try:
    from processing.trail_generation import (
        load_canonical_line,
        build_canonical_kdtree,
        generate_all_trails
    )
    TRAIL_GENERATION_AVAILABLE = True
except ImportError:
    TRAIL_GENERATION_AVAILABLE = False
    print("Trail generation module not available - delta speed trails disabled")


class RaceReplayApp:
    """Main application class managing state and UI."""

    def __init__(self):
        self.state_manager = StateManager()
        self.intro_animation = None
        self.loading_screen = None
        self.preprocessing_runner = None
        # Skip intro in hackathon mode
        self.show_intro = os.environ.get('HACKATHON_DEMO') != '1'

        # Replay components (created when data is ready)
        self.world = None
        self.renderer = None
        self.controls = None
        self.telemetry = None

        # Frame timing
        self.frame_count = 0
        self.last_fps_time = time.time()

        # Viewport dimensions
        self.viewport_width = 1600
        self.viewport_height = 900

        # Drag-and-drop handler
        self.drop_handler = None

        # Transition manager
        self.transitions = TransitionManager()
        self.progress_animator = None

        # Training demo
        self.demo_manager = None

    def setup(self):
        """Initialize DearPyGUI and create initial UI."""
        dpg.create_context()

        # Create viewport
        dpg.create_viewport(title="Race Replay - Toyota GR86",
                           width=self.viewport_width, height=self.viewport_height,
                           resizable=True)

        # Set up state change callback
        self.state_manager.set_state_change_callback(self._on_state_change)

        # HACKATHON MODE: Auto-load processed data
        if os.environ.get('HACKATHON_DEMO') == '1':
            processed_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), 'data', 'processed')
            if os.path.exists(processed_dir):
                print(f"🏁 Hackathon mode: Auto-loading data from {processed_dir}")
                self.state_manager.set_processed_dir(processed_dir)

        # Create intro animation
        self.intro_animation = IntroAnimation(self._on_intro_complete)
        self.intro_animation.setup_ui()

        # Create loading screen (hidden initially)
        self.loading_screen = LoadingScreen(self.state_manager)
        self.loading_screen.setup_ui()

        # Configure viewport
        dpg.setup_dearpygui()
        dpg.show_viewport()

        # Start with intro animation
        if self.show_intro:
            dpg.set_primary_window("intro_window", True)
            self.intro_animation.start()
            # Hide loading screen during intro
            self.loading_screen.hide()
        else:
            dpg.set_primary_window("loading_window", True)

        # Drag-and-drop disabled for stability
        # self.drop_handler = Win32DropHandler(self._on_files_dropped)
        # self.drop_handler.enable("Race Replay - Toyota GR86")
        self.drop_handler = None

        # Create fade overlay for transitions
        self.transitions.create_fade_overlay()

    def _on_intro_complete(self):
        """Handle intro animation completion."""
        print("Intro animation complete")
        # Clean up intro and show loading screen
        self.intro_animation.hide()
        self.intro_animation.cleanup()
        self.loading_screen.show()
        dpg.set_primary_window("loading_window", True)
        self.show_intro = False

    def _on_state_change(self, old_state: AppState, new_state: AppState):
        """Handle state transitions."""
        print(f"State: {old_state.value} -> {new_state.value}")

        if new_state == AppState.PROCESSING:
            self.loading_screen.update_for_state(new_state)
            self._start_preprocessing()
        elif new_state == AppState.READY:
            # Use crossfade transition to replay view
            self.transitions.crossfade(
                duration_ms=600,
                on_midpoint=self._show_replay,
                on_complete=lambda: print("Transition to replay complete")
            )
        elif new_state == AppState.ERROR:
            self.loading_screen.update_for_state(new_state)
        elif new_state == AppState.WAITING_FOR_FILE:
            self.loading_screen.update_for_state(new_state)
            self.loading_screen.show()

    def _on_files_dropped(self, file_paths):
        """Handle files dropped onto the window."""
        # Only handle drops when waiting for file
        if self.state_manager.state != AppState.WAITING_FOR_FILE:
            print("Ignoring drop - not in waiting state")
            return

        if not file_paths:
            return

        # Handle the first dropped file/folder
        dropped_path = file_paths[0]
        print(f"File dropped: {dropped_path}")

        # Use loading screen's handler which manages CSV and folder logic
        self.loading_screen.handle_file_drop(dropped_path)

    def _start_preprocessing(self):
        """Start preprocessing the dropped file."""
        input_file = self.state_manager.input_file_path
        output_dir = get_default_output_dir(input_file)

        print(f"Starting preprocessing:")
        print(f"  Input: {input_file}")
        print(f"  Output: {output_dir}")

        # Create preprocessing runner
        self.preprocessing_runner = PreprocessingRunner(
            on_progress=self._on_preprocessing_progress,
            on_complete=self._on_preprocessing_complete,
            on_error=self._on_preprocessing_error
        )

        self.preprocessing_runner.start(input_file, output_dir)

    def _on_preprocessing_progress(self, message: str, percent: float):
        """Handle preprocessing progress update."""
        self.state_manager.set_processing_progress(message, percent)
        self.loading_screen.update_progress(message, percent)

    def _on_preprocessing_complete(self, output_dir: str):
        """Handle preprocessing completion."""
        print(f"Preprocessing complete: {output_dir}")
        # Complete the animation (snap to final logo)
        if self.loading_screen.animator:
            self.loading_screen.animator.complete_animation()
        self.state_manager.set_ready(output_dir)

    def _on_preprocessing_error(self, error_message: str):
        """Handle preprocessing error."""
        print(f"Preprocessing error: {error_message}")
        self.state_manager.set_error(error_message)

    def _generate_trails_if_needed(self, data_dir: str):
        """Generate delta speed trails if not already present.

        Args:
            data_dir: The output directory from preprocessing (e.g., data/processed)
        """
        if not TRAIL_GENERATION_AVAILABLE:
            print("Trail generation not available - skipping")
            return

        trails_dir = os.path.join(data_dir, "trails")
        index_file = os.path.join(trails_dir, "trail_index_15s_ref.csv")

        # Check if trails already exist
        if os.path.exists(index_file):
            print(f"Trail index already exists: {index_file}")
            return

        # Check if canonical line exists (required for trail generation)
        canonical_path = os.path.join(data_dir, "canonical_racing_line.csv")
        if not os.path.exists(canonical_path):
            print(f"Canonical racing line not found at {canonical_path} - skipping trail generation")
            return

        # Check if fastest laps exist
        fastest_laps_dir = os.path.join(data_dir, "fastest_laps", "lap_csv")
        if not os.path.exists(fastest_laps_dir):
            print(f"Fastest laps not found at {fastest_laps_dir} - skipping trail generation")
            return

        print(f"Generating delta speed trails in {trails_dir}...")
        try:
            # Load canonical line
            canonical_line = load_canonical_line(data_dir)
            print(f"  Loaded canonical line: {len(canonical_line)} points")

            # Build KDTree
            canon_tree = build_canonical_kdtree(canonical_line)

            # Extract speed arrays
            ref_speed_ms = canonical_line["ref_speed_ms"].to_numpy()
            ideal_speed_ms = canonical_line["ideal_speed_ms"].to_numpy()

            # Generate trails
            meta_df = generate_all_trails(
                canonical_line,
                canon_tree,
                ref_speed_ms,
                ideal_speed_ms,
                vehicle_ids=None,  # Auto-detect
                trail_seconds=15.0,
                compare="ref",
                out_dir=trails_dir,
                output_dir=data_dir
            )

            print(f"Generated {len(meta_df)} delta speed trails")

        except Exception as e:
            print(f"Error generating trails: {e}")
            import traceback
            traceback.print_exc()

    def _show_replay(self):
        """Create and show the replay UI."""
        data_dir = self.state_manager.output_dir

        # Hide loading screen
        self.loading_screen.hide()

        # Generate delta speed trails if needed
        self._generate_trails_if_needed(data_dir)

        # Load world model
        self.world = WorldModel(data_dir)
        self.world.load_theme_preference()  # Load saved theme
        self.world.load_trajectories()

        # --- New: basic world sanity check before enabling zoom/pan ---
        bounds = getattr(self.world, "bounds", None)
        required_keys = ("x_min", "x_max", "y_min", "y_max")

        if (
            isinstance(bounds, dict)
            and all(k in bounds for k in required_keys)
            and bounds["x_max"] != bounds["x_min"]
            and bounds["y_max"] != bounds["y_min"]
        ):
            enable_mouse_handlers = True
        else:
            enable_mouse_handlers = False
            print("[WARN] World bounds not valid; zoom/pan handlers disabled to avoid crashes.")

        # Calculate canvas size to fill available space
        # Use large dimensions - DearPyGUI will clip to container
        canvas_width = 2000
        canvas_height = 1500

        # Create main replay window
        with dpg.window(label="Race Replay", tag="main_window",
                       width=-1, height=-1, no_close=True,
                       no_title_bar=True, no_move=True):

            with dpg.group(horizontal=True, tag="main_layout"):
                # Left: Control panel with car selection, visual FX, and playback
                with dpg.child_window(width=280, height=-1, tag="control_panel"):
                    self.telemetry = TelemetryPanel(self.world)
                    self.telemetry.setup_ui()

                    # Separator before playback controls
                    dpg.add_spacer(height=20)
                    dpg.add_separator()
                    dpg.add_spacer(height=10)

                    # Playback controls at bottom of left panel
                    self.controls = PlaybackControls(self.world)
                    self.controls.setup_ui()

                dpg.add_spacer(width=5)

                # Right: Canvas (track display) - no border, fills space
                with dpg.child_window(width=-1, height=-1, border=False, tag="canvas_window",
                                      no_scrollbar=True, no_scroll_with_mouse=True):
                    dpg.add_drawlist(tag="canvas", width=canvas_width, height=canvas_height)

        # Init renderer - viewport dimensions will be set on first frame
        # from actual canvas_window size
        self.renderer = GPURenderer("canvas", self.world)

        # Initialize message overlay system
        init_message_overlay("canvas")

        # Connect renderer to telemetry panel and controls
        self.telemetry.renderer = self.renderer
        self.renderer.controls = self.controls

        # Register mouse event handlers for zoom/pan/HUD clicks
        with dpg.handler_registry():
            # Only enable zoom/pan if bounds are sane
            if enable_mouse_handlers:
                dpg.add_mouse_wheel_handler(callback=self.renderer.on_mouse_wheel)
                dpg.add_mouse_drag_handler(
                    button=dpg.mvMouseButton_Right,
                    callback=self.renderer.on_mouse_drag,
                )

            # HUD interactions are safe even with bad bounds
            dpg.add_mouse_drag_handler(
                button=dpg.mvMouseButton_Left,
                callback=self.renderer.on_hud_drag,
            )
            dpg.add_mouse_click_handler(
                button=dpg.mvMouseButton_Left,
                callback=self.renderer.on_mouse_click,
            )
            dpg.add_mouse_release_handler(
                button=dpg.mvMouseButton_Left,
                callback=self.renderer.on_mouse_release,
            )

            # ESC key handler for demo skip
            dpg.add_key_press_handler(
                key=dpg.mvKey_Escape,
                callback=self._on_escape_key
            )

        # Switch primary window
        dpg.set_primary_window("main_window", True)

        # Demo disabled for screenshot session
        print("\nApplication started. Press Play to begin simulation.")
        print("Controls:")
        print("  - Play/Pause: Control playback")
        print("  - Speed slider: Adjust playback speed (0.1x to 4x)")
        print("  - Time scrubber: Jump to specific time")
        print("  - Driving Style: Apply different driving modes")

    def _on_escape_key(self):
        """Handle ESC key press - skip demo if active."""
        if self.demo_manager and self.demo_manager.is_running:
            self.demo_manager.request_skip()

    def run(self):
        """Main render loop."""
        while dpg.is_dearpygui_running():
            # Update intro animation if running
            if self.show_intro and self.intro_animation:
                self.intro_animation.update()

            # Update transitions
            self.transitions.update()

            # Poll for drag-and-drop events
            if self.drop_handler:
                self.drop_handler.poll()

            # Update symbol animation during processing
            if self.state_manager.state == AppState.PROCESSING:
                self.loading_screen.update_animation()

            # Update replay if ready
            if self.state_manager.state == AppState.READY and self.renderer:
                # Update renderer viewport size from visible window area (not drawlist)
                canvas_rect = dpg.get_item_rect_size("canvas_window")
                if canvas_rect[0] > 0 and canvas_rect[1] > 0:
                    # Check if dimensions changed significantly (needs redraw)
                    old_w = self.renderer.viewport_width
                    old_h = self.renderer.viewport_height
                    new_w = canvas_rect[0]
                    new_h = canvas_rect[1]

                    if abs(new_w - old_w) > 10 or abs(new_h - old_h) > 10:
                        self.renderer.viewport_width = new_w
                        self.renderer.viewport_height = new_h
                        self.renderer.invalidate_track()
                    else:
                        self.renderer.viewport_width = new_w
                        self.renderer.viewport_height = new_h

                # Update simulation and render
                self.controls.update_simulation()
                self.renderer.render_frame()
                self.telemetry.update_telemetry()

                # Render message overlay on top of everything
                render_overlay()

                # Update FPS counter
                self.frame_count += 1
                current_time = time.time()

                # Update demo if active
                if self.demo_manager and self.demo_manager.is_running:
                    dt = current_time - self.last_fps_time if self.last_fps_time else 0.016
                    self.demo_manager.update(dt)
                    # Render demo cursor on top
                    self.demo_manager.render("canvas")
                if current_time - self.last_fps_time >= 1.0:
                    fps = self.frame_count / (current_time - self.last_fps_time)
                    dpg.set_viewport_title(f"Race Replay - Toyota GR86 | {fps:.0f} FPS | Time: {self.world.current_time_ms/1000:.1f}s")
                    self.frame_count = 0
                    self.last_fps_time = current_time

            # Render frame
            dpg.render_dearpygui_frame()

        # Cleanup
        if self.drop_handler:
            self.drop_handler.disable()
        dpg.destroy_context()


def main():
    """Main application entry point."""
    app = RaceReplayApp()
    app.setup()
    app.run()


if __name__ == '__main__':
    main()
