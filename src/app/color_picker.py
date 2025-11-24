"""Color picker UI component for selecting custom colors.

Provides a popup modal with:
- Color palette grid (preset colors)
- RGB sliders for precise control
- Hex input field
- Color preview (before/after)
"""

import dearpygui.dearpygui as dpg
from typing import Callable, Tuple


# Preset color palette
COLOR_PALETTE = [
    # Row 1: Reds
    (255, 0, 0), (255, 68, 68), (255, 100, 100), (255, 136, 136),
    (200, 0, 0), (150, 0, 0), (100, 0, 0), (255, 68, 136),

    # Row 2: Oranges/Yellows
    (255, 165, 0), (255, 200, 0), (255, 255, 0), (255, 255, 68),
    (255, 136, 68), (200, 150, 0), (255, 200, 68), (255, 170, 68),

    # Row 3: Greens
    (0, 255, 0), (68, 255, 68), (100, 255, 100), (136, 255, 68),
    (0, 200, 0), (0, 150, 0), (0, 100, 0), (68, 255, 136),

    # Row 4: Cyans/Blues
    (0, 255, 255), (68, 255, 255), (0, 191, 255), (68, 200, 255),
    (0, 150, 200), (68, 68, 255), (0, 0, 255), (50, 90, 255),

    # Row 5: Purples/Magentas
    (255, 0, 255), (255, 68, 255), (200, 68, 255), (136, 68, 255),
    (136, 136, 255), (150, 0, 150), (100, 0, 100), (255, 20, 147),

    # Row 6: Grays
    (255, 255, 255), (200, 200, 200), (150, 150, 150), (100, 100, 100),
    (60, 60, 60), (40, 40, 40), (20, 20, 20), (0, 0, 0),
]


class ColorPicker:
    """Color picker popup for selecting custom colors."""

    def __init__(self):
        """Initialize the color picker."""
        self.window_tag = "color_picker_window"
        self.is_open = False

        # Current state
        self.original_color = (255, 255, 255)
        self.current_color = (255, 255, 255)
        self.category = ""
        self.key = ""

        # Callbacks
        self.on_apply: Callable = None
        self.on_cancel: Callable = None

        # UI element tags
        self.preview_original_tag = "cp_preview_original"
        self.preview_current_tag = "cp_preview_current"
        self.slider_r_tag = "cp_slider_r"
        self.slider_g_tag = "cp_slider_g"
        self.slider_b_tag = "cp_slider_b"
        self.hex_input_tag = "cp_hex_input"

    def open(self, category: str, key: str, color: Tuple[int, int, int],
             on_apply: Callable = None, on_cancel: Callable = None):
        """Open the color picker with the specified color.

        Args:
            category: Color category being edited
            key: Specific color key being edited
            color: Current RGB color (tuple of 3 ints)
            on_apply: Callback when Apply is clicked - receives (category, key, new_color)
            on_cancel: Callback when Cancel is clicked
        """
        self.category = category
        self.key = key
        self.original_color = tuple(color[:3])  # Ensure RGB only
        self.current_color = tuple(color[:3])
        self.on_apply = on_apply
        self.on_cancel = on_cancel

        self._create_window()
        self.is_open = True

    def _create_window(self):
        """Create the color picker window."""
        # Delete existing window if present
        if dpg.does_item_exist(self.window_tag):
            dpg.delete_item(self.window_tag)

        # Create modal window
        with dpg.window(
            tag=self.window_tag,
            label=f"Colour Picker - {self.category}/{self.key}",
            modal=True,
            no_close=True,
            width=450,
            height=350,
            pos=[200, 100]
        ):
            # Color previews
            with dpg.group(horizontal=True):
                with dpg.child_window(width=200, height=80):
                    dpg.add_text("Original")
                    with dpg.drawlist(width=180, height=50, tag="cp_original_drawlist"):
                        dpg.draw_rectangle(
                            [0, 0], [180, 50],
                            fill=self.original_color,
                            tag=self.preview_original_tag
                        )

                with dpg.child_window(width=200, height=80):
                    dpg.add_text("New")
                    with dpg.drawlist(width=180, height=50, tag="cp_current_drawlist"):
                        dpg.draw_rectangle(
                            [0, 0], [180, 50],
                            fill=self.current_color,
                            tag=self.preview_current_tag
                        )

            dpg.add_separator()

            # RGB Sliders
            dpg.add_text("RGB Values")

            with dpg.group(horizontal=True):
                dpg.add_text("R:", color=(255, 100, 100))
                dpg.add_slider_int(
                    tag=self.slider_r_tag,
                    default_value=self.current_color[0],
                    min_value=0, max_value=255,
                    width=300,
                    callback=self._on_slider_change
                )

            with dpg.group(horizontal=True):
                dpg.add_text("G:", color=(100, 255, 100))
                dpg.add_slider_int(
                    tag=self.slider_g_tag,
                    default_value=self.current_color[1],
                    min_value=0, max_value=255,
                    width=300,
                    callback=self._on_slider_change
                )

            with dpg.group(horizontal=True):
                dpg.add_text("B:", color=(100, 100, 255))
                dpg.add_slider_int(
                    tag=self.slider_b_tag,
                    default_value=self.current_color[2],
                    min_value=0, max_value=255,
                    width=300,
                    callback=self._on_slider_change
                )

            dpg.add_separator()

            # Hex input
            with dpg.group(horizontal=True):
                dpg.add_text("Hex:")
                dpg.add_input_text(
                    tag=self.hex_input_tag,
                    default_value=self._color_to_hex(self.current_color),
                    width=100,
                    callback=self._on_hex_change,
                    on_enter=True
                )

            dpg.add_spacer(height=20)

            # Buttons
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Apply",
                    width=100,
                    callback=self._on_apply
                )
                dpg.add_button(
                    label="Cancel",
                    width=100,
                    callback=self._on_cancel
                )
                dpg.add_button(
                    label="Reset",
                    width=100,
                    callback=self._on_reset
                )

    def _set_color(self, color: Tuple[int, int, int]):
        """Set the current color and update UI."""
        self.current_color = tuple(color)
        self._update_ui()

    def _on_slider_change(self, sender, app_data):
        """Handle RGB slider changes."""
        r = dpg.get_value(self.slider_r_tag)
        g = dpg.get_value(self.slider_g_tag)
        b = dpg.get_value(self.slider_b_tag)
        self.current_color = (r, g, b)
        self._update_preview()
        self._update_hex()

    def _on_hex_change(self, sender, app_data):
        """Handle hex input changes."""
        hex_str = app_data.strip()
        color = self._hex_to_color(hex_str)
        if color:
            self.current_color = color
            self._update_preview()
            self._update_sliders()

    def _update_ui(self):
        """Update all UI elements to reflect current color."""
        self._update_preview()
        self._update_sliders()
        self._update_hex()

    def _update_preview(self):
        """Update the preview rectangle."""
        if dpg.does_item_exist(self.preview_current_tag):
            dpg.configure_item(
                self.preview_current_tag,
                fill=self.current_color
            )

    def _update_sliders(self):
        """Update RGB sliders."""
        if dpg.does_item_exist(self.slider_r_tag):
            dpg.set_value(self.slider_r_tag, self.current_color[0])
            dpg.set_value(self.slider_g_tag, self.current_color[1])
            dpg.set_value(self.slider_b_tag, self.current_color[2])

    def _update_hex(self):
        """Update hex input field."""
        if dpg.does_item_exist(self.hex_input_tag):
            dpg.set_value(
                self.hex_input_tag,
                self._color_to_hex(self.current_color)
            )

    def _color_to_hex(self, color: Tuple[int, int, int]) -> str:
        """Convert RGB tuple to hex string."""
        return f"#{color[0]:02x}{color[1]:02x}{color[2]:02x}"

    def _hex_to_color(self, hex_str: str) -> Tuple[int, int, int]:
        """Convert hex string to RGB tuple."""
        hex_str = hex_str.lstrip('#')
        if len(hex_str) == 6:
            try:
                return (
                    int(hex_str[0:2], 16),
                    int(hex_str[2:4], 16),
                    int(hex_str[4:6], 16)
                )
            except ValueError:
                pass
        elif len(hex_str) == 3:
            try:
                return (
                    int(hex_str[0] * 2, 16),
                    int(hex_str[1] * 2, 16),
                    int(hex_str[2] * 2, 16)
                )
            except ValueError:
                pass
        return None

    def _on_apply(self, sender, app_data):
        """Handle Apply button click."""
        if self.on_apply:
            self.on_apply(self.category, self.key, self.current_color)
        self.close()

    def _on_cancel(self, sender, app_data):
        """Handle Cancel button click."""
        if self.on_cancel:
            self.on_cancel()
        self.close()

    def _on_reset(self, sender, app_data):
        """Reset to original color."""
        self.current_color = self.original_color
        self._update_ui()

    def close(self):
        """Close the color picker window."""
        if dpg.does_item_exist(self.window_tag):
            dpg.delete_item(self.window_tag)
        self.is_open = False


# Global color picker instance
color_picker = ColorPicker()
