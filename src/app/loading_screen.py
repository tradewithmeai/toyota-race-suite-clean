"""Loading screen UI for file drop and processing progress."""

import os
import json
import time
import dearpygui.dearpygui as dpg
from app.app_state import StateManager, AppState
from app.symbol_animation import SymbolAnimator


class LoadingScreen:
    """Handles the loading/file drop screen UI."""

    def __init__(self, state_manager: StateManager):
        self.state = state_manager
        self.window_tag = "loading_window"
        self.is_dragging_over = False
        self.log_messages = []  # Store log messages for terminal display

        # Symbol animation
        self.animator = None
        self.last_update_time = time.time()
        self.animation_canvas_tag = "symbol_animation_canvas"
        self.background_drawlist_created = False

        # Portrait image path
        self.portrait_path = os.path.join(
            os.path.dirname(__file__), '..', '..', 'docs',
            'ASCII Toyota Logo in Beige Tones.png'
        )

        # Theme for transparent window background
        self.transparent_theme = None

    def setup_ui(self):
        """Create the loading screen UI."""
        with dpg.window(label="Race Replay", tag=self.window_tag,
                       width=-1, height=-1, no_close=True,
                       no_title_bar=True, no_move=True):

            # Center content vertically
            dpg.add_spacer(height=100)

            # Main content group (centered horizontally)
            with dpg.group(horizontal=False):
                # App title and logo area
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=80)
                    with dpg.group(horizontal=False):
                        dpg.add_text("RACE REPLAY", tag="title_text",
                                    color=(255, 200, 0))
                        dpg.add_text("Toyota GR86 Cup Telemetry Simulator",
                                    color=(150, 150, 150))
                        dpg.add_text("v1.0.0", color=(100, 100, 100))

                dpg.add_spacer(height=40)

                # State-specific content container
                with dpg.group(tag="state_content"):
                    self._create_waiting_content()

    def _create_waiting_content(self):
        """Create content for waiting for file state."""
        # Clear existing content
        if dpg.does_item_exist("waiting_group"):
            dpg.delete_item("waiting_group")
        if dpg.does_item_exist("processing_group"):
            dpg.delete_item("processing_group")
        if dpg.does_item_exist("error_group"):
            dpg.delete_item("error_group")

        with dpg.group(tag="waiting_group", parent="state_content"):
            # Load options section
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=50)
                with dpg.group(horizontal=False):
                    dpg.add_text("SELECT DATA TO LOAD", color=(255, 200, 0))
                    dpg.add_separator()
                    dpg.add_spacer(height=20)

                    # Track if any options are available
                    has_options = False

                    # Browse for processed data button
                    dpg.add_button(label="Browse for Processed Data",
                                  callback=self._open_processed_dialog,
                                  width=420, height=50)
                    dpg.add_spacer(height=15)
                    has_options = True

                    # Browse for raw CSV button
                    dpg.add_button(label="Browse for Raw CSV",
                                  callback=self._open_file_dialog,
                                  width=420, height=50)
                    dpg.add_spacer(height=15)
                    has_options = True

                    # Demo data button (pre-processed) - optional shortcut
                    # Use current working directory (set by main.py for PyInstaller)
                    demo_path = os.path.join(os.getcwd(), 'data', 'processed')
                    if os.path.exists(os.path.join(demo_path, 'metadata.json')):
                        dpg.add_button(label="Load Demo Data (Quick Start)",
                                      callback=self._load_demo_data,
                                      width=420, height=40)
                        dpg.add_spacer(height=10)

                    # Sample CSV button (needs processing) - optional shortcut
                    sample_csv = os.path.join(os.getcwd(), 'data', 'raw', 'R2_barber_telemetry_data.csv')
                    if os.path.exists(sample_csv):
                        dpg.add_button(label="Process Sample CSV (Quick Start)",
                                      callback=self._load_sample_csv,
                                      width=420, height=40)
                        dpg.add_spacer(height=10)

            dpg.add_spacer(height=30)

            # Footer
            with dpg.group(horizontal=True):
                dpg.add_spacer(width=80)
                dpg.add_text("Toyota Race Suite v1.0",
                            color=(100, 100, 100))

    def _create_processing_content(self):
        """Create content for processing state."""
        # Clear existing content
        if dpg.does_item_exist("waiting_group"):
            dpg.delete_item("waiting_group")
        if dpg.does_item_exist("processing_group"):
            dpg.delete_item("processing_group")
        if dpg.does_item_exist("error_group"):
            dpg.delete_item("error_group")

        # Clear log messages for fresh start
        self.log_messages = []

        # Get viewport size for fullscreen background animation
        viewport_width = dpg.get_viewport_width() or 1280
        viewport_height = dpg.get_viewport_height() or 720

        # Create transparent theme for window during processing
        if self.transparent_theme is None:
            with dpg.theme() as self.transparent_theme:
                with dpg.theme_component(dpg.mvAll):
                    dpg.add_theme_color(dpg.mvThemeCol_WindowBg, (20, 15, 10, 0), category=dpg.mvThemeCat_Core)
                    dpg.add_theme_color(dpg.mvThemeCol_ChildBg, (30, 25, 20, 200), category=dpg.mvThemeCat_Core)

        # Apply transparent theme to window
        dpg.bind_item_theme(self.window_tag, self.transparent_theme)

        # Create foreground viewport drawlist (renders behind windows with transparent bg)
        if not self.background_drawlist_created:
            dpg.add_viewport_drawlist(front=False, tag=self.animation_canvas_tag)
            self.background_drawlist_created = True
        else:
            # Clear existing items if reusing
            if dpg.does_item_exist(self.animation_canvas_tag):
                dpg.delete_item(self.animation_canvas_tag, children_only=True)

        # Draw WHITE background on viewport drawlist to test visibility
        dpg.draw_rectangle([0, 0], [viewport_width, viewport_height],
                          fill=(255, 255, 255, 255),
                          parent=self.animation_canvas_tag)

        with dpg.group(tag="processing_group", parent="state_content"):
            # Top-center layout for controls
            dpg.add_spacer(height=20)

            # Center horizontally
            with dpg.group(horizontal=True):
                # Calculate center offset
                center_offset = (viewport_width - 420) // 2
                dpg.add_spacer(width=max(50, center_offset - 50))

                with dpg.group(horizontal=False):
                    # Progress bar
                    dpg.add_progress_bar(tag="progress_bar",
                                        default_value=0.0,
                                        width=420)

                    dpg.add_spacer(height=8)

                    # Current status message
                    dpg.add_text("Initializing...", tag="progress_text",
                                color=(150, 150, 150))

                    dpg.add_spacer(height=10)

                    # Compact log output
                    with dpg.child_window(width=420, height=80, tag="log_window",
                                         border=True, horizontal_scrollbar=False):
                        dpg.add_text("", tag="log_text", color=(180, 180, 180), wrap=400)

        # Initialize the symbol animator with full viewport dimensions
        self.animator = SymbolAnimator(self.animation_canvas_tag, width=viewport_width, height=viewport_height)
        self.animator.load_portrait(self.portrait_path)
        self.last_update_time = time.time()

    def append_log_message(self, message: str):
        """Append a message to the terminal log."""
        self.log_messages.append(message)
        # Keep only last 50 messages to prevent memory issues
        if len(self.log_messages) > 50:
            self.log_messages = self.log_messages[-50:]

        # Update the log text display
        if dpg.does_item_exist("log_text"):
            log_content = "\n".join(self.log_messages)
            dpg.set_value("log_text", log_content)

            # Auto-scroll to bottom
            if dpg.does_item_exist("log_window"):
                dpg.set_y_scroll("log_window", dpg.get_y_scroll_max("log_window"))

    def _create_error_content(self):
        """Create content for error state."""
        # Clear existing content
        if dpg.does_item_exist("waiting_group"):
            dpg.delete_item("waiting_group")
        if dpg.does_item_exist("processing_group"):
            dpg.delete_item("processing_group")
        if dpg.does_item_exist("error_group"):
            dpg.delete_item("error_group")

        with dpg.group(tag="error_group", parent="state_content"):
            dpg.add_text("Error", color=(255, 100, 100))
            dpg.add_spacer(height=10)

            error_msg = self.state.error_message or "Unknown error"
            dpg.add_text(error_msg, tag="error_text",
                        color=(255, 150, 150), wrap=400)

            dpg.add_spacer(height=20)

            dpg.add_button(label="Try Again",
                          callback=self._retry,
                          width=150)

    def update_for_state(self, state: AppState):
        """Update UI for current state."""
        if state == AppState.WAITING_FOR_FILE:
            self._create_waiting_content()
        elif state == AppState.PROCESSING:
            self._create_processing_content()
        elif state == AppState.ERROR:
            self._create_error_content()

    def update_progress(self, message: str, percent: float):
        """Update progress bar, status message, and append to log."""
        if dpg.does_item_exist("progress_bar"):
            dpg.set_value("progress_bar", percent)
        if dpg.does_item_exist("progress_text"):
            dpg.set_value("progress_text", message)
        # Append to terminal log
        self.append_log_message(message)

        # Update symbol animation
        if self.animator:
            self.animator.set_progress(percent)

    def update_animation(self):
        """Update the symbol animation (call this each frame during processing)."""
        if not self.animator:
            return

        current_time = time.time()
        dt = current_time - self.last_update_time
        self.last_update_time = current_time

        # Cap dt to avoid jumps
        dt = min(dt, 0.1)

        self.animator.update(dt)
        self.animator.draw()

    def _load_demo_data(self):
        """Load the bundled demo data."""
        demo_path = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'processed')
        demo_path = os.path.abspath(demo_path)
        metadata_path = os.path.join(demo_path, 'metadata.json')

        if os.path.exists(metadata_path):
            self.state.set_processed_dir(demo_path)
        else:
            self.state.set_error(f"Demo data not found:\n{demo_path}")

    def _load_sample_csv(self):
        """Load and process the sample CSV file."""
        sample_csv = os.path.join(os.path.dirname(__file__), '..', '..', 'data', 'raw', 'R2_barber_telemetry_data.csv')
        sample_csv = os.path.abspath(sample_csv)

        if os.path.exists(sample_csv):
            self._validate_and_load_csv(sample_csv)
        else:
            self.state.set_error(f"Sample CSV not found:\n{sample_csv}")

    def _open_file_dialog(self):
        """Open file dialog for selecting CSV."""
        def file_selected(sender, app_data):
            if app_data and 'file_path_name' in app_data:
                file_path = app_data['file_path_name']
                self._validate_and_load_csv(file_path)

        # Create file dialog
        with dpg.file_dialog(label="Select Telemetry CSV",
                            callback=file_selected,
                            width=700, height=400,
                            modal=True):
            dpg.add_file_extension(".csv", color=(0, 255, 0))

    def _open_processed_dialog(self):
        """Open directory dialog for selecting processed data folder."""
        def dir_selected(sender, app_data):
            if app_data and 'file_path_name' in app_data:
                dir_path = app_data['file_path_name']
                # Verify it's a valid processed data directory
                metadata_path = os.path.join(dir_path, 'metadata.json')
                if os.path.exists(metadata_path):
                    self.state.set_processed_dir(dir_path)
                else:
                    self.state.set_error(f"Invalid processed data folder:\n{dir_path}\n\nMissing metadata.json")

        # Create directory dialog
        with dpg.file_dialog(label="Select Processed Data Folder",
                            callback=dir_selected,
                            width=700, height=400,
                            modal=True,
                            directory_selector=True):
            pass

    def _validate_and_load_csv(self, file_path: str):
        """Validate CSV format before loading."""
        # Import validation function
        try:
            from processing.load_raw_data import validate_csv_format
        except ImportError:
            # Fallback if import fails - just load without validation
            self.state.set_input_file(file_path)
            return

        # Validate CSV format
        is_valid, message = validate_csv_format(file_path)

        if is_valid:
            print(f"✓ CSV validation passed: {message}")
            self.state.set_input_file(file_path)
        else:
            print(f"✗ CSV validation failed: {message}")
            self.state.set_error(f"Invalid CSV format:\n\n{message}")

    def _retry(self):
        """Reset state to try again."""
        self.state.reset()

    def show(self):
        """Show the loading window."""
        if dpg.does_item_exist(self.window_tag):
            dpg.show_item(self.window_tag)

    def hide(self):
        """Hide the loading window."""
        if dpg.does_item_exist(self.window_tag):
            dpg.hide_item(self.window_tag)
        # Hide/clear the background animation
        if dpg.does_item_exist(self.animation_canvas_tag):
            dpg.delete_item(self.animation_canvas_tag, children_only=True)

    def handle_file_drop(self, file_path: str):
        """Handle a dropped file or folder."""
        if os.path.isdir(file_path):
            # Check if it's a processed data directory
            metadata_path = os.path.join(file_path, 'metadata.json')
            if os.path.exists(metadata_path):
                self.state.set_processed_dir(file_path)
            else:
                self.state.set_error(f"Invalid folder:\n{file_path}\n\nMissing metadata.json")
        elif file_path.lower().endswith('.csv'):
            # Validate CSV before loading
            self._validate_and_load_csv(file_path)
        else:
            self.state.set_error(f"Invalid file type: {file_path}\n\nPlease drop a .csv file or processed data folder.")
