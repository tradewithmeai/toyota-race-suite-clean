"""Lap delta trail renderer - visualizes time delta vs previous lap."""

import dearpygui.dearpygui as dpg
import numpy as np


class LapDeltaRenderer:
    """Renders colored trail showing lap-to-lap time delta."""

    def __init__(self):
        """Initialize lap delta renderer."""
        self.trail_thickness = 4.0
        self.fade_enabled = True

    def render(self, world, camera, canvas_tag="canvas"):
        """Render lap delta trails for all selected cars.

        Args:
            world: WorldModel instance
            camera: Camera transform parameters
            canvas_tag: DearPyGUI canvas tag
        """
        if not world.show_lap_delta:
            return

        for car_id in world.selected_car_ids:
            self._render_car_delta(world, car_id, camera, canvas_tag)

    def _render_car_delta(self, world, car_id, camera, canvas_tag):
        """Render lap delta trail for a single car.

        Args:
            world: WorldModel instance
            car_id: Vehicle ID
            camera: Camera transform parameters
            canvas_tag: DearPyGUI canvas tag
        """
        # Get lap delta data
        delta_data = world.get_lap_delta_data(car_id)

        if not delta_data['has_delta']:
            return

        trail_points = delta_data['trail_points']
        if len(trail_points) < 2:
            return

        # Render trail segments
        for i in range(len(trail_points) - 1):
            x1, y1, delta1 = trail_points[i]
            x2, y2, delta2 = trail_points[i + 1]

            # Average delta for this segment
            avg_delta = (delta1 + delta2) / 2.0

            # Color based on delta
            color = self._delta_to_color(avg_delta)

            # Apply fade effect (older points more transparent)
            if self.fade_enabled:
                progress = i / max(1, len(trail_points) - 1)
                alpha = int(100 + (155 * progress))  # Fade from 100 to 255
                color = (color[0], color[1], color[2], alpha)

            # Transform world coordinates to screen coordinates
            sx1, sy1 = self._world_to_screen(x1, y1, camera)
            sx2, sy2 = self._world_to_screen(x2, y2, camera)

            # Draw line segment
            dpg.draw_line(
                (sx1, sy1),
                (sx2, sy2),
                color=color,
                thickness=self.trail_thickness,
                parent=canvas_tag
            )

    def _delta_to_color(self, delta_seconds):
        """Convert time delta to color.

        Args:
            delta_seconds: Time delta in seconds (negative = faster)

        Returns:
            tuple: (R, G, B, A) color
        """
        # Normalize delta to color range
        # -0.5s or better = full green
        # +0.5s or worse = full red
        # 0.0s = gray

        if delta_seconds < -0.05:
            # Faster than previous lap - green
            intensity = min(1.0, abs(delta_seconds) / 0.5)
            green = int(100 + (155 * intensity))  # 100-255
            return (0, green, 0, 200)

        elif delta_seconds > 0.05:
            # Slower than previous lap - red
            intensity = min(1.0, delta_seconds / 0.5)
            red = int(100 + (155 * intensity))  # 100-255
            return (red, 0, 0, 200)

        else:
            # Very close to previous lap - gray
            return (150, 150, 150, 200)

    def _world_to_screen(self, world_x, world_y, camera):
        """Convert world coordinates to screen coordinates.

        Args:
            world_x: World X coordinate
            world_y: World Y coordinate
            camera: Camera parameters dict with zoom_level, pan_offset_x/y, viewport_width/height

        Returns:
            tuple: (screen_x, screen_y)
        """
        zoom = camera.get('zoom_level', 1.0)
        pan_x = camera.get('pan_offset_x', 0.0)
        pan_y = camera.get('pan_offset_y', 0.0)
        vp_width = camera.get('viewport_width', 800)
        vp_height = camera.get('viewport_height', 600)

        # Apply zoom and pan
        screen_x = (world_x * zoom) + pan_x + (vp_width / 2)
        screen_y = (world_y * zoom) + pan_y + (vp_height / 2)

        return screen_x, screen_y
