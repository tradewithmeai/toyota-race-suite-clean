"""Telemetry panel for displaying car data and display options."""

import dearpygui.dearpygui as dpg
from app.color_customization_menu import color_customization_menu


class TelemetryPanel:
    """Displays telemetry data and display options."""

    def __init__(self, world_model, renderer=None):
        self.world = world_model
        self.renderer = renderer
        self.selected_car = None

    def setup_ui(self):
        """Create control panel widgets."""
        # === VISUAL EFFECTS ===
        dpg.add_text("VISUAL EFFECTS", color=(255, 255, 0))
        dpg.add_separator()

        # Lateral Diff (deviation bars)
        dpg.add_checkbox(label="Lateral Diff", tag="lateral_diff_cb",
                        default_value=False, callback=self.toggle_lateral_diff)

        # Lateral Diff reference line dropdown
        dpg.add_combo(label="", tag="lateral_diff_reference",
                     items=["Racing Line", "Global Racing Line", "Individual Racing Lines"],
                     default_value="Racing Line",
                     callback=self.set_lateral_diff_reference, width=150)

        # Brake Arcs (outer expanding arcs showing front/rear brake pressure)
        dpg.add_checkbox(label="Brake Arcs", tag="circle_glow_cb",
                        default_value=False, callback=self.toggle_circle_glow)

        # Accel Fill (inner filled circle showing acceleration intensity)
        dpg.add_checkbox(label="Accel Fill", tag="circle_centre_cb",
                        default_value=False, callback=self.toggle_circle_centre)

        # Trail with mode dropdown
        dpg.add_checkbox(label="Trail", tag="trail_cb",
                        default_value=False, callback=self.toggle_trail)

        # Trail mode dropdown (only visible when trails enabled)
        dpg.add_combo(label="", tag="trail_mode",
                     items=["fade_3s", "fade_5s", "fade_10s", "Delta Speed"],
                     default_value="fade_3s",
                     callback=self.set_trail_mode, width=120, show=False)

        # Steering Angle
        dpg.add_checkbox(label="Steering Angle", tag="steering_angle_cb",
                        default_value=False, callback=self.toggle_steering_angle)

        dpg.add_spacer(height=15)

        # === TRACK DISPLAYS ===
        dpg.add_text("TRACK DISPLAYS", color=(255, 255, 0))
        dpg.add_separator()

        dpg.add_checkbox(label="Density Plot", tag="density_plot_cb",
                        default_value=True, callback=self.toggle_density_plot)

        dpg.add_checkbox(label="Racing Line", tag="racing_line_cb",
                        default_value=True, callback=self.toggle_racing_line)

        # Track Outline removed - code commented out
        # dpg.add_checkbox(label="Track Outline", tag="track_outline_cb",
        #                 default_value=False, callback=self.toggle_track_outline)

        dpg.add_checkbox(label="Global Racing Line", tag="global_racing_line_cb",
                        default_value=False, callback=self.toggle_global_racing_line)

        dpg.add_checkbox(label="Sector Lines", tag="sector_lines_cb",
                        default_value=False, callback=self.toggle_sector_lines)

        dpg.add_checkbox(label="Lap Delta Trail", tag="lap_delta_cb",
                        default_value=False, callback=self.toggle_lap_delta)

        dpg.add_spacer(height=15)

        # === LAP DELTA INFO (collapsible) ===
        with dpg.collapsing_header(label="LAP DELTA", default_open=False, tag="lap_delta_header"):
            dpg.add_text("Current Lap: -", tag="lap_delta_lap_text")
            dpg.add_text("Delta: --:--", tag="lap_delta_time_text")
            dpg.add_text("(vs previous lap)", tag="lap_delta_hint_text", color=(150, 150, 150))

        dpg.add_spacer(height=15)

        # === STATS (collapsible) ===
        with dpg.collapsing_header(label="STATS", default_open=False):
            dpg.add_text(f"Cars: {len(self.world.car_ids)}", tag="cars_count_text")
            dpg.add_text(f"Duration: {self.world.total_duration_ms/1000:.0f}s", tag="duration_text")
            dpg.add_text("Selected: 0", tag="selected_count_text")

        dpg.add_spacer(height=15)

        # === SECTOR TIMING (collapsible) ===
        with dpg.collapsing_header(label="SECTOR TIMING", default_open=False, tag="sector_timing_header"):
            # Check if sector data is available
            if self.world.sector_map is not None:
                dpg.add_text("Ideal Lap: 0.00s", tag="ideal_lap_time_text")
                dpg.add_text("Current Sector: -", tag="current_sector_text")
                dpg.add_text("Sector 1: --:--", tag="sector_1_text")
                dpg.add_text("Sector 2: --:--", tag="sector_2_text")
                dpg.add_text("Sector 3: --:--", tag="sector_3_text")
                dpg.add_text("Lap Time: --:--", tag="lap_time_text")
            else:
                dpg.add_text("Sector data not available", tag="sector_unavailable_text", color=(150, 150, 150))
                dpg.add_text("(requires section_compare processing)", tag="sector_hint_text", color=(100, 100, 100))

        dpg.add_spacer(height=15)

        # === THEME ===
        dpg.add_text("THEME", color=(255, 255, 0))
        dpg.add_separator()

        with dpg.group(horizontal=True):
            dpg.add_text("Dark")
            dpg.add_checkbox(label="", tag="theme_toggle",
                            default_value=False, callback=self.toggle_theme)
            dpg.add_text("Light")

        dpg.add_spacer(height=5)

        # Colour customisation button
        dpg.add_button(label="Visuals - Custom", callback=self.open_color_customization, width=-1)

        dpg.add_spacer(height=10)

        # Reset View button at bottom
        dpg.add_button(label="Reset View", callback=self.reset_view, width=-1)

    def update_telemetry(self):
        """Update telemetry display each frame."""
        if self.selected_car is None and self.world.car_ids:
            self.selected_car = self.world.car_ids[0]

        # Update selected count
        dpg.set_value("selected_count_text", f"Selected: {len(self.world.selected_car_ids)}")

        # Update sector timing display
        self.update_sector_timing()

        # Update lap delta display
        self.update_lap_delta()

    # === Visual Effects Callbacks ===

    def toggle_lateral_diff(self, sender, value):
        """Toggle lateral diff (deviation bars)."""
        self.world.show_lateral_diff = value
        # Auto-enable deviation in HUD when visualization is enabled
        if value:
            self.world.hud_show_deviation = True
            dpg.set_value("hud_deviation_cb", True)

    def set_lateral_diff_reference(self, sender, value):
        """Set the reference line for lateral diff calculation."""
        reference_map = {
            'Racing Line': 'racing_line',
            'Global Racing Line': 'global_racing_line',
            'Individual Racing Lines': 'individual',
        }
        self.world.lateral_diff_reference = reference_map.get(value, 'racing_line')
        print(f"Lateral diff reference: {self.world.lateral_diff_reference}")

    def toggle_circle_glow(self, sender, value):
        """Toggle circle glow (brakes)."""
        self.world.show_circle_glow = value
        # Also update legacy flag for backward compatibility
        self.world.show_braking_overlay = value
        # Auto-enable brake in HUD when visualization is enabled
        if value:
            self.world.hud_show_brake = True
            if dpg.does_item_exist("hud_brake_cb"):
                dpg.set_value("hud_brake_cb", True)

    def toggle_circle_centre(self, sender, value):
        """Toggle circle centre (placeholder)."""
        self.world.show_circle_centre = value

    def toggle_trail(self, sender, value):
        """Toggle trails visibility."""
        self.world.show_trail = value
        if value:
            # Enable trails with current mode
            self.world.trail_mode = dpg.get_value("trail_mode")
            dpg.configure_item("trail_mode", show=True)
        else:
            # Disable trails
            self.world.trail_mode = 'off'
            dpg.configure_item("trail_mode", show=False)

    def set_trail_mode(self, sender, mode):
        """Set trail mode."""
        self.world.trail_mode = mode

    def toggle_steering_angle(self, sender, value):
        """Toggle steering angle arrow."""
        self.world.show_steering_angle = value
        # Auto-enable steering in HUD when visualization is enabled
        if value:
            self.world.hud_show_steering = True
            dpg.set_value("hud_steering_cb", True)

    # === Track Display Callbacks ===

    def toggle_density_plot(self, sender, value):
        """Toggle density plot visibility."""
        self.world.show_density_plot = value
        # Invalidate track to trigger redraw
        if self.renderer is not None:
            self.renderer.invalidate_track()

    def toggle_racing_line(self, sender, value):
        """Toggle racing line visibility."""
        self.world.show_racing_line = value
        # Invalidate track to trigger redraw
        if self.renderer is not None:
            self.renderer.invalidate_track()

    def toggle_track_outline(self, sender, value):
        """Toggle track outline visibility (placeholder)."""
        self.world.show_track_outline = value
        # Invalidate track to trigger redraw
        if self.renderer is not None:
            self.renderer.invalidate_track()

    def toggle_global_racing_line(self, sender, value):
        """Toggle global racing line visibility (neon green)."""
        self.world.show_global_racing_line = value
        # Invalidate track to trigger redraw
        if self.renderer is not None:
            self.renderer.invalidate_track()

    def toggle_sector_lines(self, sender, value):
        """Toggle sector boundary lines on track."""
        self.world.show_sector_lines = value
        # Invalidate track to trigger redraw
        if self.renderer is not None:
            self.renderer.invalidate_track()

    def toggle_lap_delta(self, sender, value):
        """Toggle lap delta trail visualization."""
        self.world.show_lap_delta = value

    def reset_view(self):
        """Reset zoom and pan to default view."""
        if self.renderer is not None:
            self.renderer.reset_view()

    def open_color_customization(self, sender=None, app_data=None):
        """Open the color customization menu."""
        color_customization_menu.open(
            world=self.world,
            on_colors_changed=self._on_colors_changed
        )

    def _on_colors_changed(self):
        """Handle color changes from customization menu."""
        # Invalidate track to redraw with new colors
        if self.renderer is not None:
            self.renderer.invalidate_track()

    # === HUD Settings Callbacks ===

    def toggle_hud_speed(self, sender, value):
        """Toggle speed display in HUD."""
        self.world.hud_show_speed = value

    def toggle_hud_gear(self, sender, value):
        """Toggle gear display in HUD."""
        self.world.hud_show_gear = value

    def toggle_hud_brake(self, sender, value):
        """Toggle brake display in HUD."""
        self.world.hud_show_brake = value

    def toggle_hud_lap(self, sender, value):
        """Toggle lap display in HUD."""
        self.world.hud_show_lap = value

    def toggle_hud_time(self, sender, value):
        """Toggle time display in HUD."""
        self.world.hud_show_time = value

    def toggle_hud_position(self, sender, value):
        """Toggle position display in HUD."""
        self.world.hud_show_position = value

    def toggle_hud_deviation(self, sender, value):
        """Toggle deviation display in HUD."""
        self.world.hud_show_deviation = value

    def toggle_hud_steering(self, sender, value):
        """Toggle steering display in HUD."""
        self.world.hud_show_steering = value

    # === Theme Callback ===

    def toggle_theme(self, sender, value):
        """Toggle between dark and light themes."""
        new_theme = self.world.toggle_theme()
        # Invalidate track to force full redraw with new theme
        if self.renderer is not None:
            self.renderer.invalidate_track()
        print(f"Theme changed to: {new_theme}")

    # === Sector Timing Updates ===

    def update_sector_timing(self):
        """Update sector timing display based on selected car and current time."""
        # Only update if sector data is available
        if self.world.sector_map is None:
            return

        # Only update if we have a selected car
        if not self.world.selected_car_ids:
            return

        car_id = list(self.world.selected_car_ids)[0]  # Use first selected car

        try:
            # Update ideal lap time
            if dpg.does_item_exist("ideal_lap_time_text"):
                ideal_time = self.world.ideal_lap_time_s
                dpg.set_value("ideal_lap_time_text", f"Ideal Lap: {ideal_time:.2f}s")

            # Get current sector
            current_sector = self.world.get_current_sector(car_id)
            if dpg.does_item_exist("current_sector_text"):
                dpg.set_value("current_sector_text", f"Current Sector: {current_sector}")

            # Get sector times for the current lap
            if car_id in self.world.car_sector_times:
                laps = sorted(self.world.car_sector_times[car_id].keys())
                if laps:
                    # Get the latest lap with sector data
                    latest_lap = laps[-1]
                    sector_times = self.world.car_sector_times[car_id][latest_lap]

                    # Get best sectors for comparison
                    best_sectors = self.world.car_best_sectors.get(car_id, [float('inf')] * 3)
                    overall_best = self.world.overall_best_sectors

                    # Update each sector
                    for i in range(min(3, len(sector_times))):
                        sector_time = sector_times[i]
                        if sector_time is not None:
                            # Calculate delta to personal best
                            delta_pb = sector_time - best_sectors[i] if best_sectors[i] < float('inf') else 0
                            delta_ob = sector_time - overall_best[i] if overall_best[i] < float('inf') else 0

                            # Color code based on delta
                            if delta_pb < -0.05:  # Significantly faster than PB
                                color = (0, 255, 0)  # Green
                            elif delta_pb > 0.05:  # Slower than PB
                                color = (255, 100, 100)  # Red
                            else:
                                color = (200, 200, 200)  # Gray

                            # Format text
                            text = f"Sector {i+1}: {sector_time:.2f}s"
                            if abs(delta_pb) > 0.001:
                                text += f" ({delta_pb:+.2f})"

                            tag = f"sector_{i+1}_text"
                            if dpg.does_item_exist(tag):
                                dpg.set_value(tag, text)
                                dpg.configure_item(tag, color=color)

                    # Calculate lap time
                    if all(t is not None for t in sector_times[:3]):
                        lap_time = sum(sector_times[:3])
                        if dpg.does_item_exist("lap_time_text"):
                            dpg.set_value("lap_time_text", f"Lap Time: {lap_time:.2f}s")

        except Exception as e:
            # Silently handle errors to avoid spamming console
            pass

    def update_lap_delta(self):
        """Update lap delta display based on selected car."""
        # Only update if we have a selected car
        if not self.world.selected_car_ids:
            # Clear display
            if dpg.does_item_exist("lap_delta_lap_text"):
                dpg.set_value("lap_delta_lap_text", "Current Lap: -")
            if dpg.does_item_exist("lap_delta_time_text"):
                dpg.set_value("lap_delta_time_text", "Delta: --:--")
            return

        car_id = list(self.world.selected_car_ids)[0]  # Use first selected car

        try:
            # Get lap delta data
            delta_data = self.world.get_lap_delta_data(car_id)

            # Update lap number
            if dpg.does_item_exist("lap_delta_lap_text"):
                current_lap = delta_data['current_lap']
                dpg.set_value("lap_delta_lap_text", f"Current Lap: {current_lap}")

            # Update delta time
            if dpg.does_item_exist("lap_delta_time_text"):
                if delta_data['has_delta']:
                    delta_s = delta_data['delta_seconds']

                    # Color code based on delta
                    if delta_s < -0.05:  # Faster
                        color = (0, 255, 0)  # Green
                    elif delta_s > 0.05:  # Slower
                        color = (255, 100, 100)  # Red
                    else:
                        color = (200, 200, 200)  # Gray

                    # Format delta with +/- sign
                    sign = "+" if delta_s >= 0 else ""
                    dpg.set_value("lap_delta_time_text", f"Delta: {sign}{delta_s:.3f}s")
                    dpg.configure_item("lap_delta_time_text", color=color)
                else:
                    # No delta available (lap 1 or no previous lap)
                    dpg.set_value("lap_delta_time_text", "Delta: N/A (Lap 1)")
                    dpg.configure_item("lap_delta_time_text", color=(150, 150, 150))

        except Exception as e:
            # Silently handle errors
            pass

