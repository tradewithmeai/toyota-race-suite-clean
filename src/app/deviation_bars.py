"""Deviation-from-racing-line visualization bars.

Renders 10 animated bars (5 left, 5 right) around each car to show
deviation from the optimal racing line. HUD-style rendering with
fixed pixel sizes regardless of zoom.
"""

import math
import dearpygui.dearpygui as dpg
from app.color_config import color_config


def get_deviation_colors():
    """Get deviation bar colors from config."""
    colors = color_config.get_deviation_colors()
    return colors['right'], colors['left'], colors['inactive']


class DeviationBarState:
    """Animation state for deviation bars of a single car."""

    def __init__(self):
        # Current fill levels for each bar (0 to 1)
        # Index 0-4 = left bars, 5-9 = right bars
        self.current_fills = [0.0] * 10
        self.target_fills = [0.0] * 10

    def update(self, dt_ms: float):
        """Smooth animation interpolation.

        Args:
            dt_ms: Time delta in milliseconds
        """
        # Exponential smoothing factor (150-250ms response)
        alpha = min(1.0, dt_ms / 150.0)

        for i in range(10):
            diff = self.target_fills[i] - self.current_fills[i]
            self.current_fills[i] += diff * alpha


def compute_bar_fills(deviation_score: float) -> list:
    """Compute target fill levels for all 10 bars.

    Args:
        deviation_score: Value in [-1, 1]
            negative = left of racing line
            positive = right of racing line

    Returns:
        List of 10 fill values (0 to 1)
        Index 0-4 = left bars (activate on negative)
        Index 5-9 = right bars (activate on positive)
    """
    fills = [0.0] * 10

    # Clamp score to valid range
    score = max(-1.0, min(1.0, deviation_score))

    if score < 0:
        # Left deviation - fill left bars
        abs_score = abs(score)
        for i in range(5):
            threshold = (i + 1) * 0.2  # 0.2, 0.4, 0.6, 0.8, 1.0
            if abs_score >= threshold:
                fills[i] = 1.0
            elif abs_score > threshold - 0.2:
                # Partial fill within this bar's band
                within_band = (abs_score - (threshold - 0.2)) / 0.2
                fills[i] = within_band
            else:
                fills[i] = 0.0
    else:
        # Right deviation - fill right bars
        for i in range(5):
            threshold = (i + 1) * 0.2  # 0.2, 0.4, 0.6, 0.8, 1.0
            if score >= threshold:
                fills[5 + i] = 1.0
            elif score > threshold - 0.2:
                # Partial fill within this bar's band
                within_band = (score - (threshold - 0.2)) / 0.2
                fills[5 + i] = within_band
            else:
                fills[5 + i] = 0.0

    return fills


def delete_deviation_bars(car_id: str):
    """Delete all deviation bar elements for a car.

    Args:
        car_id: Unique identifier for the car
    """
    for i in range(10):
        outline_tag = f"devbar_outline_{car_id}_{i}"
        fill_tag = f"devbar_fill_{car_id}_{i}"
        if dpg.does_item_exist(outline_tag):
            dpg.delete_item(outline_tag)
        if dpg.does_item_exist(fill_tag):
            dpg.delete_item(fill_tag)


def draw_deviation_bars(screen_x: float, screen_y: float, heading_rad: float,
                        bar_state: DeviationBarState, drawlist, car_id: str):
    """Draw deviation bars around a car in screen space.

    Args:
        screen_x, screen_y: Car position in screen coordinates (pixels)
        heading_rad: Car heading in radians
        bar_state: Animation state for this car
        drawlist: DearPyGUI drawlist parent
        car_id: Unique identifier for tagging draw elements
    """
    # Delete old bars first
    delete_deviation_bars(car_id)

    # Bar geometry from config
    bar_length = color_config.get_size('deviation_bar_length')
    BAR_WIDTH = 4            # Thickness of each bar
    BASE_OFFSET = 15         # Distance from car center to first bar
    BAR_SPACING = max(5, bar_length // 3)  # Space scales with bar length

    # Compute direction vectors
    # Forward direction from heading
    fx = math.cos(heading_rad)
    fy = math.sin(heading_rad)

    # Perpendicular direction (left is positive)
    px = -fy
    py = fx

    # Draw left bars (indices 0-4)
    for i in range(5):
        bar_idx = i
        fill = bar_state.current_fills[bar_idx]

        # Calculate bar center position (offset left from car)
        offset = BASE_OFFSET + i * BAR_SPACING
        center_x = screen_x + px * offset
        center_y = screen_y + py * offset

        # Bar endpoints (oriented along forward direction)
        half_len = bar_length / 2
        x1 = center_x - fx * half_len
        y1 = center_y - fy * half_len
        x2 = center_x + fx * half_len
        y2 = center_y + fy * half_len

        # Draw fill if active (from center outward)
        if fill > 0.01:
            fill_half = half_len * fill
            fx1 = center_x - fx * fill_half
            fy1 = center_y - fy * fill_half
            fx2 = center_x + fx * fill_half
            fy2 = center_y + fy * fill_half
            fill_tag = f"devbar_fill_{car_id}_{bar_idx}"
            neon_pink, neon_blue, _ = get_deviation_colors()
            dpg.draw_line([fx1, fy1], [fx2, fy2], color=neon_blue,
                         thickness=BAR_WIDTH - 1, parent=drawlist, tag=fill_tag)

    # Draw right bars (indices 5-9)
    for i in range(5):
        bar_idx = 5 + i
        fill = bar_state.current_fills[bar_idx]

        # Calculate bar center position (offset right from car)
        offset = BASE_OFFSET + i * BAR_SPACING
        center_x = screen_x - px * offset  # Negative perpendicular = right
        center_y = screen_y - py * offset

        # Bar endpoints
        half_len = bar_length / 2
        x1 = center_x - fx * half_len
        y1 = center_y - fy * half_len
        x2 = center_x + fx * half_len
        y2 = center_y + fy * half_len

        # Draw fill if active
        if fill > 0.01:
            fill_half = half_len * fill
            fx1 = center_x - fx * fill_half
            fy1 = center_y - fy * fill_half
            fx2 = center_x + fx * fill_half
            fy2 = center_y + fy * fill_half
            fill_tag = f"devbar_fill_{car_id}_{bar_idx}"
            neon_pink, neon_blue, _ = get_deviation_colors()
            dpg.draw_line([fx1, fy1], [fx2, fy2], color=neon_pink,
                         thickness=BAR_WIDTH - 1, parent=drawlist, tag=fill_tag)
