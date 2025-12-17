"""Demo cursor system for training mode - animated cursor with click feedback."""

import math
import dearpygui.dearpygui as dpg


class DemoCursor:
    """Animated cursor for guiding users through demo."""

    def __init__(self):
        self.visible = True
        self.x = 0.0
        self.y = 0.0

        # Movement animation
        self.target_x = 0.0
        self.target_y = 0.0
        self.start_x = 0.0
        self.start_y = 0.0
        self.move_progress = 1.0  # 0 to 1
        self.move_duration = 1.0  # seconds
        self.move_start_time = 0.0

        # Click animation
        self.click_active = False
        self.click_progress = 0.0
        self.click_duration = 0.3  # seconds
        self.click_start_time = 0.0

        # Drawing tags
        self.cursor_tag = "demo_cursor"
        self.ripple_tag = "demo_cursor_ripple"

    def move_to(self, target_pos, duration=1.0):
        """Animate cursor to target position.

        Args:
            target_pos: (x, y) screen coordinates
            duration: Animation duration in seconds
        """
        self.start_x = self.x
        self.start_y = self.y
        self.target_x = target_pos[0]
        self.target_y = target_pos[1]
        self.move_progress = 0.0
        self.move_duration = duration

    def trigger_click(self):
        """Start click animation."""
        self.click_active = True
        self.click_progress = 0.0

    def show(self):
        """Make cursor visible."""
        self.visible = True

    def hide(self):
        """Hide cursor and clean up."""
        self.visible = False
        self._cleanup()

    def update(self, delta_time):
        """Update cursor animation state.

        Args:
            delta_time: Time since last frame in seconds
        """
        # Update movement
        if self.move_progress < 1.0:
            self.move_progress += delta_time / self.move_duration
            self.move_progress = min(1.0, self.move_progress)

            # Cubic ease-in-out
            t = self._ease_in_out_cubic(self.move_progress)
            self.x = self.start_x + (self.target_x - self.start_x) * t
            self.y = self.start_y + (self.target_y - self.start_y) * t

        # Update click animation
        if self.click_active:
            self.click_progress += delta_time / self.click_duration
            if self.click_progress >= 1.0:
                self.click_active = False
                self.click_progress = 0.0

    def render(self, canvas):
        """Draw cursor on canvas.

        Args:
            canvas: DearPyGUI canvas tag
        """
        if not self.visible:
            return

        # Calculate scale for click animation
        scale = 1.0
        if self.click_active:
            # Scale up and down (bounce effect)
            if self.click_progress < 0.5:
                scale = 1.0 + (self.click_progress * 2) * 0.3
            else:
                scale = 1.3 - ((self.click_progress - 0.5) * 2) * 0.3

        # Draw cursor arrow
        self._draw_cursor_arrow(canvas, self.x, self.y, scale)

        # Draw ripple during click
        if self.click_active:
            self._draw_click_ripple(canvas, self.x, self.y, self.click_progress)

    def _ease_in_out_cubic(self, t):
        """Cubic easing function for smooth movement.

        Args:
            t: Progress value (0 to 1)

        Returns:
            Eased value (0 to 1)
        """
        if t < 0.5:
            return 4 * t * t * t
        else:
            return 1 - pow(-2 * t + 2, 3) / 2

    def _draw_cursor_arrow(self, canvas, x, y, scale):
        """Draw cursor arrow shape.

        Args:
            canvas: DearPyGUI canvas tag
            x, y: Cursor position
            scale: Scale factor for click animation
        """
        # Arrow points defined relative to origin (standard cursor shape)
        points = [
            (0, 0),      # Tip
            (0, 20),     # Bottom of shaft
            (6, 15),     # Inner corner
            (10, 24),    # Outer finger point
            (13, 22),    # Outer finger base
            (9, 13),     # Inner finger
            (15, 13)     # Right wing
        ]

        # Scale and translate
        scaled_points = [(x + px * scale, y + py * scale) for px, py in points]

        # Delete old cursor
        if dpg.does_item_exist(self.cursor_tag):
            dpg.delete_item(self.cursor_tag)

        # Draw white cursor with black outline
        dpg.draw_polygon(
            scaled_points,
            color=(0, 0, 0, 255),
            fill=(255, 255, 255, 255),
            thickness=2,
            parent=canvas,
            tag=self.cursor_tag
        )

    def _draw_click_ripple(self, canvas, x, y, progress):
        """Draw expanding ripple for click feedback.

        Args:
            canvas: DearPyGUI canvas tag
            x, y: Click position
            progress: Animation progress (0 to 1)
        """
        # Ripple expands and fades
        radius = 5 + progress * 20
        alpha = int(255 * (1 - progress))

        # Delete old ripple
        if dpg.does_item_exist(self.ripple_tag):
            dpg.delete_item(self.ripple_tag)

        # Draw ripple circle
        dpg.draw_circle(
            center=(x, y),
            radius=radius,
            color=(255, 255, 255, alpha),
            thickness=2,
            parent=canvas,
            tag=self.ripple_tag
        )

    def _cleanup(self):
        """Clean up all cursor rendering elements."""
        for tag in [self.cursor_tag, self.ripple_tag]:
            if dpg.does_item_exist(tag):
                dpg.delete_item(tag)
