"""Playback controls for simulation."""

import time
import dearpygui.dearpygui as dpg


class PlaybackControls:
    """Manages playback state and UI controls."""

    def __init__(self, world_model, screenshot_callback=None, video_exporter=None):
        self.world = world_model
        self.is_playing = False
        self.speed_factor = 1.0
        self.last_frame_time = time.time()
        self.screenshot_callback = screenshot_callback
        self.video_exporter = video_exporter

    def setup_ui(self):
        """Create control widgets."""
        with dpg.group(horizontal=True):
            dpg.add_button(label="Play", callback=self.play, width=80)
            dpg.add_button(label="Pause", callback=self.pause, width=80)
            dpg.add_button(label="Restart", callback=self.restart, width=80)

        dpg.add_spacer(height=10)

        # Screenshot button
        if self.screenshot_callback is not None:
            dpg.add_button(label="Screenshot (F12)", callback=self._take_screenshot, width=250)
            dpg.add_spacer(height=10)

        # Video recording button
        if self.video_exporter is not None:
            dpg.add_button(
                label="Start Recording",
                tag="video_record_button",
                callback=self._toggle_recording,
                width=250
            )
            dpg.add_text("", tag="recording_status_text", color=(150, 150, 150))
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

    def _take_screenshot(self, sender=None, app_data=None):
        """Handle screenshot button click."""
        if self.screenshot_callback:
            self.screenshot_callback()

    def _toggle_recording(self, sender=None, app_data=None):
        """Toggle video recording on/off."""
        if not self.video_exporter:
            return

        if not self.video_exporter.is_recording:
            # Start recording
            success = self.video_exporter.start_recording()
            if success:
                dpg.set_item_label("video_record_button", "Stop Recording")
                dpg.set_value("recording_status_text", "Recording...")
                dpg.configure_item("recording_status_text", color=(255, 100, 100))
        else:
            # Stop recording
            output_path = self.video_exporter.stop_recording()
            dpg.set_item_label("video_record_button", "Start Recording")
            if output_path:
                import os
                filename = os.path.basename(output_path)
                dpg.set_value("recording_status_text", f"Saved: {filename}")
                dpg.configure_item("recording_status_text", color=(100, 255, 100))
            else:
                dpg.set_value("recording_status_text", "Recording failed")
                dpg.configure_item("recording_status_text", color=(255, 100, 100))

    def update_recording_status(self):
        """Update recording status display."""
        if not self.video_exporter or not self.video_exporter.is_recording:
            return

        status = self.video_exporter.get_recording_status()
        frame_count = status['frame_count']
        duration = status['duration']

        dpg.set_value("recording_status_text", f"Recording: {frame_count} frames ({duration:.1f}s)")

    def capture_video_frame(self):
        """Capture frame if recording."""
        if self.video_exporter and self.video_exporter.is_recording:
            self.video_exporter.capture_frame()
