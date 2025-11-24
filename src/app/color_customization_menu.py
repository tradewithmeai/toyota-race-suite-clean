"""Color customization menu for the desktop app.

Provides the main UI for customizing all visualization colors.
Integrates the color preview display and color picker components.
"""

import dearpygui.dearpygui as dpg
from .color_config import color_config
from .color_preview import ColorPreviewDisplay
from .color_picker import color_picker


class ColorCustomizationMenu:
    """Main color customization settings panel."""

    def __init__(self):
        """Initialize the color customization menu."""
        self.window_tag = "color_customization_window"
        self.is_open = False
        self.preview_display = None
        self.on_colors_changed = None  # Callback when colors are updated
        self.world = None  # World model for highlighting cars

        # Category dropdown
        self.category_combo_tag = "cc_category_combo"

        # Size slider container tag
        self.slider_container_tag = "cc_slider_container"

        # Categories with display names
        self.categories = {
            'car_colors': 'Car Colours',
            'brake_gradient': 'Brake Visualisation',
            'deviation_bars': 'Deviation Bars',
            'race_timer': 'Race Timer',
            'track': 'Track Elements',
        }

    def open(self, world=None, on_colors_changed=None):
        """Open the color customization menu.

        Args:
            world: World model for accessing car IDs and highlighting
            on_colors_changed: Callback when colors are updated
        """
        if self.is_open:
            return

        self.world = world
        self.on_colors_changed = on_colors_changed
        self._create_window()
        self.is_open = True

    def _create_window(self):
        """Create the color customization window."""
        # Delete existing window if present
        if dpg.does_item_exist(self.window_tag):
            dpg.delete_item(self.window_tag)

        # Create main window
        with dpg.window(
            tag=self.window_tag,
            label="Visuals - Custom",
            width=500,
            height=600,
            pos=[100, 50],
            on_close=self._on_close
        ):
            # Header
            dpg.add_text(
                "Customise Visualisation Colours",
                color=(255, 200, 0)
            )
            dpg.add_text(
                "Click on a coloured element to change it",
                color=(150, 150, 150)
            )

            dpg.add_separator()

            # Category selector
            with dpg.group(horizontal=True):
                dpg.add_text("Category:")
                dpg.add_combo(
                    tag=self.category_combo_tag,
                    items=list(self.categories.values()),
                    default_value=self.categories['car_colors'],
                    width=250,
                    callback=self._on_category_change
                )

            dpg.add_spacer(height=10)

            # Preview container
            with dpg.child_window(
                tag="cc_preview_container",
                width=-1,
                height=420,
                border=True
            ):
                # Create preview display
                self.preview_display = ColorPreviewDisplay("cc_preview_container")
                self.preview_display.create()
                self.preview_display.set_callback(self._on_color_selected)
                # Pass car IDs, world colors, and selected cars if available
                if self.world is not None:
                    self.preview_display.car_ids = self.world.car_ids
                    self.preview_display.world_colors = self.world.colors
                    self.preview_display.selected_car_ids = self.world.selected_car_ids
                self.preview_display.render()

            dpg.add_spacer(height=10)

            # Slider container for size controls (shown for certain categories)
            with dpg.group(tag=self.slider_container_tag):
                pass  # Will be populated by _update_sliders

            dpg.add_spacer(height=5)

            # Action buttons
            with dpg.group(horizontal=True):
                dpg.add_button(
                    label="Reset Category",
                    width=120,
                    callback=self._on_reset_category
                )
                dpg.add_button(
                    label="Reset All",
                    width=120,
                    callback=self._on_reset_all
                )
                dpg.add_button(
                    label="Close",
                    width=100,
                    callback=self._on_close
                )

        # Show initial sliders for default category
        self._update_sliders('car_colors')

    def _on_category_change(self, sender, app_data):
        """Handle category dropdown change."""
        # Find the category key from display name
        selected_display_name = app_data
        category_key = None

        for key, name in self.categories.items():
            if name == selected_display_name:
                category_key = key
                break

        if category_key and self.preview_display:
            self.preview_display.set_category(category_key)
            self._update_sliders(category_key)

    def _on_color_selected(self, category: str, key: str, current_color):
        """Handle when a color element is clicked in the preview.

        Args:
            category: Color category
            key: Color key within category
            current_color: Current RGB(A) color
        """
        # If car color selected, highlight that car on the track
        if category == 'car_colors' and self.world is not None:
            try:
                car_index = int(key)
                if car_index < len(self.world.car_ids):
                    car_id = self.world.car_ids[car_index]
                    # Set as only selected car to show white circle
                    self.world.selected_car_ids = [car_id]
            except (ValueError, IndexError):
                pass

        # Open color picker
        color_picker.open(
            category=category,
            key=key,
            color=current_color[:3],  # Ensure RGB only
            on_apply=self._on_color_applied,
            on_cancel=None
        )

    def _on_color_applied(self, category: str, key: str, new_color):
        """Handle when a new color is applied from the picker.

        Args:
            category: Color category
            key: Color key
            new_color: New RGB color
        """
        # Update the color config
        color_config.set_color(category, key, new_color)

        # If car color changed, also update world.colors so track rendering uses new color
        if category == 'car_colors' and self.world is not None:
            try:
                car_index = int(key)
                if car_index < len(self.world.car_ids):
                    car_id = self.world.car_ids[car_index]
                    self.world.colors[car_id] = tuple(new_color)
                    print(f"Updated world.colors[{car_id}] = {new_color}")
            except (ValueError, IndexError) as e:
                print(f"Error updating world color: {e}")

        # Refresh preview
        if self.preview_display:
            self.preview_display.render()

        # Notify listeners
        if self.on_colors_changed:
            self.on_colors_changed()

        print(f"Updated {category}/{key} to {new_color}")

    def _on_reset_category(self, sender, app_data):
        """Reset current category to defaults."""
        if self.preview_display:
            category = self.preview_display.current_category
            color_config.reset_category(category)

            # Sync world.colors if car_colors category was reset
            if category == 'car_colors' and self.world is not None:
                self._sync_world_colors()

            self.preview_display.render()

            if self.on_colors_changed:
                self.on_colors_changed()

            print(f"Reset {category} to defaults")

    def _on_reset_all(self, sender, app_data):
        """Reset all colors to defaults."""
        color_config.reset_to_defaults()

        # Sync world.colors with reset car colors
        if self.world is not None:
            self._sync_world_colors()

        if self.preview_display:
            self.preview_display.render()

        if self.on_colors_changed:
            self.on_colors_changed()

        print("Reset all colors to defaults")

    def _sync_world_colors(self):
        """Sync world.colors dictionary with color_config car colors."""
        if self.world is None:
            return

        car_colors = color_config.get_car_colors_list()
        for i, car_id in enumerate(self.world.car_ids):
            if i < len(car_colors):
                self.world.colors[car_id] = car_colors[i]

    def _update_sliders(self, category: str):
        """Update slider container based on selected category."""
        # Clear existing sliders
        if dpg.does_item_exist(self.slider_container_tag):
            dpg.delete_item(self.slider_container_tag, children_only=True)

        # Define sliders for each category with category-specific labels
        slider_config = {
            'brake_gradient': [
                ('brake_arc_max_radius', 'Brake Arc Size', 40, 200),
            ],
            'deviation_bars': [
                ('deviation_bar_length', 'Deviation Bar Length', 10, 50),
            ],
            'acceleration_heatmap': [
                ('trail_duration_s', 'Custom Trail Duration (s)', 1, 15),
            ],
        }

        if category not in slider_config:
            return

        # Get display name for category
        category_name = self.categories.get(category, category)

        # Create sliders for this category
        with dpg.group(parent=self.slider_container_tag):
            dpg.add_separator()
            dpg.add_text(f"{category_name} - Size Settings", color=(255, 200, 0))

            for key, label, min_val, max_val in slider_config[category]:
                current_value = color_config.get_size(key)
                slider_tag = f"size_slider_{key}"
                # Delete existing slider if it exists
                if dpg.does_item_exist(slider_tag):
                    dpg.delete_item(slider_tag)
                dpg.add_slider_int(
                    label=label,
                    tag=slider_tag,
                    default_value=current_value,
                    min_value=min_val,
                    max_value=max_val,
                    width=200,
                    callback=self._on_size_changed,
                    user_data=key
                )

    def _on_size_changed(self, sender, value, user_data):
        """Handle size slider change."""
        key = user_data
        color_config.set_size(key, value)

        # Refresh preview to show size change
        if self.preview_display:
            self.preview_display.render()

        # Notify listeners for immediate update on animation
        if self.on_colors_changed:
            self.on_colors_changed()

        print(f"Size {key} set to {value}")

    def _on_close(self, sender=None, app_data=None):
        """Close the window."""
        if dpg.does_item_exist(self.window_tag):
            dpg.delete_item(self.window_tag)

        if self.preview_display:
            self.preview_display = None

        self.is_open = False

    def close(self):
        """Public method to close the menu."""
        self._on_close()


# Global instance
color_customization_menu = ColorCustomizationMenu()
