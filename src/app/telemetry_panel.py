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

        # Sector Lines removed - code commented out
        # dpg.add_checkbox(label="Sector Lines", tag="sector_lines_cb",
        #                 default_value=False, callback=self.toggle_sector_lines)

        dpg.add_spacer(height=15)

        # === STATS (collapsible) ===
        with dpg.collapsing_header(label="STATS", default_open=False):
            dpg.add_text(f"Cars: {len(self.world.car_ids)}", tag="cars_count_text")
            dpg.add_text(f"Duration: {self.world.total_duration_ms/1000:.0f}s", tag="duration_text")
            dpg.add_text("Selected: 0", tag="selected_count_text")

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

