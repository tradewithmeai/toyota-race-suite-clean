"""GPU renderer using DearPyGUI canvas with static track + dynamic car layers."""

import math
import dearpygui.dearpygui as dpg
import numpy as np

from app.density_map import build_density_map, density_map_to_texture
from app.deviation_bars import DeviationBarState, compute_bar_fills, draw_deviation_bars, delete_deviation_bars
from app.color_config import color_config


class GPURenderer:
    """Handles all canvas rendering with GPU acceleration."""

    def __init__(self, canvas_tag: str, world_model):
        self.canvas = canvas_tag
        self.world = world_model
        self.viewport_width = 1600
        self.viewport_height = 1000

        # Track drawing state (PATCH 8)
        self.track_drawn = False
        self.car_items = {}  # car_id -> item tag
        self.trail_items = {}  # car_id -> trail item tag
        self.glow_items = {}  # car_id -> brake glow item tag
        self.background_drawn = False  # Background drawn flag

        # Zoom and pan state
        self.zoom_level = 1.0  # 1.0 = fit to view
        self.pan_offset_x = 0.0  # World coordinate offset
        self.pan_offset_y = 0.0

        # Track cumulative drag delta to compute per-frame delta
        self.last_drag_delta_x = 0.0
        self.last_drag_delta_y = 0.0

        # Density map state
        self.density_texture = None
        self.density_bounds = None
        self.density_initialized = False

        # Deviation bar animation state per car
        self.deviation_bar_states = {}  # car_id -> DeviationBarState
        self.last_frame_time_ms = 0

        # HUD toggle regions for click detection
        self.hud_toggle_regions = {}  # 'toggle_name' -> (x, y, width, height)

        # HUD panel interaction state
        self.hud_collapse_regions = {}  # car_id -> (x, y, width, height) for collapse button
        self.hud_drag_regions = {}  # car_id -> (x, y, width, height) for drag handle

        # Reference to playback controls (set by main.py)
        self.controls = None
        self.dragging_hud = None  # car_id being dragged
        self.drag_start_y = 0  # Y position where drag started

        # Box selection state
        self.box_select_start = None  # (x, y) start position for box selection
        self.box_select_active = False

    def world_to_screen(self, x: float, y: float) -> tuple:
        """Transform meters -> pixels with padding, aspect ratio, zoom and pan."""
        bounds = self.world.bounds

        # Add 15% padding
        padding_factor = 0.15
        x_range = bounds['x_max'] - bounds['x_min']
        y_range = bounds['y_max'] - bounds['y_min']

        x_min = bounds['x_min'] - padding_factor * x_range
        x_max = bounds['x_max'] + padding_factor * x_range
        y_min = bounds['y_min'] - padding_factor * y_range
        y_max = bounds['y_max'] + padding_factor * y_range

        # Apply pan offset in world coordinates
        x_adjusted = x - self.pan_offset_x
        y_adjusted = y - self.pan_offset_y

        # Normalize to [0, 1]
        sx = (x_adjusted - x_min) / (x_max - x_min) if x_max != x_min else 0.5
        sy = (y_adjusted - y_min) / (y_max - y_min) if y_max != y_min else 0.5

        # Flip Y axis
        sy = 1.0 - sy

        # Apply zoom (scale from center)
        cx, cy = 0.5, 0.5
        sx = cx + (sx - cx) * self.zoom_level
        sy = cy + (sy - cy) * self.zoom_level

        # Preserve aspect ratio
        data_aspect = (x_max - x_min) / (y_max - y_min) if y_max != y_min else 1.0
        canvas_aspect = self.viewport_width / self.viewport_height

        if data_aspect > canvas_aspect:
            # Fit to width
            scale = self.viewport_width
            height = scale / data_aspect
            offset_y = (self.viewport_height - height) / 2
            px = sx * scale
            py = sy * height + offset_y
        else:
            # Fit to height
            scale = self.viewport_height
            width = scale * data_aspect
            offset_x = (self.viewport_width - width) / 2
            px = sx * width + offset_x
            py = sy * scale

        return px, py

    def draw_static_track(self):
        """Draw track using density map with optional racing line overlay."""
        if self.track_drawn:
            return

        # Initialize density map if not done
        if not self.density_initialized:
            self._initialize_density_map()
            self.density_initialized = True

        # Draw density map first (background layer) - respect show flag
        if self.world.show_density_plot and self.density_texture and self.density_bounds:
            self._draw_density_map()
        else:
            # Delete density map if hidden
            if dpg.does_item_exist("density_map_image"):
                dpg.delete_item("density_map_image")

        # Draw racing line on top - respect show flag
        if self.world.show_racing_line:
            self._draw_racing_line()
        else:
            # Delete racing line if hidden
            if dpg.does_item_exist("track_line"):
                dpg.delete_item("track_line")

        # Draw track outline if enabled
        if self.world.show_track_outline:
            self._draw_track_outline()
        else:
            # Delete track outline if hidden
            if dpg.does_item_exist("track_outline"):
                dpg.delete_item("track_outline")

        # Draw global racing line if enabled (neon green)
        if self.world.show_global_racing_line:
            self._draw_global_racing_line()
        else:
            # Delete global racing line if hidden
            if dpg.does_item_exist("global_racing_line"):
                dpg.delete_item("global_racing_line")

        # Draw sector lines if enabled
        if self.world.show_sector_lines:
            self._draw_sector_lines()
        else:
            # Delete sector lines if hidden
            for i in range(10):  # Max 10 sectors
                tag = f"sector_line_{i}"
                label_tag = f"sector_label_{i}"
                if dpg.does_item_exist(tag):
                    dpg.delete_item(tag)
                if dpg.does_item_exist(label_tag):
                    dpg.delete_item(label_tag)

        self.track_drawn = True

    def _initialize_density_map(self):
        """Build and create texture for density map."""
        try:
            density_image, bounds = build_density_map(self.world, bins=400, sigma=3.0)
            if density_image is not None:
                self.density_texture = density_map_to_texture(density_image)
                self.density_bounds = bounds
                print(f"Density map initialized: {density_image.shape}")
            else:
                print("Warning: Could not create density map")
        except Exception as e:
            print(f"Error creating density map: {e}")
            self.density_texture = None

    def _draw_density_map(self):
        """Draw the density map image on canvas."""
        bounds = self.density_bounds

        # Delete old density map if exists
        if dpg.does_item_exist("density_map_image"):
            dpg.delete_item("density_map_image")

        # Get screen coordinates for image corners
        # Note: Image origin is top-left, so we need to handle Y flip
        p_min = self.world_to_screen(bounds['x_min'], bounds['y_max'])  # top-left
        p_max = self.world_to_screen(bounds['x_max'], bounds['y_min'])  # bottom-right

        # Draw the density map image
        dpg.draw_image(
            self.density_texture,
            pmin=p_min,
            pmax=p_max,
            parent=self.canvas,
            tag="density_map_image"
        )

    def _draw_racing_line(self):
        """Draw racing line polyline (overlay on density map)."""
        racing_line = self.world.racing_line

        if racing_line is None or len(racing_line) == 0:
            return

        # Defensive filter: remove any outlier points far outside track bounds
        bounds = self.world.bounds
        margin = 50.0  # meters
        x_min = bounds['x_min'] - margin
        x_max = bounds['x_max'] + margin
        y_min = bounds['y_min'] - margin
        y_max = bounds['y_max'] + margin

        # Filter points within bounds
        valid_mask = (
            (racing_line[:, 0] >= x_min) & (racing_line[:, 0] <= x_max) &
            (racing_line[:, 1] >= y_min) & (racing_line[:, 1] <= y_max)
        )
        filtered_line = racing_line[valid_mask]

        if len(filtered_line) < 10:
            return

        # Convert racing line to screen coordinates
        points = []
        for i in range(len(filtered_line)):
            px, py = self.world_to_screen(filtered_line[i, 0], filtered_line[i, 1])
            points.append([px, py])

        # Close the loop
        if len(points) > 0:
            points.append(points[0])

        # Draw polyline on canvas (thin line, lower opacity)
        track_colors = color_config.get_track_colors()
        dpg.draw_polyline(points, color=track_colors['racing_line'], thickness=1,
                         closed=True, parent=self.canvas, tag="track_line")

    def _draw_track_outline(self):
        """Draw smooth track boundary outline."""
        # Delete old track outline if exists
        if dpg.does_item_exist("track_outline"):
            dpg.delete_item("track_outline")

        boundary = self.world.track_boundary

        if boundary is None or len(boundary) == 0:
            return

        # Convert to screen coordinates
        points = []
        for i in range(len(boundary)):
            px, py = self.world_to_screen(boundary[i, 0], boundary[i, 1])
            points.append([px, py])

        # Close the loop
        if len(points) > 0:
            points.append(points[0])

        # Draw polyline (thicker, bright color for visibility)
        track_colors = color_config.get_track_colors()
        dpg.draw_polyline(points, color=track_colors['outline'], thickness=3,
                         closed=True, parent=self.canvas, tag="track_outline")

    def _draw_global_racing_line(self):
        """Draw global racing line in neon green for high visibility."""
        racing_line = self.world.racing_line

        if racing_line is None or len(racing_line) == 0:
            return

        # Delete old global racing line if exists
        if dpg.does_item_exist("global_racing_line"):
            dpg.delete_item("global_racing_line")

        # Defensive filter: remove any outlier points far outside track bounds
        bounds = self.world.bounds
        margin = 50.0  # meters
        x_min = bounds['x_min'] - margin
        x_max = bounds['x_max'] + margin
        y_min = bounds['y_min'] - margin
        y_max = bounds['y_max'] + margin

        # Filter points within bounds
        valid_mask = (
            (racing_line[:, 0] >= x_min) & (racing_line[:, 0] <= x_max) &
            (racing_line[:, 1] >= y_min) & (racing_line[:, 1] <= y_max)
        )
        filtered_line = racing_line[valid_mask]

        if len(filtered_line) < 10:
            return

        # Convert racing line to screen coordinates
        points = []
        for i in range(len(filtered_line)):
            px, py = self.world_to_screen(filtered_line[i, 0], filtered_line[i, 1])
            points.append([px, py])

        # Close the loop
        if len(points) > 0:
            points.append(points[0])

        # Draw polyline using configured color
        track_colors = color_config.get_track_colors()
        dpg.draw_polyline(points, color=track_colors['global_racing_line'], thickness=2,
                         closed=True, parent=self.canvas, tag="global_racing_line")

    def _draw_sector_lines(self):
        """Draw sector boundary lines on track."""
        if not self.world.sector_boundaries:
            return

        # Delete old sector lines
        for i in range(10):
            tag = f"sector_line_{i}"
            label_tag = f"sector_label_{i}"
            if dpg.does_item_exist(tag):
                dpg.delete_item(tag)
            if dpg.does_item_exist(label_tag):
                dpg.delete_item(label_tag)

        # Get sector colors
        sector_colors = color_config.get_sector_timing_colors()

        # Draw each sector boundary
        for i in range(len(self.world.sector_boundaries)):
            # Get line points from world model
            line_points = self.world.get_sector_line_points(i)
            if not line_points or len(line_points) < 2:
                continue

            # Convert to screen coordinates
            p1 = self.world_to_screen(line_points[0][0], line_points[0][1])
            p2 = self.world_to_screen(line_points[1][0], line_points[1][1])

            # Get color for this sector (S1=red, S2=blue, S3=yellow)
            sector_num = i + 1
            color_key = f'sector_{sector_num}'
            color = sector_colors.get(color_key, (255, 255, 255))
            color_rgba = (color[0], color[1], color[2], 255)

            # Draw the line
            tag = f"sector_line_{i}"
            dpg.draw_line(p1, p2, color=color_rgba, thickness=3,
                         parent=self.canvas, tag=tag)

            # Draw sector label at midpoint
            mid_x = (p1[0] + p2[0]) / 2
            mid_y = (p1[1] + p2[1]) / 2

            label_tag = f"sector_label_{i}"
            dpg.draw_text([mid_x - 8, mid_y - 8], f"S{sector_num}",
                         color=color_rgba, size=14,
                         parent=self.canvas, tag=label_tag)

    def get_brake_color(self, intensity: float, brake_type: str = 'front') -> tuple:
        """Get brake glow color based on intensity and type (front/rear)."""
        return color_config.get_brake_color(intensity, brake_type)

    def _draw_brake_arc(self, px, py, heading_rad, intensity, base_radius, is_front, car_id):
        """Draw brake as oriented semi-circle ring that expands with intensity."""
        # Validate inputs
        if intensity is None or intensity <= 0.05:
            return
        if not (math.isfinite(px) and math.isfinite(py) and math.isfinite(heading_rad)):
            return
        if base_radius <= 0:
            return

        # Calculate expanding radius based on intensity
        # Ring expands from base_radius based on configured max size
        max_expansion = color_config.get_size('brake_arc_max_radius') / 8  # Scale from config
        ring_radius = base_radius + (max_expansion * intensity)

        # Account for screen Y-flip
        visual_heading = -heading_rad

        # Forward direction vector
        fx = math.cos(visual_heading)
        fy = math.sin(visual_heading)

        # Offset distance to separate front and rear arcs
        # This creates the split at 3 and 9 o'clock positions
        arc_offset = ring_radius * 0.5  # Half radius offset

        # Arc angles, center offset, and label positioning
        if is_front:
            # Front semi-circle: centered forward from car, opens toward front
            # Arc from -90° to +90° relative to heading
            start_angle = visual_heading - math.pi/2
            end_angle = visual_heading + math.pi/2
            tag = f"brake_front_{car_id}"
            # Offset arc center forward
            arc_center_x = px + fx * arc_offset
            arc_center_y = py + fy * arc_offset
            # Position label in front
            label_x = px + fx * (ring_radius + arc_offset + 10)
            label_y = py + fy * (ring_radius + arc_offset + 10)
            label_prefix = "F"
        else:
            # Rear semi-circle: centered backward from car, opens toward back
            # Arc from +90° to +270° relative to heading
            start_angle = visual_heading + math.pi/2
            end_angle = visual_heading + math.pi * 3/2
            tag = f"brake_rear_{car_id}"
            # Offset arc center backward
            arc_center_x = px - fx * arc_offset
            arc_center_y = py - fy * arc_offset
            # Position label behind
            label_x = px - fx * (ring_radius + arc_offset + 10)
            label_y = py - fy * (ring_radius + arc_offset + 10)
            label_prefix = "R"

        # Generate arc points (20 segments for smooth curve)
        points = []
        for i in range(21):
            t = i / 20
            angle = start_angle + t * (end_angle - start_angle)
            x = arc_center_x + ring_radius * math.cos(angle)
            y = arc_center_y + ring_radius * math.sin(angle)
            points.append([x, y])

        # Get color based on intensity and brake type
        brake_type = 'front' if is_front else 'rear'
        color = self.get_brake_color(intensity, brake_type)
        color_rgba = (color[0], color[1], color[2], 255)

        # Clean up old tags before drawing
        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)

        # Draw arc ring with thickness proportional to intensity
        thickness = 2 + int(3 * intensity)  # 2-5 pixels thick
        dpg.draw_polyline(points, color=color_rgba, thickness=thickness,
                         closed=False, parent=self.canvas, tag=tag)

        # Draw percentage label positioned along heading direction
        label_tag = f"{tag}_label"
        if dpg.does_item_exist(label_tag):
            dpg.delete_item(label_tag)

        brake_pct = int(intensity * 100)
        dpg.draw_text([label_x - 12, label_y - 6], f"{label_prefix}:{brake_pct}%",
                      color=color_rgba, size=12, parent=self.canvas, tag=label_tag)

    def _draw_brake_fill(self, px, py, heading_rad, intensity, radius, is_front, car_id):
        """Draw pie-slice fill that expands from center based on brake intensity."""
        # Validate inputs
        if intensity is None or intensity <= 0.05:
            return
        if not (math.isfinite(px) and math.isfinite(py) and math.isfinite(heading_rad)):
            return
        if radius <= 0:
            return

        # Account for screen Y-flip
        visual_heading = -heading_rad

        # Fill radius expands with intensity - starts small, grows to 1.8x highlight radius
        fill_radius = radius * (0.3 + 1.5 * intensity)

        # Gap angle at 3 and 9 o'clock positions (15 degrees)
        gap_angle = math.pi / 12

        # Arc angles for semi-circle with gap
        if is_front:
            # Front semi-circle: from -90° + gap to +90° - gap
            start_angle = visual_heading - math.pi/2 + gap_angle
            end_angle = visual_heading + math.pi/2 - gap_angle
            tag = f"brake_fill_front_{car_id}"
            brake_type = 'front'
        else:
            # Rear semi-circle: from +90° + gap to +270° - gap
            start_angle = visual_heading + math.pi/2 + gap_angle
            end_angle = visual_heading + math.pi * 3/2 - gap_angle
            tag = f"brake_fill_rear_{car_id}"
            brake_type = 'rear'

        # Generate filled semi-circle points (pie slice from center)
        points = [[px, py]]  # Start at center
        for i in range(21):
            t = i / 20
            angle = start_angle + t * (end_angle - start_angle)
            x = px + fill_radius * math.cos(angle)
            y = py + fill_radius * math.sin(angle)
            points.append([x, y])

        # Get color based on intensity and brake type
        color = self.get_brake_color(intensity, brake_type)
        alpha = int(150 + 100 * intensity)
        fill_color = (color[0], color[1], color[2], alpha)

        # Clean up old tag before drawing
        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)

        # Draw filled polygon (pie slice)
        dpg.draw_polygon(points, color=fill_color, fill=fill_color,
                        parent=self.canvas, tag=tag)

    def get_deviation_color(self, deviation: float) -> tuple:
        """Get highlight color based on deviation from racing line."""
        # Clamp to ±2m
        dev_clamped = max(-2.0, min(2.0, deviation))
        alpha = abs(dev_clamped) / 2.0  # 0 → 1

        # Base colors
        white = (255, 255, 255)
        red = (255, 68, 68)    # right of racing line (positive)
        blue = (68, 119, 255)  # left of racing line (negative)

        # Lerp based on sign
        if deviation > 0:  # right
            target = red
        elif deviation < 0:  # left
            target = blue
        else:
            return (255, 255, 255, 80)  # pure white with opacity

        # Linear interpolation
        r = int(white[0] + (target[0] - white[0]) * alpha)
        g = int(white[1] + (target[1] - white[1]) * alpha)
        b = int(white[2] + (target[2] - white[2]) * alpha)

        return (r, g, b, 80)  # maintain opacity

    def draw_cars(self, car_states: dict):
        """Draw cars with highlighting and braking overlay."""
        selected = self.world.selected_car_ids
        highlight = self.world.highlight_selected
        show_brake = self.world.show_braking_overlay
        is_any_selected = len(selected) > 0

        for car_id, state in car_states.items():
            # Skip hidden cars - delete all their visual elements
            if car_id in self.world.hidden_car_ids:
                for tag in [f"car_{car_id}", f"overlay_{car_id}", f"outline_{car_id}",
                           f"brake_label_{car_id}", f"arrow_shaft_{car_id}", f"arrow_head_{car_id}"]:
                    if dpg.does_item_exist(tag):
                        dpg.delete_item(tag)
                delete_deviation_bars(car_id)
                continue

            # Deviation data available (for future visualization)
            deviation = state.get('deviation', 0.0)
            ideal_x = state.get('ideal_x', 0.0)
            ideal_y = state.get('ideal_y', 0.0)
            px, py = self.world_to_screen(state['x'], state['y'])
            base_color = self.world.colors.get(car_id, (255, 255, 255))
            is_selected = car_id in selected

            # All cars have same base size - selected cars get overlay circle + outline
            if is_any_selected and not is_selected:
                # Non-selected cars: dimmed
                radius = 7
                alpha = 80
            else:
                # Selected cars OR no selection: normal
                radius = 7
                alpha = 255

            # Apply alpha to base car color
            color = (base_color[0], base_color[1], base_color[2], alpha)

            # Delete old overlay if exists
            overlay_tag = f"overlay_{car_id}"
            if dpg.does_item_exist(overlay_tag):
                dpg.delete_item(overlay_tag)

            # Delete old brake label if exists
            label_tag = f"brake_label_{car_id}"
            if dpg.does_item_exist(label_tag):
                dpg.delete_item(label_tag)

            # Delete old car item if exists
            item_tag = f"car_{car_id}"
            if dpg.does_item_exist(item_tag):
                dpg.delete_item(item_tag)

            # Draw base car circle (small, colored)
            dpg.draw_circle(center=(px, py), radius=radius,
                           color=color, fill=color,
                           parent=self.canvas,
                           tag=item_tag)

            # For SELECTED cars only: Draw overlay, outline, and deviation bars (if enabled)
            if is_selected:
                overlay_radius = 14

                # Check if Circle Glow is enabled (outer expanding brake arcs)
                show_glow = self.world.show_circle_glow or self.world.show_circle_glow_all
                # Check if Circle Centre is enabled (inner brake fills)
                show_centre = self.world.show_circle_centre or self.world.show_circle_centre_all

                brake_front = state.get('brake_front', 0) or 0
                brake_rear = state.get('brake_rear', 0) or 0
                heading = state.get('heading', 0) or 0
                # Ensure values are valid numbers
                if not isinstance(brake_front, (int, float)):
                    brake_front = 0
                if not isinstance(brake_rear, (int, float)):
                    brake_rear = 0
                if not isinstance(heading, (int, float)):
                    heading = 0
                is_braking_glow = show_glow and (brake_front > 0.05 or brake_rear > 0.05)
                is_braking_centre = show_centre and (brake_front > 0.05 or brake_rear > 0.05)

                # Check if Lateral Diff is enabled (deviation bars + colored overlay)
                show_lateral_diff = self.world.show_lateral_diff or self.world.show_lateral_diff_all

                # Only show deviation overlay if NOT showing brake centre (brake centre takes priority)
                if show_lateral_diff and not is_braking_centre:
                    # Draw overlay circle with deviation-based color
                    overlay_color = self.get_deviation_color(deviation)
                    dpg.draw_circle(center=(px, py), radius=overlay_radius,
                                   color=overlay_color, fill=overlay_color,
                                   parent=self.canvas,
                                   tag=overlay_tag)
                else:
                    # No lateral diff or brake centre active - delete overlay if exists
                    if dpg.does_item_exist(overlay_tag):
                        dpg.delete_item(overlay_tag)

                # Draw inner filled semi-circles (Circle Centre effect)
                if is_braking_centre:
                    self._draw_brake_fill(px, py, heading, brake_front, overlay_radius,
                                         is_front=True, car_id=car_id)
                    self._draw_brake_fill(px, py, heading, brake_rear, overlay_radius,
                                         is_front=False, car_id=car_id)
                else:
                    # Clean up brake fills when not active
                    for fill_tag in [f"brake_fill_front_{car_id}", f"brake_fill_rear_{car_id}"]:
                        if dpg.does_item_exist(fill_tag):
                            dpg.delete_item(fill_tag)

                # Draw outer expanding brake arcs (Circle Glow effect)
                if is_braking_glow:
                    self._draw_brake_arc(px, py, heading, brake_front, overlay_radius,
                                        is_front=True, car_id=car_id)
                    self._draw_brake_arc(px, py, heading, brake_rear, overlay_radius,
                                        is_front=False, car_id=car_id)
                else:
                    # Remove brake arcs and labels if not active
                    for brake_tag in [f"brake_front_{car_id}", f"brake_rear_{car_id}",
                                     f"brake_front_{car_id}_label", f"brake_rear_{car_id}_label"]:
                        if dpg.does_item_exist(brake_tag):
                            dpg.delete_item(brake_tag)
                    if dpg.does_item_exist(label_tag):
                        dpg.delete_item(label_tag)

                # Draw white outline for selection highlight
                # Always show outline for selected cars (even with brake effects)
                outline_tag = f"outline_{car_id}"
                if dpg.does_item_exist(outline_tag):
                    dpg.delete_item(outline_tag)
                dpg.draw_circle(center=(px, py), radius=overlay_radius + 2,
                               color=(255, 255, 255, 255), thickness=3,
                               parent=self.canvas,
                               tag=outline_tag)

                # Draw deviation bars if lateral diff enabled
                if show_lateral_diff:
                    heading_rad = state.get('heading', 0)

                    # Get or create animation state for this car
                    if car_id not in self.deviation_bar_states:
                        self.deviation_bar_states[car_id] = DeviationBarState()
                    bar_state = self.deviation_bar_states[car_id]

                    # Normalize deviation to [-1, 1] range
                    deviation_score = max(-1.0, min(1.0, deviation / 2.0))

                    # Update target fills based on deviation
                    bar_state.target_fills = compute_bar_fills(deviation_score)

                    # Update animation (use 16ms as approximate frame time)
                    bar_state.update(16.0)

                    # Draw the bars in screen space
                    draw_deviation_bars(px, py, -heading_rad, bar_state, self.canvas, car_id)
                else:
                    # Remove deviation bars if disabled
                    delete_deviation_bars(car_id)

                # Draw steering arrow if enabled
                show_steering = self.world.show_steering_angle or self.world.show_steering_angle_all
                if show_steering:
                    steering_deg = state.get('steering', 0)
                    heading_rad = state.get('heading', 0)

                    # Convert steering to radians and combine with heading
                    steering_rad = math.radians(steering_deg)
                    visual_angle = heading_rad + steering_rad

                    # Account for Y-flip in screen coordinates
                    visual_angle = -visual_angle

                    # Arrow parameters
                    arrow_length = 18
                    arrow_width = 6

                    # Calculate arrow tip position
                    tip_x = px + arrow_length * math.cos(visual_angle)
                    tip_y = py + arrow_length * math.sin(visual_angle)

                    # Calculate arrowhead points
                    arrow_angle_left = visual_angle + 2.8
                    arrow_angle_right = visual_angle - 2.8

                    left_x = tip_x + arrow_width * math.cos(arrow_angle_left)
                    left_y = tip_y + arrow_width * math.sin(arrow_angle_left)
                    right_x = tip_x + arrow_width * math.cos(arrow_angle_right)
                    right_y = tip_y + arrow_width * math.sin(arrow_angle_right)

                    # Draw arrow shaft
                    arrow_shaft_tag = f"arrow_shaft_{car_id}"
                    if dpg.does_item_exist(arrow_shaft_tag):
                        dpg.delete_item(arrow_shaft_tag)

                    dpg.draw_line((px, py), (tip_x, tip_y),
                                  color=(255, 255, 255, 255), thickness=2,
                                  parent=self.canvas, tag=arrow_shaft_tag)

                    # Draw arrowhead triangle
                    arrow_head_tag = f"arrow_head_{car_id}"
                    if dpg.does_item_exist(arrow_head_tag):
                        dpg.delete_item(arrow_head_tag)

                    dpg.draw_triangle((tip_x, tip_y), (left_x, left_y), (right_x, right_y),
                                      color=(255, 255, 255, 255), fill=(255, 255, 255, 255),
                                      parent=self.canvas, tag=arrow_head_tag)
                else:
                    # Remove arrow if disabled
                    arrow_shaft_tag = f"arrow_shaft_{car_id}"
                    arrow_head_tag = f"arrow_head_{car_id}"
                    if dpg.does_item_exist(arrow_shaft_tag):
                        dpg.delete_item(arrow_shaft_tag)
                    if dpg.does_item_exist(arrow_head_tag):
                        dpg.delete_item(arrow_head_tag)
            else:
                # Remove outline if not selected
                outline_tag = f"outline_{car_id}"
                if dpg.does_item_exist(outline_tag):
                    dpg.delete_item(outline_tag)

                # Remove arrow if not selected
                arrow_shaft_tag = f"arrow_shaft_{car_id}"
                arrow_head_tag = f"arrow_head_{car_id}"
                if dpg.does_item_exist(arrow_shaft_tag):
                    dpg.delete_item(arrow_shaft_tag)
                if dpg.does_item_exist(arrow_head_tag):
                    dpg.delete_item(arrow_head_tag)

                # Remove deviation bars if not selected
                delete_deviation_bars(car_id)

    def get_accel_color(self, accel_norm: float, alpha: int = 200) -> tuple:
        """Get color based on normalized acceleration (0-1).

        Color mapping interpolates between low, medium, high colors.
        """
        accel_colors = color_config.get_acceleration_colors()
        low = accel_colors['low']
        mid = accel_colors['medium']
        high = accel_colors['high']

        if accel_norm <= 0.5:
            # Low to Medium
            t = accel_norm * 2
            r = int(low[0] + (mid[0] - low[0]) * t)
            g = int(low[1] + (mid[1] - low[1]) * t)
            b = int(low[2] + (mid[2] - low[2]) * t)
        else:
            # Medium to High
            t = (accel_norm - 0.5) * 2
            r = int(mid[0] + (high[0] - mid[0]) * t)
            g = int(mid[1] + (high[1] - mid[1]) * t)
            b = int(mid[2] + (high[2] - mid[2]) * t)

        return (r, g, b, alpha)

    def get_delta_speed_color(self, delta_kmh: float, alpha: int = 200) -> tuple:
        """Get color based on delta speed in km/h.

        Color mapping interpolates between slower (blue), baseline (green), faster (red).
        Range: -30 to +30 km/h
        """
        delta_colors = color_config.get_delta_speed_colors()
        slower = delta_colors['slower']
        baseline = delta_colors['baseline']
        faster = delta_colors['faster']

        # Clamp delta to range [-30, 30]
        delta_clamped = max(-30, min(30, delta_kmh))

        # Normalize to 0-1 range (0 = -30, 0.5 = 0, 1 = +30)
        normalized = (delta_clamped + 30) / 60

        if normalized <= 0.5:
            # Slower to Baseline (blue to green)
            t = normalized * 2
            r = int(slower[0] + (baseline[0] - slower[0]) * t)
            g = int(slower[1] + (baseline[1] - slower[1]) * t)
            b = int(slower[2] + (baseline[2] - slower[2]) * t)
        else:
            # Baseline to Faster (green to red)
            t = (normalized - 0.5) * 2
            r = int(baseline[0] + (faster[0] - baseline[0]) * t)
            g = int(baseline[1] + (faster[1] - baseline[1]) * t)
            b = int(baseline[2] + (faster[2] - baseline[2]) * t)

        return (r, g, b, alpha)

    def draw_trails(self):
        """Draw trails based on trail mode."""
        trail_mode = self.world.trail_mode

        # Always clear all existing trails first to avoid relics
        for car_id in self.world.car_ids:
            trail_tag = f"trail_{car_id}"
            if dpg.does_item_exist(trail_tag):
                dpg.delete_item(trail_tag)
            # Also clear heatmap segments
            for seg_idx in range(1000):
                seg_tag = f"accel_seg_{car_id}_{seg_idx}"
                if dpg.does_item_exist(seg_tag):
                    dpg.delete_item(seg_tag)
                else:
                    break
            # Also clear delta speed segments
            for seg_idx in range(1000):
                seg_tag = f"delta_seg_{car_id}_{seg_idx}"
                if dpg.does_item_exist(seg_tag):
                    dpg.delete_item(seg_tag)
                else:
                    break

        if trail_mode == 'off':
            return

        selected = self.world.selected_car_ids
        highlight = self.world.highlight_selected
        is_any_selected = len(selected) > 0

        for i, car_id in enumerate(self.world.car_ids):
            # Skip hidden cars
            if car_id in self.world.hidden_car_ids:
                continue

            # Handle acceleration heatmap mode separately
            if trail_mode == 'accel_heatmap':
                # Only draw for selected cars
                is_selected = car_id in selected
                if highlight and is_any_selected and not is_selected:
                    continue

                # Get trajectory data directly for accel_norm access
                traj = self.world.trajectories.get(car_id)
                if traj is None:
                    continue

                # Calculate trail window based on configured duration
                trail_duration = color_config.get_size('trail_duration_s')
                trail_frames = trail_duration * 100  # 100Hz sampling rate
                current_idx = int(self.world.current_time_ms / 10)
                start_idx = max(0, current_idx - trail_frames)

                if current_idx >= len(traj):
                    current_idx = len(traj) - 1

                if current_idx - start_idx < 2:
                    continue

                # Draw individual segments with acceleration-based colors
                for seg_idx in range(start_idx, current_idx):
                    # Get positions
                    x1, y1 = float(traj[seg_idx, 0]), float(traj[seg_idx, 1])
                    x2, y2 = float(traj[seg_idx + 1, 0]), float(traj[seg_idx + 1, 1])

                    # Get acceleration (use average of segment)
                    # Support both 10-column (old) and 11-column (new) formats
                    accel_col = 9 if traj.shape[1] >= 11 else 8
                    accel1 = float(traj[seg_idx, accel_col]) if traj.shape[1] > accel_col else 0.0
                    accel2 = float(traj[seg_idx + 1, accel_col]) if traj.shape[1] > accel_col else 0.0
                    avg_accel = (accel1 + accel2) / 2

                    # Compute fade alpha based on age
                    age = current_idx - seg_idx
                    fade = 1.0 - (age / trail_frames)  # Fade over trail duration
                    alpha = int(200 * max(0.1, fade))

                    # Get color based on acceleration
                    color = self.get_accel_color(avg_accel, alpha)

                    # Convert to screen coordinates
                    px1, py1 = self.world_to_screen(x1, y1)
                    px2, py2 = self.world_to_screen(x2, y2)

                    # Draw segment
                    seg_tag = f"accel_seg_{car_id}_{seg_idx - start_idx}"
                    dpg.draw_line((px1, py1), (px2, py2),
                                 color=color, thickness=3,
                                 parent=self.canvas, tag=seg_tag)
                continue

            # Handle Delta Speed mode (from pre-computed trail CSVs)
            # This shows the last 15s of each car's fastest lap with delta speed coloring
            if trail_mode == 'Delta Speed':
                # Only draw for selected cars
                is_selected = car_id in selected
                if highlight and is_any_selected and not is_selected:
                    continue

                # Get delta speed trail data
                trail_points = self.world.get_delta_speed_trail(car_id)
                if len(trail_points) < 2:
                    # Debug: print once if no trail data
                    if not hasattr(self, '_delta_speed_warning_shown'):
                        self._delta_speed_warning_shown = True
                        print(f"Delta Speed trails not available - trail_data has {len(self.world.trail_data)} entries")
                        if len(self.world.trail_data) == 0:
                            print("  Hint: Re-run preprocessing pipeline by dropping a CSV to generate trails")
                    continue

                # Draw individual segments with delta speed-based colors
                # Use lower alpha to not obscure the animation
                for seg_idx in range(len(trail_points) - 1):
                    x1, y1, delta1 = trail_points[seg_idx]
                    x2, y2, delta2 = trail_points[seg_idx + 1]

                    # Use average delta for segment color
                    avg_delta = (delta1 + delta2) / 2

                    # Lower alpha so it doesn't dominate - this is reference data
                    alpha = 120

                    # Get color based on delta speed
                    color = self.get_delta_speed_color(avg_delta, alpha)

                    # Convert to screen coordinates
                    px1, py1 = self.world_to_screen(x1, y1)
                    px2, py2 = self.world_to_screen(x2, y2)

                    # Draw segment
                    seg_tag = f"delta_seg_{car_id}_{seg_idx}"
                    dpg.draw_line((px1, py1), (px2, py2),
                                 color=color, thickness=2,
                                 parent=self.canvas, tag=seg_tag)
                continue

            # Get trail data based on mode
            if trail_mode == 'last_lap':
                trail = self.world.get_last_lap_trace(car_id)
            elif trail_mode == 'fade_3s':
                trail = self.world.get_fading_trail(car_id, 3)
            elif trail_mode == 'fade_5s':
                trail = self.world.get_fading_trail(car_id, 5)
            elif trail_mode == 'fade_10s':
                trail = self.world.get_fading_trail(car_id, 10)
            elif trail_mode == 'Custom':
                # Use duration from color config settings
                custom_duration = color_config.get_size('trail_duration_s')
                trail = self.world.get_fading_trail(car_id, custom_duration)
            else:
                trail = []

            # Skip if trail is too short (need at least 2 points)
            if len(trail) < 2:
                continue

            # Get color and alpha
            base_color = self.world.colors.get(car_id, (255, 255, 255))
            is_selected = car_id in selected

            # Skip trail for unselected cars when selection is active
            if highlight and is_any_selected and not is_selected:
                continue  # Don't draw trail at all

            # Only selected cars reach here
            alpha = 150 if is_selected else 100
            color = (base_color[0], base_color[1], base_color[2], alpha)

            # Convert to screen coordinates
            points = []
            for x, y in trail:
                px, py = self.world_to_screen(x, y)
                points.append([px, py])

            # Draw polyline
            trail_tag = f"trail_{car_id}"
            dpg.draw_polyline(points, color=color, thickness=2,
                             parent=self.canvas, tag=trail_tag)

    def draw_hover_label(self, car_id: str, mouse_x: float, mouse_y: float):
        """Draw a hover label near the mouse position."""
        label_tag = f"hover_label_{car_id}"

        # Delete old label if exists
        if dpg.does_item_exist(label_tag):
            dpg.delete_item(label_tag)

        # Draw label with background
        bg_tag = f"hover_bg_{car_id}"
        if dpg.does_item_exist(bg_tag):
            dpg.delete_item(bg_tag)

        # Position label offset from mouse
        label_x = mouse_x + 15
        label_y = mouse_y - 10

        # Draw semi-transparent background
        dpg.draw_rectangle(pmin=(label_x - 5, label_y - 5),
                          pmax=(label_x + len(car_id) * 8 + 5, label_y + 20),
                          color=(0, 0, 0, 180), fill=(0, 0, 0, 180),
                          parent=self.canvas, tag=bg_tag)

        # Draw text
        dpg.draw_text(pos=(label_x, label_y), text=car_id,
                     color=(255, 255, 255, 255), size=14,
                     parent=self.canvas, tag=label_tag)

    def clear_hover_labels(self):
        """Clear all hover labels."""
        for car_id in self.world.car_ids:
            label_tag = f"hover_label_{car_id}"
            bg_tag = f"hover_bg_{car_id}"
            if dpg.does_item_exist(label_tag):
                dpg.delete_item(label_tag)
            if dpg.does_item_exist(bg_tag):
                dpg.delete_item(bg_tag)

    def get_car_at_position(self, screen_x: float, screen_y: float, threshold: float = 15) -> str:
        """Find which car is near the given screen position.

        Args:
            screen_x, screen_y: Screen coordinates
            threshold: Distance threshold in pixels

        Returns:
            car_id if a car is nearby, None otherwise
        """
        states = self.world.get_all_car_states(self.world.current_time_ms)

        for car_id, state in states.items():
            px, py = self.world_to_screen(state['x'], state['y'])
            distance = ((px - screen_x)**2 + (py - screen_y)**2)**0.5

            if distance <= threshold:
                return car_id

        return None

    def get_cars_in_box(self, min_x: float, min_y: float, max_x: float, max_y: float) -> list:
        """Find all cars within a screen-space bounding box.

        Args:
            min_x, min_y: Top-left corner of box in screen coordinates
            max_x, max_y: Bottom-right corner of box in screen coordinates

        Returns:
            List of car_ids within the box
        """
        states = self.world.get_all_car_states(self.world.current_time_ms)
        cars_in_box = []

        for car_id, state in states.items():
            px, py = self.world_to_screen(state['x'], state['y'])

            if min_x <= px <= max_x and min_y <= py <= max_y:
                cars_in_box.append(car_id)

        return cars_in_box

    def render_frame(self):
        """Main render call - draw track once, update trails and cars."""
        # Get current theme
        theme = self.world.get_theme()

        # Draw/update background with theme color
        if not self.background_drawn:
            dpg.draw_rectangle((0, 0), (self.viewport_width, self.viewport_height),
                              fill=theme['bg'], parent=self.canvas,
                              tag="background_rect")
            self.background_drawn = True
        else:
            # Update background color if theme changed
            if dpg.does_item_exist("background_rect"):
                dpg.configure_item("background_rect", fill=theme['bg'])

        # Draw track once
        self.draw_static_track()

        # Draw trails
        self.draw_trails()

        # Update cars
        states = self.world.get_all_car_states(self.world.current_time_ms)
        self.draw_cars(states)

        # Draw race timer in top left
        self.draw_race_timer()

        # Draw HUD overlay
        self.draw_hud(states)

    def draw_race_timer(self):
        """Draw race timer display in top left corner with racing-style colors."""
        # Delete old timer elements
        for tag in ["race_timer_bg", "race_timer_label", "race_timer_time",
                    "race_timer_min", "race_timer_colon", "race_timer_sec", "race_timer_ms"]:
            if dpg.does_item_exist(tag):
                dpg.delete_item(tag)

        # Get current theme
        theme = self.world.get_theme()

        # Timer position (top left with padding)
        timer_x = 20
        timer_y = 20

        # Get current time
        time_ms = self.world.current_time_ms
        total_seconds = time_ms / 1000
        minutes = int(total_seconds // 60)
        seconds = int(total_seconds % 60)
        milliseconds = int(time_ms % 1000)  # Full milliseconds (1/1000)

        # Draw background
        dpg.draw_rectangle(
            (timer_x - 10, timer_y - 5),
            (timer_x + 200, timer_y + 45),
            fill=theme['timer_bg'],
            rounding=5,
            parent=self.canvas,
            tag="race_timer_bg"
        )

        # Draw "RACE TIME" label
        dpg.draw_text(
            (timer_x, timer_y),
            "RACE TIME",
            color=theme['text_muted'],
            size=12,
            parent=self.canvas,
            tag="race_timer_label"
        )

        # Draw time with racing-style color coding
        # Red for minutes, Orange for seconds, Green for milliseconds
        time_y = timer_y + 18
        timer_colors = color_config.get_race_timer_colors()

        # Minutes (red)
        min_text = f"{minutes:02d}"
        dpg.draw_text(
            (timer_x, time_y),
            min_text,
            color=timer_colors['minutes'],
            size=24,
            parent=self.canvas,
            tag="race_timer_min"
        )

        # Colon (gray)
        dpg.draw_text(
            (timer_x + 35, time_y),
            ":",
            color=timer_colors['separator'],
            size=24,
            parent=self.canvas,
            tag="race_timer_colon"
        )

        # Seconds (orange)
        sec_text = f"{seconds:02d}"
        dpg.draw_text(
            (timer_x + 50, time_y),
            sec_text,
            color=timer_colors['seconds'],
            size=24,
            parent=self.canvas,
            tag="race_timer_sec"
        )

        # Milliseconds (green - 1/1000)
        ms_text = f".{milliseconds:03d}"
        dpg.draw_text(
            (timer_x + 85, time_y),
            ms_text,
            color=timer_colors['milliseconds'],
            size=24,
            parent=self.canvas,
            tag="race_timer_ms"
        )

    def draw_hud(self, car_states: dict):
        """Draw HUD overlay with telemetry data for all selected cars."""
        # Get current theme
        theme = self.world.get_theme()

        # Delete all old HUD elements (support multiple cars and multiple toggles)
        for i in range(20):  # Support up to 20 cars max
            # Delete main HUD items
            for tag_prefix in ["hud_bg", "hud_header", "hud_car_name", "hud_collapse_btn",
                              "hud_speed", "hud_gear", "hud_brake", "hud_lap", "hud_time",
                              "hud_position", "hud_deviation", "hud_steering"]:
                tag = f"{tag_prefix}_{i}"
                if dpg.does_item_exist(tag):
                    dpg.delete_item(tag)

            # Delete drag handle lines
            for j in range(3):
                tag = f"hud_drag_line_{i}_{j}"
                if dpg.does_item_exist(tag):
                    dpg.delete_item(tag)

            # Delete all toggle items
            for toggle_name in ["speed", "gear", "brake", "lap", "time", "position", "deviation", "steering"]:
                tag = f"hud_toggle_{toggle_name}_{i}"
                if dpg.does_item_exist(tag):
                    dpg.delete_item(tag)

        # Clear interaction regions for fresh click detection
        self.hud_toggle_regions = {}
        self.hud_collapse_regions = {}
        self.hud_drag_regions = {}

        # Get cars to display in order
        display_cars = []
        if self.world.selected_car_ids:
            # Use custom order if set, otherwise use selection order
            if self.world.hud_order:
                # Filter to only selected cars in custom order
                display_cars = [cid for cid in self.world.hud_order if cid in self.world.selected_car_ids]
                # Add any newly selected cars not in order yet
                for cid in self.world.selected_car_ids:
                    if cid not in display_cars:
                        display_cars.append(cid)
            else:
                display_cars = self.world.selected_car_ids
                self.world.hud_order = list(display_cars)  # Initialize order
        # Hide HUD when no cars selected (removed fallback to first car)

        if not display_cars:
            return

        # Get race order once (includes lapping info)
        race_order = self.world.get_race_order(self.world.current_time_ms)

        # HUD starting position (top-right corner)
        hud_start_x = self.viewport_width - 200
        hud_start_y = 20
        hud_spacing = 5  # Space between HUDs
        toggle_x_offset = 150  # X position for toggle indicators
        header_height = 25  # Height of collapsible header

        current_y = hud_start_y

        for idx, car_id in enumerate(display_cars):
            if car_id not in car_states:
                continue

            state = car_states[car_id]

            # Initialize collapse state if not set
            if car_id not in self.world.hud_collapsed:
                self.world.hud_collapsed[car_id] = False

            # Initialize per-car HUD item visibility if not set (copy from global defaults)
            if car_id not in self.world.hud_items_visible:
                self.world.hud_items_visible[car_id] = {
                    'speed': self.world.hud_show_speed,
                    'gear': self.world.hud_show_gear,
                    'brake': self.world.hud_show_brake,
                    'lap': self.world.hud_show_lap,
                    'time': self.world.hud_show_time,
                    'position': self.world.hud_show_position,
                    'deviation': self.world.hud_show_deviation,
                    'steering': self.world.hud_show_steering,
                }

            is_collapsed = self.world.hud_collapsed[car_id]

            # Get car color
            car_color = self.world.colors.get(car_id, (255, 255, 255))

            # Build HUD items list (only if not collapsed)
            hud_items = []
            y_offset = header_height

            # Get per-car visibility settings
            car_hud_visible = self.world.hud_items_visible[car_id]

            # Speed
            if car_hud_visible.get('speed', True):
                speed = state.get('speed', 0)
                hud_items.append({
                    'y': y_offset, 'text': f"{speed:.0f} mph", 'color': theme['text'],
                    'size': 20, 'tag_prefix': 'speed', 'toggle': 'speed'
                })
                y_offset += 25

            # Gear
            if car_hud_visible.get('gear', True):
                gear = state.get('gear', 0)
                gear_display = "N" if gear == 0 else str(int(gear))
                hud_items.append({
                    'y': y_offset, 'text': f"Gear: {gear_display}", 'color': theme['text_secondary'],
                    'size': 14, 'tag_prefix': 'gear', 'toggle': 'gear'
                })
                y_offset += 18

            # Brake (show if Circle Glow enabled OR if HUD brake is on)
            show_brake_in_hud = car_hud_visible.get('brake', True) or self.world.show_circle_glow or self.world.show_circle_glow_all
            if show_brake_in_hud:
                brake = state.get('brake', 0) * 100
                brake_color = (255, 100, 100) if brake > 5 else theme['text_secondary']
                hud_items.append({
                    'y': y_offset, 'text': f"Brake: {brake:.0f}%", 'color': brake_color,
                    'size': 14, 'tag_prefix': 'brake', 'toggle': 'brake'
                })
                y_offset += 18

            # Deviation (show if Lateral Diff enabled)
            if (self.world.show_lateral_diff or self.world.show_lateral_diff_all):
                if car_hud_visible.get('deviation', False):
                    deviation = state.get('deviation', 0.0)
                    dev_color = (255, 68, 68) if deviation > 0 else (68, 119, 255) if deviation < 0 else theme['text_secondary']
                    hud_items.append({
                        'y': y_offset, 'text': f"Dev: {deviation:+.2f}m", 'color': dev_color,
                        'size': 14, 'tag_prefix': 'deviation', 'toggle': 'deviation'
                    })
                    y_offset += 18

            # Steering (show if Steering Angle enabled)
            if (self.world.show_steering_angle or self.world.show_steering_angle_all):
                if car_hud_visible.get('steering', False):
                    steering = state.get('steering', 0)
                    hud_items.append({
                        'y': y_offset, 'text': f"Steer: {steering:+.1f}°", 'color': theme['text_secondary'],
                        'size': 14, 'tag_prefix': 'steering', 'toggle': 'steering'
                    })
                    y_offset += 18

            # Lap
            if car_hud_visible.get('lap', True):
                lap = state.get('lap', 1)
                hud_items.append({
                    'y': y_offset, 'text': f"Lap: {int(lap)}", 'color': theme['text_secondary'],
                    'size': 14, 'tag_prefix': 'lap', 'toggle': 'lap'
                })
                y_offset += 18

            # Time (only show on first HUD)
            if idx == 0 and car_hud_visible.get('time', True):
                time_s = self.world.current_time_ms / 1000
                minutes = int(time_s // 60)
                seconds = time_s % 60
                hud_items.append({
                    'y': y_offset, 'text': f"{minutes:02d}:{seconds:04.1f}", 'color': (255, 255, 0),
                    'size': 14, 'tag_prefix': 'time', 'toggle': 'time'
                })
                y_offset += 18

            # Position
            if car_hud_visible.get('position', True):
                car_info = race_order["cars"].get(car_id, {})
                pos = car_info.get("position", "-")
                is_leader = car_info.get("is_leader", False)
                laps_down = car_info.get("laps_down", 0)

                # Format position text
                if is_leader:
                    pos_text = "LEADER"
                    pos_color = (255, 215, 0)  # Gold for leader
                elif laps_down > 0:
                    pos_text = f"P{pos} L{laps_down}"
                    pos_color = (255, 100, 100)  # Red-ish for lapped
                else:
                    pos_text = f"P{pos}"
                    pos_color = theme['accent']

                hud_items.append({
                    'y': y_offset, 'text': pos_text, 'color': pos_color,
                    'size': 14, 'tag_prefix': 'position', 'toggle': 'position'
                })
                y_offset += 18

            # Calculate total HUD height
            if is_collapsed:
                hud_height = header_height
            else:
                hud_height = y_offset + 5

            # Position for this HUD panel
            hud_x = hud_start_x
            hud_y = current_y

            # Draw semi-transparent background
            dpg.draw_rectangle(
                (hud_x - 10, hud_y),
                (hud_x + 190, hud_y + hud_height),
                fill=theme['panel_bg_alpha'],
                parent=self.canvas,
                tag=f"hud_bg_{idx}"
            )

            # Draw header bar (darker background for dragging)
            dpg.draw_rectangle(
                (hud_x - 10, hud_y),
                (hud_x + 190, hud_y + header_height),
                fill=theme['header_bg'],
                parent=self.canvas,
                tag=f"hud_header_{idx}"
            )

            # Draw drag handle (3 horizontal lines on left)
            drag_handle_x = hud_x - 5
            for i in range(3):
                line_y = hud_y + 8 + (i * 4)
                dpg.draw_line(
                    (drag_handle_x, line_y),
                    (drag_handle_x + 10, line_y),
                    color=(150, 150, 150),
                    thickness=1,
                    parent=self.canvas,
                    tag=f"hud_drag_line_{idx}_{i}"
                )

            # Store drag region - make entire header draggable (except collapse button area on right)
            self.hud_drag_regions[car_id] = (hud_x - 10, hud_y, 170, header_height)

            # Draw car name in header
            dpg.draw_text(
                (hud_x + 15, hud_y + 5),
                car_id[-6:],
                color=car_color,
                size=16,
                parent=self.canvas,
                tag=f"hud_car_name_{idx}"
            )

            # Draw collapse/expand button (triangle)
            collapse_btn_x = hud_x + 170
            collapse_btn_y = hud_y + 12
            collapse_size = 8

            if is_collapsed:
                # Draw right-pointing triangle (collapsed)
                dpg.draw_triangle(
                    (collapse_btn_x, collapse_btn_y - collapse_size // 2),
                    (collapse_btn_x, collapse_btn_y + collapse_size // 2),
                    (collapse_btn_x + collapse_size, collapse_btn_y),
                    color=(200, 200, 200),
                    fill=(200, 200, 200),
                    parent=self.canvas,
                    tag=f"hud_collapse_btn_{idx}"
                )
            else:
                # Draw down-pointing triangle (expanded)
                dpg.draw_triangle(
                    (collapse_btn_x - collapse_size // 2, collapse_btn_y),
                    (collapse_btn_x + collapse_size // 2, collapse_btn_y),
                    (collapse_btn_x, collapse_btn_y + collapse_size),
                    color=(200, 200, 200),
                    fill=(200, 200, 200),
                    parent=self.canvas,
                    tag=f"hud_collapse_btn_{idx}"
                )

            # Store collapse button region
            self.hud_collapse_regions[car_id] = (collapse_btn_x - 10, collapse_btn_y - 10, 20, 20)

            # Draw HUD items (only if not collapsed)
            if not is_collapsed:
                for item_idx, item in enumerate(hud_items):
                    item_y = hud_y + item['y']
                    text_tag = f"hud_{item['tag_prefix']}_{idx}_{item_idx}"
                    if dpg.does_item_exist(text_tag):
                        dpg.delete_item(text_tag)
                    dpg.draw_text(
                        (hud_x, item_y),
                        item['text'],
                        color=item['color'],
                        size=item['size'],
                        parent=self.canvas,
                        tag=text_tag
                    )

                    # Draw toggle indicator
                    if item['toggle']:
                        toggle_enabled = car_hud_visible.get(item['toggle'], True)
                        toggle_color = (100, 255, 100) if toggle_enabled else (100, 100, 100)
                        toggle_size = 8
                        toggle_x = hud_x + toggle_x_offset
                        toggle_y = item_y + (item['size'] // 2) - (toggle_size // 2)

                        toggle_tag = f"hud_toggle_{item['tag_prefix']}_{idx}_{item_idx}"
                        if dpg.does_item_exist(toggle_tag):
                            dpg.delete_item(toggle_tag)
                        dpg.draw_rectangle(
                            (toggle_x, toggle_y),
                            (toggle_x + toggle_size, toggle_y + toggle_size),
                            fill=toggle_color,
                            color=toggle_color,
                            parent=self.canvas,
                            tag=toggle_tag
                        )

                        # Store clickable region for this toggle (use unique key per HUD)
                        toggle_key = f"{item['toggle']}_{car_id}"
                        self.hud_toggle_regions[toggle_key] = (toggle_x, toggle_y, toggle_size, toggle_size)

            # Update Y position for next panel
            current_y += hud_height + hud_spacing

    def reset(self):
        """Reset renderer state (e.g., when loading new data)."""
        self.track_drawn = False
        self.car_items = {}

    def invalidate_track(self):
        """Force track redraw on next frame (needed after zoom/pan)."""
        if dpg.does_item_exist("track_line"):
            dpg.delete_item("track_line")
        self.track_drawn = False
        # Also clear background to redraw
        if dpg.does_item_exist("background_rect"):
            dpg.delete_item("background_rect")
        self.background_drawn = False

    def reset_view(self):
        """Reset zoom and pan to default view."""
        self.zoom_level = 1.0
        self.pan_offset_x = 0.0
        self.pan_offset_y = 0.0
        self.invalidate_track()

    def on_mouse_wheel(self, sender, app_data):
        """Handle zoom via mouse wheel (only when over canvas)."""
        # Get mouse position in global screen coordinates
        mouse_pos = dpg.get_mouse_pos(local=False)

        # Get canvas_window position and size
        if not dpg.does_item_exist("canvas_window"):
            return

        canvas_pos = dpg.get_item_pos("canvas_window")
        canvas_size = dpg.get_item_rect_size("canvas_window")

        # Check if mouse is within canvas_window bounds
        if (mouse_pos[0] < canvas_pos[0] or
            mouse_pos[0] > canvas_pos[0] + canvas_size[0] or
            mouse_pos[1] < canvas_pos[1] or
            mouse_pos[1] > canvas_pos[1] + canvas_size[1]):
            return

        # app_data is the wheel delta
        zoom_speed = 0.1
        if app_data > 0:
            # Zoom in
            self.zoom_level *= (1.0 + zoom_speed)
        else:
            # Zoom out
            self.zoom_level *= (1.0 - zoom_speed)

        # Clamp zoom level
        self.zoom_level = max(0.5, min(10.0, self.zoom_level))

        # Redraw track with new zoom
        self.invalidate_track()

    def on_mouse_click(self, sender, app_data):
        """Handle mouse clicks for pause, car selection, and HUD interaction."""
        # Get mouse position in screen coordinates
        mouse_pos = dpg.get_mouse_pos(local=False)

        # Check if click is on any overlay window (color customization, color picker, etc.)
        # These windows should block track click events
        overlay_windows = [
            "color_customization_window",
            "color_picker_window",
        ]

        for window_tag in overlay_windows:
            if dpg.does_item_exist(window_tag) and dpg.is_item_shown(window_tag):
                # Get window position and size
                try:
                    win_pos = dpg.get_item_pos(window_tag)
                    win_size = dpg.get_item_rect_size(window_tag)

                    # Check if mouse is within this window
                    if (win_pos[0] <= mouse_pos[0] <= win_pos[0] + win_size[0] and
                        win_pos[1] <= mouse_pos[1] <= win_pos[1] + win_size[1]):
                        # Click is on overlay window, don't process as track click
                        return
                except Exception:
                    pass

        # Get canvas offset
        if not dpg.does_item_exist("canvas_window"):
            return

        canvas_pos = dpg.get_item_pos("canvas_window")
        canvas_size = dpg.get_item_rect_size("canvas_window")

        # Convert mouse position to canvas-relative coordinates
        canvas_mouse_x = mouse_pos[0] - canvas_pos[0]
        canvas_mouse_y = mouse_pos[1] - canvas_pos[1]

        # Check if click is outside canvas bounds
        if (canvas_mouse_x < 0 or canvas_mouse_x > canvas_size[0] or
            canvas_mouse_y < 0 or canvas_mouse_y > canvas_size[1]):
            return

        # Check collapse button regions first (highest priority - small specific area)
        for car_id, (x, y, w, h) in self.hud_collapse_regions.items():
            if (canvas_mouse_x >= x and canvas_mouse_x <= x + w and
                canvas_mouse_y >= y and canvas_mouse_y <= y + h):
                # Collapse button clicked
                self.world.hud_collapsed[car_id] = not self.world.hud_collapsed.get(car_id, False)
                print(f"Toggled collapse for {car_id}: {self.world.hud_collapsed[car_id]}")
                return

        # Check drag handle regions (header bar - for starting drag)
        # This has second priority, larger area than collapse button
        for car_id, (x, y, w, h) in self.hud_drag_regions.items():
            if (canvas_mouse_x >= x and canvas_mouse_x <= x + w and
                canvas_mouse_y >= y and canvas_mouse_y <= y + h):
                # Start dragging
                self.dragging_hud = car_id
                self.drag_start_y = canvas_mouse_y
                print(f"Started dragging {car_id}")
                return

        # Check toggle regions
        for toggle_key, (x, y, w, h) in self.hud_toggle_regions.items():
            if (canvas_mouse_x >= x and canvas_mouse_x <= x + w and
                canvas_mouse_y >= y and canvas_mouse_y <= y + h):
                # Toggle was clicked - extract toggle name and car_id from composite key (format: "speed_GR86-002-000")
                # Split by underscore and take everything before the car ID (which starts with GR86)
                parts = toggle_key.split('_')
                toggle_name = parts[0]  # First part is always the toggle name (speed, gear, brake, etc.)
                car_id = '_'.join(parts[1:])  # Rest is the car ID (may contain underscores)

                # Toggle the per-car visibility
                if car_id in self.world.hud_items_visible:
                    current_value = self.world.hud_items_visible[car_id].get(toggle_name, True)
                    new_value = not current_value
                    self.world.hud_items_visible[car_id][toggle_name] = new_value
                    print(f"Toggled {toggle_name} for {car_id}: {current_value} -> {new_value}")
                return

        # Click is on track area (not on HUD elements)
        # Check if clicking on a car first (works whether paused or not)
        clicked_car = self.get_car_at_position(canvas_mouse_x, canvas_mouse_y)

        if clicked_car:
            # Clicking on a car - toggle selection
            if clicked_car in self.world.selected_car_ids:
                self.world.selected_car_ids.remove(clicked_car)
                print(f"Deselected car: {clicked_car}")
            else:
                self.world.selected_car_ids.append(clicked_car)
                print(f"Selected car: {clicked_car}")
        else:
            # Clicking on empty track - toggle pause state using controls
            if self.controls:
                if self.controls.is_playing:
                    self.controls.pause()
                    print("Animation paused - click on track")
                    # Store start position for potential box selection
                    self.box_select_start = (canvas_mouse_x, canvas_mouse_y)
                else:
                    self.controls.play()
                    print("Animation resumed - click on track")
            else:
                # Fallback if controls not set
                if not self.world.is_paused:
                    self.world.is_paused = True
                    print("Animation paused - click on track")
                    self.box_select_start = (canvas_mouse_x, canvas_mouse_y)
                else:
                    self.world.is_paused = False
                    print("Animation resumed - click on track")

    def on_mouse_release(self, sender, app_data):
        """Handle mouse release to end HUD dragging and box selection."""
        if self.dragging_hud:
            # Get mouse position
            mouse_pos = dpg.get_mouse_pos(local=False)
            if dpg.does_item_exist("canvas_window"):
                canvas_pos = dpg.get_item_pos("canvas_window")
                canvas_mouse_y = mouse_pos[1] - canvas_pos[1]

                # Calculate which position this should be in the order
                # Based on the Y position, determine the new index
                hud_height_approx = 30  # Approximate header height
                new_index = max(0, min(len(self.world.hud_order) - 1, int(canvas_mouse_y / hud_height_approx)))

                # Reorder the HUD list
                if self.dragging_hud in self.world.hud_order:
                    old_index = self.world.hud_order.index(self.dragging_hud)
                    self.world.hud_order.pop(old_index)
                    self.world.hud_order.insert(new_index, self.dragging_hud)
                    print(f"Moved {self.dragging_hud} from {old_index} to {new_index}")

            self.dragging_hud = None
            self.drag_start_y = 0

        # Handle box selection completion
        if self.box_select_active and self.box_select_start:
            mouse_pos = dpg.get_mouse_pos(local=False)
            if dpg.does_item_exist("canvas_window"):
                canvas_pos = dpg.get_item_pos("canvas_window")
                end_x = mouse_pos[0] - canvas_pos[0]
                end_y = mouse_pos[1] - canvas_pos[1]
                start_x, start_y = self.box_select_start

                # Get box bounds
                min_x = min(start_x, end_x)
                max_x = max(start_x, end_x)
                min_y = min(start_y, end_y)
                max_y = max(start_y, end_y)

                # Only process if box has significant size
                if max_x - min_x > 5 and max_y - min_y > 5:
                    # Find all cars within the box
                    selected_cars = self.get_cars_in_box(min_x, min_y, max_x, max_y)
                    for car_id in selected_cars:
                        if car_id not in self.world.selected_car_ids:
                            self.world.selected_car_ids.append(car_id)
                    print(f"Box selected {len(selected_cars)} cars")

                # Delete selection rectangle
                if dpg.does_item_exist("box_select_rect"):
                    dpg.delete_item("box_select_rect")

            self.box_select_active = False
            self.box_select_start = None

    def on_hud_drag(self, sender, app_data):
        """Handle HUD dragging with left mouse button and box selection.

        app_data contains: [button, delta_x, delta_y]
        """
        # Only process if we're actively dragging a HUD
        if self.dragging_hud:
            # HUD is being dragged, just update visual feedback
            # The actual reordering happens on mouse release
            return

        # Handle box selection drawing
        if self.box_select_active and self.box_select_start:
            mouse_pos = dpg.get_mouse_pos(local=False)
            if dpg.does_item_exist("canvas_window"):
                canvas_pos = dpg.get_item_pos("canvas_window")
                end_x = mouse_pos[0] - canvas_pos[0]
                end_y = mouse_pos[1] - canvas_pos[1]
                start_x, start_y = self.box_select_start

                # Delete old rectangle
                if dpg.does_item_exist("box_select_rect"):
                    dpg.delete_item("box_select_rect")

                # Draw selection rectangle
                dpg.draw_rectangle(
                    [start_x, start_y], [end_x, end_y],
                    color=(100, 200, 255, 200),
                    fill=(100, 200, 255, 50),
                    thickness=2,
                    parent=self.canvas,
                    tag="box_select_rect"
                )

    def on_mouse_drag(self, sender, app_data):
        """Handle pan drag with right mouse button only.

        app_data contains: [button, delta_x, delta_y]
        """
        # Only handle right button panning
        # Check if mouse is over canvas
        mouse_pos = dpg.get_mouse_pos(local=False)

        if not dpg.does_item_exist("canvas_window"):
            return

        canvas_pos = dpg.get_item_pos("canvas_window")
        canvas_size = dpg.get_item_rect_size("canvas_window")

        # Only pan if mouse is over canvas
        if (mouse_pos[0] < canvas_pos[0] or
            mouse_pos[0] > canvas_pos[0] + canvas_size[0] or
            mouse_pos[1] < canvas_pos[1] or
            mouse_pos[1] > canvas_pos[1] + canvas_size[1]):
            return

        # Get CUMULATIVE delta from app_data (total since drag started)
        # Note: app_data contains [button, cumulative_delta_x, cumulative_delta_y]
        cumulative_dx = app_data[1]
        cumulative_dy = app_data[2]

        # Detect new drag (cumulative resets to near zero)
        if abs(cumulative_dx) < 1 and abs(cumulative_dy) < 1:
            self.last_drag_delta_x = 0.0
            self.last_drag_delta_y = 0.0

        # Compute per-frame delta from cumulative
        dx = cumulative_dx - self.last_drag_delta_x
        dy = cumulative_dy - self.last_drag_delta_y

        # Update tracked cumulative
        self.last_drag_delta_x = cumulative_dx
        self.last_drag_delta_y = cumulative_dy

        # Skip if no movement
        if abs(dx) < 0.1 and abs(dy) < 0.1:
            return

        # Convert screen delta to world delta
        # Must match the scale calculation in world_to_screen() for 1:1 pixel movement
        bounds = self.world.bounds
        x_range = bounds['x_max'] - bounds['x_min']
        y_range = bounds['y_max'] - bounds['y_min']

        # Account for 15% padding on each side (1.3x total range)
        padded_x_range = x_range * 1.3
        padded_y_range = y_range * 1.3

        # Calculate actual render scale (same logic as world_to_screen)
        data_aspect = padded_x_range / padded_y_range if padded_y_range != 0 else 1.0
        canvas_aspect = self.viewport_width / self.viewport_height

        if data_aspect > canvas_aspect:
            # Fit to width
            h_scale = self.viewport_width
            v_scale = self.viewport_width / data_aspect
        else:
            # Fit to height
            h_scale = self.viewport_height * data_aspect
            v_scale = self.viewport_height

        # Convert using correct scales (1:1 pixel movement)
        world_dx = (dx / h_scale) * padded_x_range / self.zoom_level
        world_dy = -(dy / v_scale) * padded_y_range / self.zoom_level  # Flip Y

        # Update pan offset
        self.pan_offset_x -= world_dx
        self.pan_offset_y -= world_dy

        # Redraw track
        self.invalidate_track()
