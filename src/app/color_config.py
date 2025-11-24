"""Color configuration manager for customizable visualization colors.

Provides centralized color storage with JSON persistence for all
visualization elements. Users can customize colors through the UI
and settings persist across sessions.
"""

import json
import os
from typing import Tuple


# Type aliases
RGB = Tuple[int, int, int]
RGBA = Tuple[int, int, int, int]


class ColorConfig:
    """Manages all customizable colors with persistence."""

    # Default config file location
    DEFAULT_CONFIG_PATH = os.path.join(
        os.path.expanduser("~"), ".race_replay_colors.json"
    )

    def __init__(self, config_path: str = None):
        """Initialize with default colors.

        Args:
            config_path: Path to JSON config file (uses default if None)
        """
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self._colors = self._get_defaults()
        self._load_config()

    def _get_defaults(self) -> dict:
        """Return default color configuration."""
        return {
            # Car colors (18 cars)
            'car_colors': {
                '0': (255, 68, 68),      # Red
                '1': (68, 255, 68),      # Green
                '2': (68, 68, 255),      # Blue
                '3': (255, 255, 68),     # Yellow
                '4': (255, 68, 255),     # Magenta
                '5': (68, 255, 255),     # Cyan
                '6': (255, 136, 68),     # Orange
                '7': (136, 255, 68),     # Lime
                '8': (255, 136, 255),    # Pink
                '9': (136, 68, 255),     # Purple
                '10': (255, 200, 68),    # Gold
                '11': (68, 200, 255),    # Sky Blue
                '12': (200, 68, 255),    # Violet
                '13': (255, 68, 136),    # Rose
                '14': (68, 255, 136),    # Mint
                '15': (136, 136, 255),   # Periwinkle
                '16': (255, 136, 136),   # Salmon
                '17': (136, 255, 255),   # Aqua
            },

            # Brake visualization gradient (front and rear)
            'brake_gradient': {
                'front_light': (68, 255, 68),      # Front 0-30% - Green
                'front_medium': (255, 170, 68),    # Front 30-70% - Orange
                'front_heavy': (255, 68, 68),      # Front 70-100% - Red
                'rear_light': (68, 200, 68),       # Rear 0-30% - Darker Green
                'rear_medium': (255, 140, 68),     # Rear 30-70% - Darker Orange
                'rear_heavy': (200, 68, 68),       # Rear 70-100% - Darker Red
            },

            # Deviation bars
            'deviation_bars': {
                'right': (255, 20, 147),     # Neon Pink - positive deviation
                'left': (0, 191, 255),       # Neon Blue - negative deviation
                'inactive': (60, 60, 60),    # Dim Gray
            },

            # Acceleration heatmap gradient
            'acceleration_heatmap': {
                'low': (50, 90, 255),        # Blue
                'medium': (60, 220, 60),     # Green
                'high': (255, 50, 50),       # Red
            },

            # Delta speed trail gradient (vs reference/ideal)
            'delta_speed': {
                'slower': (68, 119, 255),    # Blue - slower than baseline
                'baseline': (60, 220, 60),   # Green - at baseline speed
                'faster': (255, 50, 50),     # Red - faster than baseline
            },

            # Race timer colors
            'race_timer': {
                'minutes': (255, 68, 68),    # Red
                'seconds': (255, 165, 0),    # Orange
                'milliseconds': (68, 255, 68),  # Green
                'separator': (150, 150, 150),   # Gray
            },

            # Track visualization
            'track': {
                'density_plot': (255, 255, 255, 128),        # White with alpha
                'racing_line': (100, 100, 100, 128),         # Gray with alpha
                'outline': (255, 200, 0, 180),               # Gold with alpha
                'global_racing_line': (57, 255, 20, 255),    # Neon green
            },

            # Theme colors - Dark
            'theme_dark': {
                'bg': (20, 20, 20),
                'panel_bg': (40, 40, 40),
                'panel_bg_alpha': (40, 40, 40, 200),
                'header_bg': (60, 60, 60, 220),
                'text': (255, 255, 255),
                'text_secondary': (200, 200, 200),
                'text_muted': (150, 150, 150),
                'accent': (100, 255, 100),
                'timer_bg': (0, 0, 0, 180),
            },

            # Theme colors - Light
            'theme_light': {
                'bg': (200, 200, 200),
                'panel_bg': (245, 245, 245),
                'panel_bg_alpha': (245, 245, 245, 230),
                'header_bg': (230, 230, 230, 240),
                'text': (20, 20, 20),
                'text_secondary': (60, 60, 60),
                'text_muted': (100, 100, 100),
                'accent': (0, 180, 0),
                'timer_bg': (255, 255, 255, 200),
            },

            # Intro/Loading screen
            'intro': {
                'title': (255, 200, 0),         # Gold
                'subtitle': (150, 150, 150),    # Medium Gray
                'error': (255, 100, 100),       # Light Red
                'file_extension': (0, 255, 0),  # Green
            },

            # HUD elements
            'hud': {
                'drag_handle': (150, 150, 150),
                'collapse_button': (200, 200, 200),
                'toggle_enabled': (100, 255, 100),
                'toggle_disabled': (100, 100, 100),
                'hover_label_bg': (0, 0, 0, 180),
                'hover_label_text': (255, 255, 255),
            },

            # Sector timing colors (F1/professional motorsport standard)
            'sector_timing': {
                'sector_1': (255, 68, 68),        # Red - Sector 1
                'sector_2': (68, 136, 255),       # Blue - Sector 2
                'sector_3': (255, 255, 68),       # Yellow - Sector 3
                'overall_best': (180, 68, 255),   # Purple - Overall best
                'personal_best': (68, 255, 68),   # Green - Personal best
                'slower': (255, 200, 68),         # Orange/Yellow - Slower than best
                'current': (255, 255, 255),       # White - In progress
                'delta_positive': (255, 68, 68),  # Red - Behind
                'delta_negative': (68, 255, 68),  # Green - Ahead
            },

            # Speed comparison overlay colors
            'speed_comparison': {
                'faster': (68, 255, 68),          # Green - Faster than ideal
                'slower': (255, 68, 68),          # Red - Slower than ideal
                'neutral': (255, 255, 255),       # White - At ideal speed
            },

            # Size configuration (stored as single-value tuples for consistency)
            'sizes': {
                'car_dot_radius': 8,           # Car marker radius in pixels
                'brake_arc_thickness': 3,      # Brake arc line thickness
                'trail_width': 2,              # Acceleration trail width
                'racing_line_width': 2,        # Racing line thickness
                'deviation_bar_width': 4,      # Deviation bar width
                'hud_font_size': 12,           # HUD text font size
                # Visual effect sizes
                'brake_arc_max_radius': 120,   # Max brake arc radius in pixels
                'deviation_bar_length': 20,    # Deviation bar length in pixels
                'trail_duration_s': 5,         # Trail duration in seconds (1-15)
                'steering_arrow_size': 30,     # Steering arrow length in pixels
                'accel_display_size': 15,      # Accel circle max expansion in pixels
            },
        }

    def _load_config(self):
        """Load color configuration from JSON file."""
        if os.path.exists(self.config_path):
            try:
                with open(self.config_path, 'r') as f:
                    saved = json.load(f)

                # Merge saved colors with defaults (preserves new defaults)
                self._merge_colors(saved)
                print(f"Loaded color config from {self.config_path}")
            except Exception as e:
                print(f"Error loading color config: {e}")

    def _merge_colors(self, saved: dict):
        """Merge saved colors into current config."""
        for category, colors in saved.items():
            if category in self._colors:
                if isinstance(colors, dict):
                    for key, value in colors.items():
                        if key in self._colors[category]:
                            # Convert list to tuple
                            self._colors[category][key] = tuple(value) if isinstance(value, list) else value

    def save(self):
        """Save current color configuration to JSON file."""
        try:
            # Convert tuples to lists for JSON serialization
            serializable = {}
            for category, colors in self._colors.items():
                if isinstance(colors, dict):
                    serializable[category] = {
                        k: list(v) if isinstance(v, tuple) else v
                        for k, v in colors.items()
                    }
                else:
                    serializable[category] = colors

            with open(self.config_path, 'w') as f:
                json.dump(serializable, f, indent=2)

            print(f"Saved color config to {self.config_path}")
        except Exception as e:
            print(f"Error saving color config: {e}")

    def reset_to_defaults(self):
        """Reset all colors to default values."""
        self._colors = self._get_defaults()
        self.save()

    def reset_category(self, category: str):
        """Reset a specific category to defaults."""
        defaults = self._get_defaults()
        if category in defaults:
            self._colors[category] = defaults[category]
            self.save()

    # ----- Getters -----

    def get_car_color(self, index: int) -> RGB:
        """Get car color by index (0-17)."""
        return self._colors['car_colors'].get(str(index), (255, 255, 255))

    def get_car_colors_list(self) -> list:
        """Get all car colors as a list ordered by index."""
        return [self._colors['car_colors'].get(str(i), (255, 255, 255))
                for i in range(18)]

    def get_brake_color(self, intensity: float, brake_type: str = 'front') -> RGB:
        """Get brake color based on intensity (0-1) and type (front/rear).

        Args:
            intensity: Brake intensity 0-1
            brake_type: 'front' or 'rear'
        """
        prefix = brake_type if brake_type in ('front', 'rear') else 'front'
        if intensity < 0.3:
            return self._colors['brake_gradient'][f'{prefix}_light']
        elif intensity < 0.7:
            return self._colors['brake_gradient'][f'{prefix}_medium']
        else:
            return self._colors['brake_gradient'][f'{prefix}_heavy']

    def get_brake_gradient(self) -> dict:
        """Get all brake gradient colors."""
        return self._colors['brake_gradient'].copy()

    def get_deviation_colors(self) -> dict:
        """Get deviation bar colors."""
        return self._colors['deviation_bars'].copy()

    def get_acceleration_colors(self) -> dict:
        """Get acceleration heatmap colors."""
        return self._colors['acceleration_heatmap'].copy()

    def get_delta_speed_colors(self) -> dict:
        """Get delta speed trail colors."""
        return self._colors['delta_speed'].copy()

    def get_race_timer_colors(self) -> dict:
        """Get race timer colors."""
        return self._colors['race_timer'].copy()

    def get_track_colors(self) -> dict:
        """Get track visualization colors."""
        return self._colors['track'].copy()

    def get_theme(self, theme_name: str) -> dict:
        """Get theme colors (dark/light)."""
        key = f'theme_{theme_name}'
        return self._colors.get(key, self._colors['theme_dark']).copy()

    def get_intro_colors(self) -> dict:
        """Get intro/loading screen colors."""
        return self._colors['intro'].copy()

    def get_hud_colors(self) -> dict:
        """Get HUD element colors."""
        return self._colors['hud'].copy()

    def get_sector_timing_colors(self) -> dict:
        """Get sector timing colors."""
        return self._colors.get('sector_timing', {}).copy()

    def get_speed_comparison_colors(self) -> dict:
        """Get speed comparison overlay colors."""
        return self._colors.get('speed_comparison', {}).copy()

    def get_sector_color(self, sector: int) -> RGB:
        """Get color for a specific sector (1, 2, or 3)."""
        colors = self._colors.get('sector_timing', {})
        return colors.get(f'sector_{sector}', (255, 255, 255))

    def get_sizes(self) -> dict:
        """Get all size configuration."""
        return self._colors.get('sizes', {}).copy()

    def get_size(self, key: str) -> int:
        """Get a specific size value."""
        sizes = self._colors.get('sizes', {})
        defaults = {
            'car_dot_radius': 8,
            'brake_arc_thickness': 3,
            'trail_width': 2,
            'racing_line_width': 2,
            'deviation_bar_width': 4,
            'hud_font_size': 12,
        }
        return sizes.get(key, defaults.get(key, 8))

    # ----- Setters -----

    def set_car_color(self, index: int, color: RGB):
        """Set car color by index."""
        self._colors['car_colors'][str(index)] = tuple(color)
        self.save()

    def set_brake_color(self, level: str, color: RGB):
        """Set brake gradient color (light/medium/heavy)."""
        if level in self._colors['brake_gradient']:
            self._colors['brake_gradient'][level] = tuple(color)
            self.save()

    def set_deviation_color(self, key: str, color: RGB):
        """Set deviation bar color (right/left/inactive)."""
        if key in self._colors['deviation_bars']:
            self._colors['deviation_bars'][key] = tuple(color)
            self.save()

    def set_acceleration_color(self, level: str, color: RGB):
        """Set acceleration heatmap color (low/medium/high)."""
        if level in self._colors['acceleration_heatmap']:
            self._colors['acceleration_heatmap'][level] = tuple(color)
            self.save()

    def set_race_timer_color(self, component: str, color: RGB):
        """Set race timer color (minutes/seconds/milliseconds/separator)."""
        if component in self._colors['race_timer']:
            self._colors['race_timer'][component] = tuple(color)
            self.save()

    def set_track_color(self, element: str, color):
        """Set track color (racing_line/outline) - accepts RGB or RGBA."""
        if element in self._colors['track']:
            self._colors['track'][element] = tuple(color)
            self.save()

    def set_theme_color(self, theme_name: str, key: str, color):
        """Set a specific theme color."""
        theme_key = f'theme_{theme_name}'
        if theme_key in self._colors and key in self._colors[theme_key]:
            self._colors[theme_key][key] = tuple(color)
            self.save()

    def set_intro_color(self, key: str, color: RGB):
        """Set intro/loading screen color."""
        if key in self._colors['intro']:
            self._colors['intro'][key] = tuple(color)
            self.save()

    def set_hud_color(self, key: str, color):
        """Set HUD element color."""
        if key in self._colors['hud']:
            self._colors['hud'][key] = tuple(color)
            self.save()

    def set_size(self, key: str, value: int):
        """Set a size configuration value."""
        if 'sizes' not in self._colors:
            self._colors['sizes'] = {}
        self._colors['sizes'][key] = value
        self.save()

    # ----- Utility -----

    def get_all_categories(self) -> list:
        """Get list of all color categories."""
        return list(self._colors.keys())

    def get_category_colors(self, category: str) -> dict:
        """Get all colors in a category."""
        return self._colors.get(category, {}).copy()

    def set_color(self, category: str, key: str, color):
        """Generic setter for any color."""
        if category in self._colors and key in self._colors[category]:
            self._colors[category][key] = tuple(color)
            self.save()
            return True
        return False


# Global color config instance
color_config = ColorConfig()
