"""Playback controls for simulation."""

import time
import dearpygui.dearpygui as dpg


class PlaybackControls:
    """Manages playback state and UI controls."""

    def __init__(self, world_model):
        self.world = world_model
        self.is_playing = False
        self.speed_factor = 1.0
        self.last_frame_time = time.time()

    def setup_ui(self):
        """Create control widgets."""
        with dpg.group(horizontal=True):
            dpg.add_button(label="Play", callback=self.play, width=80)
            dpg.add_button(label="Pause", callback=self.pause, width=80)
            dpg.add_button(label="Restart", callback=self.restart, width=80)

        dpg.add_spacer(height=10)

        dpg.add_slider_float(label="Speed", tag="speed_slider",
                            default_value=1.0, min_value=0.1, max_value=4.0,
                            callback=self.set_speed, width=300)

        dpg.add_slider_int(label="Time (s)", tag="time_scrubber",
                          default_value=0, min_value=0,
                          max_value=int(self.world.total_duration_ms // 1000),
                          callback=self.scrub_time, width=300)

    def update_simulation(self):
        """Called each frame to update simulation time."""
        if self.is_playing:
            current_time = time.time()
            dt_real = current_time - self.last_frame_time
            self.last_frame_time = current_time

            # Update simulation time
            dt_ms = dt_real * 1000 * self.speed_factor
            self.world.current_time_ms += dt_ms

            # Clamp to race duration
            if self.world.current_time_ms >= self.world.total_duration_ms:
                self.world.current_time_ms = self.world.total_duration_ms
                self.is_playing = False

            # Update scrubber
            dpg.set_value("time_scrubber", int(self.world.current_time_ms // 1000))

    def play(self):
        """Start playback."""
        self.is_playing = True
        self.last_frame_time = time.time()

    def pause(self):
        """Pause playback."""
        self.is_playing = False

    def restart(self):
        """Restart from beginning."""
        self.world.current_time_ms = 0
        self.is_playing = False
        dpg.set_value("time_scrubber", 0)

    def set_speed(self, sender, speed):
        """Set playback speed."""
        self.speed_factor = speed

    def scrub_time(self, sender, time_s):
        """Scrub to specific time."""
        self.world.current_time_ms = time_s * 1000
