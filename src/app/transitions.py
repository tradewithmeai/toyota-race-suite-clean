"""Smooth transitions and fading effects for UI elements."""

import time
import dearpygui.dearpygui as dpg


class TransitionManager:
    """Manages smooth transitions between UI states."""

    def __init__(self):
        self.active_transitions = []
        self.fade_overlay_tag = "fade_overlay"
        self.overlay_created = False

    def create_fade_overlay(self):
        """Create a full-screen overlay for fade effects."""
        if self.overlay_created:
            return

        # Create overlay window that covers everything
        with dpg.window(label="Fade Overlay", tag=self.fade_overlay_tag,
                       width=-1, height=-1, no_close=True,
                       no_title_bar=True, no_move=True, no_scrollbar=True,
                       no_background=False, modal=False, popup=False,
                       show=False):
            # Dark rectangle for fade effect
            with dpg.drawlist(tag="fade_drawlist", width=2000, height=2000):
                dpg.draw_rectangle((0, 0), (2000, 2000),
                                  color=(0, 0, 0, 0),
                                  fill=(0, 0, 0, 0),
                                  tag="fade_rect")

        self.overlay_created = True

    def fade_out(self, duration_ms=300, on_complete=None):
        """
        Fade to black.

        Args:
            duration_ms: Duration of fade in milliseconds
            on_complete: Callback when fade completes
        """
        self.active_transitions.append({
            'type': 'fade_out',
            'start_time': time.time(),
            'duration_ms': duration_ms,
            'on_complete': on_complete
        })

        # Show overlay
        if dpg.does_item_exist(self.fade_overlay_tag):
            dpg.show_item(self.fade_overlay_tag)
            dpg.set_item_pos(self.fade_overlay_tag, [0, 0])

    def fade_in(self, duration_ms=300, on_complete=None):
        """
        Fade from black to clear.

        Args:
            duration_ms: Duration of fade in milliseconds
            on_complete: Callback when fade completes
        """
        self.active_transitions.append({
            'type': 'fade_in',
            'start_time': time.time(),
            'duration_ms': duration_ms,
            'on_complete': on_complete
        })

        # Show overlay at full opacity
        if dpg.does_item_exist(self.fade_overlay_tag):
            dpg.show_item(self.fade_overlay_tag)
            dpg.configure_item("fade_rect", fill=(0, 0, 0, 255))

    def crossfade(self, duration_ms=500, on_midpoint=None, on_complete=None):
        """
        Crossfade effect (fade out, then fade in).

        Args:
            duration_ms: Total duration
            on_midpoint: Callback at midpoint (when fully black)
            on_complete: Callback when complete
        """
        half_duration = duration_ms // 2

        def on_fade_out_done():
            if on_midpoint:
                on_midpoint()
            self.fade_in(half_duration, on_complete)

        self.fade_out(half_duration, on_fade_out_done)

    def update(self):
        """Update all active transitions. Call from main loop."""
        completed = []

        for i, transition in enumerate(self.active_transitions):
            elapsed_ms = (time.time() - transition['start_time']) * 1000
            progress = min(1.0, elapsed_ms / transition['duration_ms'])

            if transition['type'] == 'fade_out':
                # Increase opacity from 0 to 255
                alpha = int(255 * progress)
                if dpg.does_item_exist("fade_rect"):
                    dpg.configure_item("fade_rect", fill=(0, 0, 0, alpha))

            elif transition['type'] == 'fade_in':
                # Decrease opacity from 255 to 0
                alpha = int(255 * (1 - progress))
                if dpg.does_item_exist("fade_rect"):
                    dpg.configure_item("fade_rect", fill=(0, 0, 0, alpha))

            # Check if complete
            if progress >= 1.0:
                completed.append(i)
                if transition['on_complete']:
                    transition['on_complete']()

                # Hide overlay when fade_in completes
                if transition['type'] == 'fade_in':
                    if dpg.does_item_exist(self.fade_overlay_tag):
                        dpg.hide_item(self.fade_overlay_tag)

        # Remove completed transitions
        for i in reversed(completed):
            self.active_transitions.pop(i)

    def is_transitioning(self):
        """Check if any transitions are active."""
        return len(self.active_transitions) > 0


class FadingElement:
    """Wrapper for UI elements with fade-in/out capabilities."""

    def __init__(self, tag, initial_alpha=255):
        self.tag = tag
        self.target_alpha = initial_alpha
        self.current_alpha = initial_alpha
        self.fade_speed = 5  # Alpha change per frame

    def fade_to(self, target_alpha, speed=5):
        """Set target alpha for smooth transition."""
        self.target_alpha = max(0, min(255, target_alpha))
        self.fade_speed = speed

    def show(self, speed=10):
        """Fade in the element."""
        self.fade_to(255, speed)

    def hide(self, speed=10):
        """Fade out the element."""
        self.fade_to(0, speed)

    def update(self):
        """Update alpha transition."""
        if self.current_alpha != self.target_alpha:
            if self.current_alpha < self.target_alpha:
                self.current_alpha = min(self.target_alpha, self.current_alpha + self.fade_speed)
            else:
                self.current_alpha = max(self.target_alpha, self.current_alpha - self.fade_speed)

            # Apply alpha to element color
            # Note: This works for text elements with color property
            if dpg.does_item_exist(self.tag):
                try:
                    # Get current color and update alpha
                    config = dpg.get_item_configuration(self.tag)
                    if 'color' in config:
                        color = list(config['color'])
                        if len(color) >= 3:
                            if len(color) == 3:
                                color.append(self.current_alpha)
                            else:
                                color[3] = self.current_alpha
                            dpg.configure_item(self.tag, color=tuple(color))
                except:
                    pass

        return self.current_alpha == self.target_alpha


class AnimatedProgress:
    """Animated progress bar with smooth value transitions."""

    def __init__(self, tag):
        self.tag = tag
        self.current_value = 0.0
        self.target_value = 0.0
        self.speed = 0.05  # Progress per frame

    def set_progress(self, value, instant=False):
        """Set target progress value."""
        self.target_value = max(0.0, min(1.0, value))
        if instant:
            self.current_value = self.target_value

    def update(self):
        """Update progress animation."""
        if abs(self.current_value - self.target_value) > 0.001:
            diff = self.target_value - self.current_value
            self.current_value += diff * self.speed

            if dpg.does_item_exist(self.tag):
                dpg.set_value(self.tag, self.current_value)

        return abs(self.current_value - self.target_value) < 0.001
