"""Color preview display widget for color customization.

Shows an expanded car dot visualization with all visual effects highlighted.
Users can click on different colored sections to customize them.
"""

import math
import dearpygui.dearpygui as dpg
from .color_config import color_config
from .color_picker import color_picker


class ColorPreviewDisplay:
    """Displays an expanded car with all visual effects for color customization."""

    def __init__(self, parent_window: str):
        """Initialize the preview display.

        Args:
            parent_window: DearPyGUI parent window tag
        """
        self.parent = parent_window
        self.drawlist_tag = "color_preview_drawlist"
        self.window_tag = "color_preview_window"

        # Preview state
        self.current_category = "car_colors"
        self.selected_element = None
        self.on_color_select_callback = None

        # Element bounding boxes for click detection
        self.clickable_regions = {}

        # Car IDs for display (set by menu)
        self.car_ids = []

        # World colors for displaying actual track colours (set by menu)
        self.world_colors = {}

        # Selected car IDs for highlighting (set by menu)
        self.selected_car_ids = []

        # Preview dimensions
        self.preview_width = 400
        self.preview_height = 400
        self.center_x = self.preview_width // 2
        self.center_y = self.preview_height // 2

    def create(self):
        """Create the preview display UI elements."""
        # Create a child window for the preview
        with dpg.child_window(
            tag=self.window_tag,
            parent=self.parent,
            width=self.preview_width,
            height=self.preview_height,
            border=True
        ):
            # Create drawlist for custom rendering
            dpg.add_drawlist(
                tag=self.drawlist_tag,
                width=self.preview_width,
                height=self.preview_height
            )

        # Register click handler with unique tag
        handler_tag = f"{self.window_tag}_handler"
        if not dpg.does_item_exist(handler_tag):
            with dpg.handler_registry(tag=handler_tag):
                dpg.add_mouse_click_handler(callback=self._handle_click)

    def set_category(self, category: str):
        """Set the visualization category to display.

        Args:
            category: One of the color categories from ColorConfig
        """
        self.current_category = category
        self.render()

    def set_callback(self, callback):
        """Set callback for when a color element is clicked.

        Args:
            callback: Function(category, key, current_color)
        """
        self.on_color_select_callback = callback

    def render(self):
        """Render the preview based on current category."""
        # Clear previous drawings
        dpg.delete_item(self.drawlist_tag, children_only=True)
        self.clickable_regions.clear()

        # Draw background
        dpg.draw_rectangle(
            [0, 0], [self.preview_width, self.preview_height],
            fill=(30, 30, 30), parent=self.drawlist_tag
        )

        # Render based on category
        if self.current_category == "car_colors":
            self._render_car_colors()
        elif self.current_category == "brake_gradient":
            self._render_brake_gradient()
        elif self.current_category == "deviation_bars":
            self._render_deviation_bars()
        elif self.current_category == "acceleration_heatmap":
            self._render_acceleration_heatmap()
        elif self.current_category == "race_timer":
            self._render_race_timer()
        elif self.current_category == "track":
            self._render_track()
        else:
            self._render_generic()

    def _render_car_colors(self):
        """Render car color preview - grid of car dots with IDs."""
        # Use world colors if available (actual track colours), otherwise fall back to config
        if self.car_ids and self.world_colors:
            # Build colors list from world_colors in same order as car_ids
            colors = []
            for car_id in self.car_ids:
                colors.append(self.world_colors.get(car_id, (255, 255, 255)))
        else:
            colors = color_config.get_car_colors_list()

        # Determine number of cars to display
        num_cars = len(self.car_ids) if self.car_ids else min(len(colors), 18)

        # Grid layout - dynamic based on number of cars
        if num_cars <= 6:
            cols, rows = 3, 2
        elif num_cars <= 12:
            cols, rows = 4, 3
        else:
            cols, rows = 6, 3

        cell_w = self.preview_width // cols
        cell_h = self.preview_height // rows
        radius = min(cell_w, cell_h) // 4

        for i in range(num_cars):
            if i >= len(colors):
                break

            color = colors[i]
            row = i // cols
            col = i % cols

            cx = col * cell_w + cell_w // 2
            cy = row * cell_h + cell_h // 2

            # Check if this car is selected on the track
            is_selected = False
            if self.car_ids and i < len(self.car_ids):
                car_id = self.car_ids[i]
                is_selected = car_id in self.selected_car_ids

            # Draw white ring around selected cars
            if is_selected:
                dpg.draw_circle(
                    [cx, cy], radius + 4, fill=(0, 0, 0, 0), color=(255, 255, 255),
                    thickness=3, parent=self.drawlist_tag
                )

            # Draw car dot
            dpg.draw_circle(
                [cx, cy], radius, fill=color, color=(255, 255, 255),
                thickness=2 if self.selected_element == f"car_{i}" else 1,
                parent=self.drawlist_tag
            )

            # Draw car ID (last 6 chars) or number if no IDs available
            if self.car_ids and i < len(self.car_ids):
                car_label = self.car_ids[i][-6:]  # Last 6 chars like "040-3"
            else:
                car_label = str(i + 1)

            # Center the text below the circle
            text_x = cx - len(car_label) * 3
            text_y = cy + radius + 3
            dpg.draw_text(
                [text_x, text_y], car_label,
                color=(200, 200, 200), size=9, parent=self.drawlist_tag
            )

            # Store clickable region
            self.clickable_regions[f"car_{i}"] = {
                'bounds': (cx - radius, cy - radius, cx + radius, cy + radius + 15),
                'category': 'car_colors',
                'key': str(i),
                'color': color
            }

    def _render_brake_gradient(self):
        """Render brake visualization preview with front and rear arcs."""
        colors = color_config.get_brake_gradient()

        # Get max arc radius from config and scale for preview
        max_radius = color_config.get_size('brake_arc_max_radius')
        # Scale to fit in preview (max_radius 200 -> 120 in preview)
        scale = min(120, max_radius * 0.6)

        # Draw central car dot
        car_radius = 25
        dpg.draw_circle(
            [self.center_x, self.center_y], car_radius,
            fill=(200, 200, 200), parent=self.drawlist_tag
        )

        # Draw front brake arcs (top half) at different intensities
        front_levels = [
            ('front_light', 0.15, int(scale * 0.5)),
            ('front_medium', 0.5, int(scale * 0.75)),
            ('front_heavy', 0.85, int(scale))
        ]

        for level, intensity, radius in front_levels:
            color = colors[level]

            # Draw arc (top arc for front brakes)
            start_angle = 30
            end_angle = 150
            self._draw_arc(
                self.center_x, self.center_y, radius,
                start_angle, end_angle, color, 6
            )

            # Clickable region
            label_name = level.replace('front_', '')
            self.clickable_regions[f"brake_{level}"] = {
                'bounds': (self.center_x - radius - 10, self.center_y - radius - 20,
                          self.center_x + radius + 10, self.center_y - 20),
                'category': 'brake_gradient',
                'key': level,
                'color': color
            }

        # Draw rear brake arcs (bottom half) at different intensities
        rear_levels = [
            ('rear_light', 0.15, int(scale * 0.5)),
            ('rear_medium', 0.5, int(scale * 0.75)),
            ('rear_heavy', 0.85, int(scale))
        ]

        for level, intensity, radius in rear_levels:
            color = colors[level]

            # Draw arc (bottom arc for rear brakes)
            start_angle = 210
            end_angle = 330
            self._draw_arc(
                self.center_x, self.center_y, radius,
                start_angle, end_angle, color, 6
            )

            # Clickable region
            self.clickable_regions[f"brake_{level}"] = {
                'bounds': (self.center_x - radius - 10, self.center_y + 20,
                          self.center_x + radius + 10, self.center_y + radius + 20),
                'category': 'brake_gradient',
                'key': level,
                'color': color
            }

        # Labels for front and rear
        dpg.draw_text(
            [self.center_x - 25, 20],
            "Front Brakes",
            color=(200, 200, 200), size=11, parent=self.drawlist_tag
        )
        dpg.draw_text(
            [self.center_x - 25, self.preview_height - 35],
            "Rear Brakes",
            color=(200, 200, 200), size=11, parent=self.drawlist_tag
        )

        # Intensity labels on the side
        dpg.draw_text(
            [10, self.center_y - 60], "Light",
            color=(150, 150, 150), size=9, parent=self.drawlist_tag
        )
        dpg.draw_text(
            [10, self.center_y - 10], "Medium",
            color=(150, 150, 150), size=9, parent=self.drawlist_tag
        )
        dpg.draw_text(
            [10, self.center_y + 40], "Heavy",
            color=(150, 150, 150), size=9, parent=self.drawlist_tag
        )

    def _render_deviation_bars(self):
        """Render deviation bars preview."""
        colors = color_config.get_deviation_colors()

        # Get bar length from config
        config_bar_length = color_config.get_size('deviation_bar_length')

        # Draw central car
        car_radius = 25
        dpg.draw_circle(
            [self.center_x, self.center_y], car_radius,
            fill=(200, 200, 200), parent=self.drawlist_tag
        )

        # Draw left deviation bars - scale to preview
        bar_length = int(config_bar_length * 1.5)  # Scale up for visibility
        bar_width = 6
        base_offset = 50
        spacing = max(10, bar_length // 2)

        for i in range(5):
            x = self.center_x - base_offset - i * spacing
            y1 = self.center_y - bar_length // 2
            y2 = self.center_y + bar_length // 2

            # Fill increases with distance
            fill = (i + 1) / 5
            color = colors['left']
            alpha_color = (*color, int(255 * fill))

            dpg.draw_rectangle(
                [x - bar_width // 2, y1], [x + bar_width // 2, y2],
                fill=alpha_color, parent=self.drawlist_tag
            )

        # Draw right deviation bars
        for i in range(5):
            x = self.center_x + base_offset + i * spacing
            y1 = self.center_y - bar_length // 2
            y2 = self.center_y + bar_length // 2

            fill = (i + 1) / 5
            color = colors['right']
            alpha_color = (*color, int(255 * fill))

            dpg.draw_rectangle(
                [x - bar_width // 2, y1], [x + bar_width // 2, y2],
                fill=alpha_color, parent=self.drawlist_tag
            )

        # Labels and clickable regions
        dpg.draw_text(
            [self.center_x - 150, self.center_y + 50],
            "Left (negative)",
            color=colors['left'], size=12, parent=self.drawlist_tag
        )
        self.clickable_regions['deviation_left'] = {
            'bounds': (self.center_x - 200, self.center_y - 50,
                      self.center_x - 40, self.center_y + 50),
            'category': 'deviation_bars',
            'key': 'left',
            'color': colors['left']
        }

        dpg.draw_text(
            [self.center_x + 70, self.center_y + 50],
            "Right (positive)",
            color=colors['right'], size=12, parent=self.drawlist_tag
        )
        self.clickable_regions['deviation_right'] = {
            'bounds': (self.center_x + 40, self.center_y - 50,
                      self.center_x + 200, self.center_y + 50),
            'category': 'deviation_bars',
            'key': 'right',
            'color': colors['right']
        }

    def _render_acceleration_heatmap(self):
        """Render acceleration trail preview."""
        colors = color_config.get_acceleration_colors()

        # Get size settings from config
        trail_duration = color_config.get_size('trail_duration_s')
        accel_size = color_config.get_size('accel_display_size')

        # Scale trail length based on duration (1-15s maps to 100-350px)
        trail_length = int(100 + (trail_duration - 1) * 17.8)
        # Scale trail height based on accel display size (5-40 maps to 20-60px)
        trail_height = int(20 + (accel_size - 5) * 1.14)

        start_x = (self.preview_width - trail_length) // 2
        start_y = self.center_y - trail_height // 2

        levels = [('low', 0), ('medium', 0.33), ('high', 0.66)]

        segment_width = trail_length // 3
        for i, (level, offset) in enumerate(levels):
            x = start_x + i * segment_width
            color = colors[level]

            dpg.draw_rectangle(
                [x, start_y], [x + segment_width, start_y + trail_height],
                fill=color, parent=self.drawlist_tag
            )

            # Label
            dpg.draw_text(
                [x + 10, start_y + trail_height + 10],
                level.capitalize(),
                color=color, size=12, parent=self.drawlist_tag
            )

            # Clickable region
            self.clickable_regions[f'accel_{level}'] = {
                'bounds': (x, start_y, x + segment_width, start_y + trail_height),
                'category': 'acceleration_heatmap',
                'key': level,
                'color': color
            }

        # Draw car at end of trail
        car_x = start_x + trail_length + 30
        dpg.draw_circle(
            [car_x, self.center_y], 20,
            fill=(200, 200, 200), parent=self.drawlist_tag
        )

    def _render_race_timer(self):
        """Render race timer preview."""
        colors = color_config.get_race_timer_colors()

        # Draw timer: 12:34:567
        y = self.center_y
        x_start = 80

        components = [
            ('minutes', '12', 40),
            ('separator', ':', 15),
            ('seconds', '34', 40),
            ('separator', '.', 15),
            ('milliseconds', '567', 50),
        ]

        x = x_start
        for key, text, width in components:
            if key == 'separator':
                color = colors['separator']
            else:
                color = colors[key]

            dpg.draw_text(
                [x, y - 20], text,
                color=color, size=32, parent=self.drawlist_tag
            )

            if key != 'separator':
                # Clickable region
                self.clickable_regions[f'timer_{key}'] = {
                    'bounds': (x, y - 25, x + width, y + 25),
                    'category': 'race_timer',
                    'key': key,
                    'color': color
                }

            x += width

    def _render_track(self):
        """Render track element preview with dynamic list from track displays."""
        colors = color_config.get_track_colors()

        # Track elements matching the Track Displays menu
        track_elements = [
            ('density_plot', 'Density Plot'),
            ('racing_line', 'Racing Line'),
            ('outline', 'Track Outline'),
            ('global_racing_line', 'Global Racing Line'),
        ]

        # Layout parameters
        start_y = 30
        row_height = 80
        box_size = 40
        box_x = 30
        label_x = 90

        for i, (key, display_name) in enumerate(track_elements):
            y = start_y + i * row_height

            # Get colour (use default if not in config)
            if key in colors:
                color = colors[key]
            else:
                color = (150, 150, 150, 255)

            # Extract RGB for display
            rgb = color[:3] if len(color) >= 3 else color

            # Draw colour box with border
            dpg.draw_rectangle(
                [box_x, y], [box_x + box_size, y + box_size],
                fill=rgb, color=(255, 255, 255), thickness=1,
                parent=self.drawlist_tag
            )

            # Draw label
            dpg.draw_text(
                [label_x, y + 12], display_name,
                color=(200, 200, 200), size=14, parent=self.drawlist_tag
            )

            # Draw "Click to change" hint
            dpg.draw_text(
                [label_x, y + 32], "Click to change",
                color=(100, 100, 100), size=10, parent=self.drawlist_tag
            )

            # Store clickable region (the colour box)
            self.clickable_regions[f'track_{key}'] = {
                'bounds': (box_x, y, box_x + box_size, y + box_size),
                'category': 'track',
                'key': key,
                'color': color
            }

    def _render_generic(self):
        """Render generic category preview."""
        category_colors = color_config.get_category_colors(self.current_category)

        y = 30
        for key, color in category_colors.items():
            rgb = color[:3] if len(color) > 3 else color

            # Color swatch
            dpg.draw_rectangle(
                [30, y], [60, y + 20],
                fill=rgb, parent=self.drawlist_tag
            )

            # Label
            dpg.draw_text(
                [70, y + 2], key,
                color=(200, 200, 200), size=11, parent=self.drawlist_tag
            )

            # Clickable region
            self.clickable_regions[f'{self.current_category}_{key}'] = {
                'bounds': (30, y, 200, y + 20),
                'category': self.current_category,
                'key': key,
                'color': color
            }

            y += 30

    def _draw_arc(self, cx, cy, radius, start_deg, end_deg, color, thickness):
        """Draw an arc using line segments."""
        segments = 20
        angle_range = end_deg - start_deg
        points = []

        for i in range(segments + 1):
            angle = math.radians(start_deg + (angle_range * i / segments))
            x = cx + radius * math.cos(angle)
            y = cy - radius * math.sin(angle)  # Negative because screen Y is inverted
            points.append([x, y])

        dpg.draw_polyline(
            points, color=color, thickness=thickness,
            parent=self.drawlist_tag
        )

    def _handle_click(self, sender, app_data):
        """Handle mouse clicks on the preview."""
        # Don't process clicks if color picker is already open
        if color_picker.is_open:
            return

        # Check if click is within our drawlist
        if not dpg.does_item_exist(self.drawlist_tag):
            return

        # Check if the parent window exists and is shown
        if not dpg.does_item_exist(self.window_tag):
            return

        # Check if the main customization menu is open
        if not dpg.does_item_exist("color_customization_window"):
            return

        # Get mouse position in screen coordinates
        mouse_pos = dpg.get_mouse_pos(local=False)

        # Get the drawlist's absolute position on screen
        # get_item_rect_min gives us the absolute screen position
        try:
            drawlist_pos = dpg.get_item_rect_min(self.drawlist_tag)
        except Exception:
            return

        # Calculate relative position within the drawlist
        rel_x = mouse_pos[0] - drawlist_pos[0]
        rel_y = mouse_pos[1] - drawlist_pos[1]

        # Check if within drawlist bounds
        if not (0 <= rel_x <= self.preview_width and 0 <= rel_y <= self.preview_height):
            return

        # Check clickable regions
        for region_id, region in self.clickable_regions.items():
            x1, y1, x2, y2 = region['bounds']
            if x1 <= rel_x <= x2 and y1 <= rel_y <= y2:
                self.selected_element = region_id
                print(f"Color preview clicked: {region['category']}/{region['key']}")

                if self.on_color_select_callback:
                    self.on_color_select_callback(
                        region['category'],
                        region['key'],
                        region['color']
                    )
                else:
                    print("Warning: No color select callback set!")

                # Re-render to show selection
                self.render()
                break

    def destroy(self):
        """Clean up UI elements."""
        if dpg.does_item_exist(self.window_tag):
            dpg.delete_item(self.window_tag)
