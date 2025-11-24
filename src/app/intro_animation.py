"""Intro animation screen with ASCII art and keyboard symbol effects."""

import time
import dearpygui.dearpygui as dpg
import math


class IntroAnimation:
    """Displays an animated intro screen with ASCII art."""

    def __init__(self, on_complete_callback):
        """
        Initialize the intro animation.

        Args:
            on_complete_callback: Function to call when animation completes
        """
        self.on_complete = on_complete_callback
        self.window_tag = "intro_window"
        self.start_time = None
        self.duration_ms = 3500  # Total animation duration
        self.is_running = False

        # ASCII art frames for the race car animation
        self.car_frames = [
            "    ______________",
            "   /|            |\\",
            "  /_|____________|_\\",
            " |  ____________  |",
            " | |    GR86    | |",
            " | |____________| |",
            "  \\______________/",
            "   (O)        (O)",
        ]

        # Racing flag pattern
        self.flag_pattern = [
            "##  ##  ##  ##",
            "  ##  ##  ##  ",
            "##  ##  ##  ##",
            "  ##  ##  ##  ",
        ]

        # Keyboard symbols for particle effects
        self.particles = ['*', '+', 'x', 'o', '.', ':', '|', '/', '\\', '-', '=']

    def setup_ui(self):
        """Create the intro animation window."""
        with dpg.window(label="Intro", tag=self.window_tag,
                       width=-1, height=-1, no_close=True,
                       no_title_bar=True, no_move=True, no_scrollbar=True):

            # Dark background
            dpg.add_spacer(height=50)

            # Main content centered
            with dpg.group(horizontal=False, tag="intro_content"):
                # Racing flags top
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=100)
                    dpg.add_text("", tag="flag_top", color=(255, 255, 255))

                dpg.add_spacer(height=30)

                # Title area with animation
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=80)
                    with dpg.group(horizontal=False):
                        dpg.add_text("", tag="title_line_1", color=(255, 200, 0))
                        dpg.add_text("", tag="title_line_2", color=(255, 200, 0))
                        dpg.add_text("", tag="title_line_3", color=(255, 200, 0))

                dpg.add_spacer(height=20)

                # ASCII car
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=120)
                    with dpg.group(horizontal=False):
                        for i in range(8):
                            dpg.add_text("", tag=f"car_line_{i}", color=(200, 200, 200))

                dpg.add_spacer(height=20)

                # Subtitle / tagline
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=100)
                    dpg.add_text("", tag="subtitle", color=(150, 150, 150))

                dpg.add_spacer(height=30)

                # Racing flags bottom
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=100)
                    dpg.add_text("", tag="flag_bottom", color=(255, 255, 255))

                dpg.add_spacer(height=50)

                # Loading indicator
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=200)
                    dpg.add_text("", tag="loading_indicator", color=(100, 100, 100))

    def start(self):
        """Start the intro animation."""
        self.start_time = time.time()
        self.is_running = True

    def update(self):
        """Update animation frame. Call this from main render loop."""
        if not self.is_running or self.start_time is None:
            return

        elapsed_ms = (time.time() - self.start_time) * 1000

        # Check if animation is complete
        if elapsed_ms >= self.duration_ms:
            self.is_running = False
            if self.on_complete:
                self.on_complete()
            return

        # Calculate animation phases
        progress = elapsed_ms / self.duration_ms

        # Phase 1: Title reveal (0-30%)
        if progress < 0.3:
            phase_progress = progress / 0.3
            self._animate_title_reveal(phase_progress)

        # Phase 2: Car reveal (20-60%)
        if 0.2 <= progress < 0.6:
            phase_progress = (progress - 0.2) / 0.4
            self._animate_car_reveal(phase_progress)

        # Phase 3: Full display with effects (50-90%)
        if 0.5 <= progress < 0.9:
            phase_progress = (progress - 0.5) / 0.4
            self._animate_full_display(phase_progress, elapsed_ms)

        # Phase 4: Fade out (85-100%)
        if progress >= 0.85:
            phase_progress = (progress - 0.85) / 0.15
            self._animate_fade_out(phase_progress)

        # Update loading indicator throughout
        self._update_loading_indicator(elapsed_ms)

    def _animate_title_reveal(self, progress):
        """Animate the title text appearing character by character."""
        title_lines = [
            "  ____   _    ____ _____   ____  _____ ____  _        _ __   __",
            " |  _ \\ / \\  / ___| ____| |  _ \\| ____|  _ \\| |      / \\\\ \\ / /",
            " | |_) / _ \\| |   |  _|   | |_) |  _| | |_) | |     / _ \\\\ V / ",
        ]

        # Simple version for cleaner look
        title_simple = [
            "####  ###  ### ###   ####  #### ####  #    ###  #   #",
            "#   # #  # #   #     #   # #    #   # #   #   #  # # ",
            "####  ###  #   ##    ####  ###  ####  #   #####   #  ",
        ]

        # Even simpler - just the text
        title_text = [
            "R A C E",
            "R E P L A Y",
            ""
        ]

        chars_to_show = int(progress * 12)  # Max chars per line

        for i, line in enumerate(title_text):
            if i < len(title_text):
                visible = line[:chars_to_show] if chars_to_show < len(line) else line
                dpg.set_value(f"title_line_{i+1}", visible)

    def _animate_car_reveal(self, progress):
        """Animate the ASCII car appearing line by line."""
        lines_to_show = int(progress * len(self.car_frames))

        for i in range(len(self.car_frames)):
            if i < lines_to_show:
                dpg.set_value(f"car_line_{i}", self.car_frames[i])
            else:
                dpg.set_value(f"car_line_{i}", "")

    def _animate_full_display(self, progress, elapsed_ms):
        """Display full content with animated effects."""
        # Full title
        dpg.set_value("title_line_1", "R A C E")
        dpg.set_value("title_line_2", "R E P L A Y")
        dpg.set_value("title_line_3", "")

        # Full car
        for i in range(len(self.car_frames)):
            dpg.set_value(f"car_line_{i}", self.car_frames[i])

        # Animated subtitle
        subtitles = [
            "Toyota GR86 Cup Telemetry",
            ">> Toyota GR86 Cup Telemetry <<",
            ">>> Toyota GR86 Cup Telemetry <<<",
            ">> Toyota GR86 Cup Telemetry <<",
        ]
        subtitle_idx = int((elapsed_ms / 200) % len(subtitles))
        dpg.set_value("subtitle", subtitles[subtitle_idx])

        # Animated racing flags
        flag_offset = int((elapsed_ms / 100) % 2)
        if flag_offset == 0:
            dpg.set_value("flag_top", "##  ##  ##  ##  ##  ##")
            dpg.set_value("flag_bottom", "  ##  ##  ##  ##  ##  ")
        else:
            dpg.set_value("flag_top", "  ##  ##  ##  ##  ##  ")
            dpg.set_value("flag_bottom", "##  ##  ##  ##  ##  ##")

    def _animate_fade_out(self, progress):
        """Fade out effect by changing colors."""
        # Gradually dim the colors
        intensity = int(255 * (1 - progress))
        yellow_intensity = int(200 * (1 - progress))

        # Update title color
        if dpg.does_item_exist("title_line_1"):
            dpg.configure_item("title_line_1", color=(intensity, yellow_intensity, 0))
            dpg.configure_item("title_line_2", color=(intensity, yellow_intensity, 0))

        # Update car color
        car_intensity = int(200 * (1 - progress))
        for i in range(8):
            if dpg.does_item_exist(f"car_line_{i}"):
                dpg.configure_item(f"car_line_{i}", color=(car_intensity, car_intensity, car_intensity))

        # Update subtitle
        sub_intensity = int(150 * (1 - progress))
        if dpg.does_item_exist("subtitle"):
            dpg.configure_item("subtitle", color=(sub_intensity, sub_intensity, sub_intensity))

        # Update flags
        flag_intensity = int(255 * (1 - progress))
        if dpg.does_item_exist("flag_top"):
            dpg.configure_item("flag_top", color=(flag_intensity, flag_intensity, flag_intensity))
            dpg.configure_item("flag_bottom", color=(flag_intensity, flag_intensity, flag_intensity))

    def _update_loading_indicator(self, elapsed_ms):
        """Update the loading dots animation."""
        dots = int((elapsed_ms / 300) % 4)
        indicator = "Loading" + "." * dots + " " * (3 - dots)
        dpg.set_value("loading_indicator", indicator)

    def show(self):
        """Show the intro window."""
        if dpg.does_item_exist(self.window_tag):
            dpg.show_item(self.window_tag)

    def hide(self):
        """Hide the intro window."""
        if dpg.does_item_exist(self.window_tag):
            dpg.hide_item(self.window_tag)

    def cleanup(self):
        """Clean up the intro window."""
        if dpg.does_item_exist(self.window_tag):
            dpg.delete_item(self.window_tag)
