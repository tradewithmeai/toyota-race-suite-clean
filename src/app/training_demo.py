"""Training demo system - orchestrates automated demo of all features."""

import time
import json
import os
import dearpygui.dearpygui as dpg

from app.demo_cursor import DemoCursor
from app.demo_script import DemoScript
from app.hackathon_demo_script import HackathonDemoScript
from app.message_overlay import show_message, clear_all_messages


def should_show_demo():
    """Check if demo should be shown (first launch).

    Returns:
        bool: True if demo should be shown
    """
    config_file = os.path.join(os.path.expanduser("~"), ".race_replay_config.json")
    if not os.path.exists(config_file):
        return True

    try:
        with open(config_file, 'r') as f:
            config = json.load(f)
        return not config.get('demo_completed', False)
    except Exception as e:
        print(f"Error reading demo config: {e}")
        return True


def mark_demo_completed():
    """Mark demo as completed in config file."""
    config_file = os.path.join(os.path.expanduser("~"), ".race_replay_config.json")
    config = {}

    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                config = json.load(f)
        except Exception as e:
            print(f"Error reading config: {e}")

    config['demo_completed'] = True

    try:
        with open(config_file, 'w') as f:
            json.dump(config, f)
    except Exception as e:
        print(f"Error saving demo config: {e}")


class ActionExecutor:
    """Executes demo actions on the application."""

    def __init__(self, world_model, renderer, controls, telemetry):
        self.world = world_model
        self.renderer = renderer
        self.controls = controls
        self.telemetry = telemetry
        self.scheduled_actions = []  # (execute_time, action)

    def execute(self, action):
        """Execute a demo action.

        Args:
            action: Action dictionary with type, target, delay, etc.
        """
        delay = action.get('delay', 0.0)

        if delay > 0:
            # Schedule for later execution
            execute_time = time.time() + delay
            self.scheduled_actions.append((execute_time, action))
        else:
            # Execute immediately
            self._execute_now(action)

    def update(self):
        """Update scheduled actions."""
        current_time = time.time()
        remaining = []

        for execute_time, action in self.scheduled_actions:
            if current_time >= execute_time:
                self._execute_now(action)
            else:
                remaining.append((execute_time, action))

        self.scheduled_actions = remaining

    def _execute_now(self, action):
        """Execute action immediately.

        Args:
            action: Action dictionary
        """
        action_type = action['type']

        if action_type == 'ui_click':
            self._execute_ui_click(action)
        elif action_type == 'enable_checkbox':
            self._execute_enable_checkbox(action)
        elif action_type == 'set_dropdown':
            self._execute_set_dropdown(action)
        elif action_type == 'animate_slider':
            self._execute_animate_slider(action)
        elif action_type == 'select_car':
            self._execute_select_car(action)
        elif action_type == 'simulate_track_click':
            self._execute_track_click(action)
        elif action_type == 'wait':
            pass  # Wait actions are just delays
        elif action_type == 'close_color_menu':
            self._execute_close_color_menu(action)
        elif action_type == 'demo_zoom':
            self._execute_demo_zoom(action)
        elif action_type == 'demo_pan':
            self._execute_demo_pan(action)
        elif action_type == 'trigger_cursor_click':
            # Trigger cursor click animation (handled by parent)
            pass

    def _execute_ui_click(self, action):
        """Execute UI button click."""
        target = action['target']

        # Map button labels to methods
        if target == 'Play':
            self.controls.play()
        elif target == 'Pause':
            self.controls.pause()
        elif target == 'Restart':
            self.controls.restart()
        elif target == 'Visuals - Custom':
            # Open color customization menu
            if hasattr(self.telemetry, 'open_color_customization'):
                self.telemetry.open_color_customization()
        elif target == 'Reset View':
            # Reset camera view
            if hasattr(self.telemetry, 'reset_view'):
                self.telemetry.reset_view()

    def _execute_enable_checkbox(self, action):
        """Enable a checkbox."""
        target = action['target']

        if dpg.does_item_exist(target):
            dpg.set_value(target, True)
            # Trigger callback
            callback = dpg.get_item_callback(target)
            if callback:
                callback(target, True)

    def _execute_set_dropdown(self, action):
        """Set dropdown value."""
        target = action['target']
        value = action['value']

        if dpg.does_item_exist(target):
            dpg.set_value(target, value)
            # Trigger callback
            callback = dpg.get_item_callback(target)
            if callback:
                callback(target, value)

    def _execute_animate_slider(self, action):
        """Animate slider value change."""
        target = action['target']
        to_value = action['to']

        if dpg.does_item_exist(target):
            # For simplicity, just set the value directly
            # Could add smooth animation in future
            dpg.set_value(target, to_value)
            # Trigger callback
            callback = dpg.get_item_callback(target)
            if callback:
                callback(target, to_value)

    def _execute_select_car(self, action):
        """Select a car."""
        car_index = action['car_index']
        add_to_selection = action.get('add_to_selection', False)

        if car_index < len(self.world.car_ids):
            car_id = self.world.car_ids[car_index]

            if add_to_selection:
                # Add to selection
                if car_id not in self.world.selected_car_ids:
                    self.world.selected_car_ids.append(car_id)
            else:
                # Replace selection
                self.world.selected_car_ids = [car_id]

    def _execute_track_click(self, action):
        """Simulate track click for pause/play."""
        # Toggle pause state
        if self.controls.is_playing:
            self.controls.pause()
        else:
            self.controls.play()

    def _execute_close_color_menu(self, action):
        """Close color customization menu."""
        # Check if color menu window exists and close it
        if dpg.does_item_exist("color_customization_window"):
            dpg.delete_item("color_customization_window")

    def _execute_demo_zoom(self, action):
        """Demonstrate zoom."""
        zoom_to = action['zoom_to']
        self.renderer.zoom_level = zoom_to
        self.renderer.invalidate_track()

    def _execute_demo_pan(self, action):
        """Demonstrate pan."""
        pan_x = action.get('pan_x', 0)
        pan_y = action.get('pan_y', 0)
        self.renderer.pan_offset_x += pan_x
        self.renderer.pan_offset_y += pan_y
        self.renderer.invalidate_track()


class CameraController:
    """Smooth camera transitions for demo."""

    def __init__(self, renderer):
        self.renderer = renderer
        self.animating = False
        self.start_zoom = 1.0
        self.target_zoom = 1.0
        self.start_pan_x = 0.0
        self.start_pan_y = 0.0
        self.target_pan_x = 0.0
        self.target_pan_y = 0.0
        self.animation_progress = 0.0
        self.animation_duration = 1.0

    def animate_to(self, camera_spec):
        """Start camera animation.

        Args:
            camera_spec: Dictionary with zoom, pan_to, duration
        """
        if camera_spec is None:
            return

        self.start_zoom = self.renderer.zoom_level
        self.target_zoom = camera_spec.get('zoom', self.start_zoom)

        # Handle pan target
        pan_to = camera_spec.get('pan_to')
        if pan_to:
            # For now, keep current pan (can implement pan-to-car later)
            self.target_pan_x = self.renderer.pan_offset_x
            self.target_pan_y = self.renderer.pan_offset_y
        else:
            self.target_pan_x = self.renderer.pan_offset_x
            self.target_pan_y = self.renderer.pan_offset_y

        self.start_pan_x = self.renderer.pan_offset_x
        self.start_pan_y = self.renderer.pan_offset_y

        self.animation_duration = camera_spec.get('duration', 2.0)
        self.animation_progress = 0.0
        self.animating = True

    def update(self, delta_time):
        """Update camera animation.

        Args:
            delta_time: Time since last frame in seconds
        """
        if not self.animating:
            return

        self.animation_progress += delta_time / self.animation_duration

        if self.animation_progress >= 1.0:
            # Complete animation
            self.renderer.zoom_level = self.target_zoom
            self.renderer.pan_offset_x = self.target_pan_x
            self.renderer.pan_offset_y = self.target_pan_y
            self.animating = False
            self.renderer.invalidate_track()
        else:
            # Interpolate with ease-in-out
            t = self._ease_in_out_quad(self.animation_progress)
            self.renderer.zoom_level = self.start_zoom + (self.target_zoom - self.start_zoom) * t
            self.renderer.pan_offset_x = self.start_pan_x + (self.target_pan_x - self.start_pan_x) * t
            self.renderer.pan_offset_y = self.start_pan_y + (self.target_pan_y - self.start_pan_y) * t
            self.renderer.invalidate_track()

    def _ease_in_out_quad(self, t):
        """Quadratic easing function."""
        if t < 0.5:
            return 2 * t * t
        else:
            return 1 - pow(-2 * t + 2, 2) / 2


class DemoStateManager:
    """Main orchestrator for training demo."""

    def __init__(self, world_model, renderer, controls, telemetry, use_hackathon_script=False):
        self.world = world_model
        self.renderer = renderer
        self.controls = controls
        self.telemetry = telemetry

        # Demo state
        self.is_running = False
        self.current_step_index = 0
        self.step_start_time = 0.0
        self.skip_requested = False
        self._cursor_click_scheduled = False
        self._cursor_click_time = 0.0

        # Components
        self.cursor = DemoCursor()
        # Choose script: hackathon (2.5 min) or full training (3.5 min)
        if use_hackathon_script:
            self.script = HackathonDemoScript()
        else:
            self.script = DemoScript()
        self.action_executor = ActionExecutor(world_model, renderer, controls, telemetry)
        self.camera_controller = CameraController(renderer)

    def start_demo(self):
        """Initialize and start demo sequence."""
        print("Starting training demo...")
        self.is_running = True
        self.current_step_index = 0
        self.step_start_time = time.time()
        self.skip_requested = False

        # Position cursor at center
        viewport_width = dpg.get_viewport_width()
        viewport_height = dpg.get_viewport_height()
        self.cursor.x = viewport_width / 2
        self.cursor.y = viewport_height / 2
        self.cursor.show()

        # Start first step
        self._begin_step(0)

    def update(self, delta_time):
        """Update demo state.

        Args:
            delta_time: Time since last frame in seconds

        Returns:
            bool: True if demo is still running
        """
        if not self.is_running:
            return False

        if self.skip_requested:
            self._end_demo()
            return False

        # Update cursor animation
        self.cursor.update(delta_time)

        # Update camera animation
        self.camera_controller.update(delta_time)

        # Update scheduled actions
        self.action_executor.update()

        # Check for scheduled cursor click
        if self._cursor_click_scheduled and time.time() >= self._cursor_click_time:
            self.cursor.trigger_click()
            self._cursor_click_scheduled = False

        # Check if current step is complete
        step = self.script.steps[self.current_step_index]
        step_elapsed = time.time() - self.step_start_time

        if step_elapsed >= step['duration']:
            self._advance_to_next_step()

        return True

    def request_skip(self):
        """Request to skip demo (called by ESC key handler)."""
        self.skip_requested = True

    def _begin_step(self, step_index):
        """Initialize a demo step.

        Args:
            step_index: Index of step to begin
        """
        if step_index >= len(self.script.steps):
            self._end_demo()
            return

        step = self.script.steps[step_index]
        print(f"Demo step {step_index + 1}/{len(self.script.steps)}: {step['id']}")

        # Show message
        if step.get('message'):
            show_message(step['message'], duration=step['duration'])

        # Move cursor
        if step.get('cursor_target'):
            target_pos = self._resolve_cursor_target(step['cursor_target'])
            if target_pos:
                self.cursor.move_to(target_pos, duration=1.0)

                # Trigger click animation if specified
                if step.get('cursor_click'):
                    # Schedule click after cursor reaches target (handled here, not via action_executor)
                    # Will trigger in update loop when cursor reaches target
                    self._cursor_click_scheduled = True
                    self._cursor_click_time = time.time() + 1.2
        else:
            self._cursor_click_scheduled = False

        # Execute actions
        if step.get('actions'):
            for action in step['actions']:
                self.action_executor.execute(action)

        # Camera movement
        if step.get('camera'):
            self.camera_controller.animate_to(step['camera'])

    def _advance_to_next_step(self):
        """Move to next step or end demo."""
        self.current_step_index += 1

        if self.current_step_index >= len(self.script.steps):
            self._end_demo()
        else:
            self.step_start_time = time.time()
            self._begin_step(self.current_step_index)

    def _end_demo(self):
        """Complete demo and return to normal mode."""
        print("Training demo completed")
        self.is_running = False
        clear_all_messages()
        self.cursor.hide()
        mark_demo_completed()

    def _resolve_cursor_target(self, target_spec):
        """Resolve cursor target specification to screen coordinates.

        Args:
            target_spec: Tuple describing target (type, ...)

        Returns:
            (x, y) screen coordinates or None
        """
        if not target_spec:
            return None

        target_type = target_spec[0]

        if target_type == 'center':
            # Center of viewport
            viewport_width = dpg.get_viewport_width()
            viewport_height = dpg.get_viewport_height()
            return (viewport_width / 2, viewport_height / 2)

        elif target_type == 'ui_element':
            # UI element by tag
            tag = target_spec[1]
            if dpg.does_item_exist(tag):
                pos = dpg.get_item_pos(tag)
                state = dpg.get_item_state(tag)
                rect = state.get('rect_size', (100, 20))
                # Center of element
                return (pos[0] + rect[0] / 2, pos[1] + rect[1] / 2)

        elif target_type == 'ui_button':
            # Button by label (search for it)
            label = target_spec[1]
            # Simple approach: assume button is in control panel at specific positions
            # In real implementation, would search for button by label
            return (140, 300)  # Approximate control panel position

        elif target_type == 'car':
            # Car position (world to screen)
            car_index = target_spec[1]
            if car_index < len(self.world.car_ids):
                car_id = self.world.car_ids[car_index]
                state = self.world.get_car_state(car_id, self.world.current_time_ms)
                if state:
                    screen_pos = self.renderer.world_to_screen(state['x'], state['y'])
                    return screen_pos

        elif target_type == 'selected_car':
            # Currently selected car
            if self.world.selected_car_ids:
                car_id = self.world.selected_car_ids[0]
                state = self.world.get_car_state(car_id, self.world.current_time_ms)
                if state:
                    screen_pos = self.renderer.world_to_screen(state['x'], state['y'])

                    # Apply offset if specified
                    if len(target_spec) >= 4 and target_spec[1] == 'offset':
                        offset_x = target_spec[2]
                        offset_y = target_spec[3]
                        return (screen_pos[0] + offset_x, screen_pos[1] + offset_y)

                    return screen_pos

        elif target_type == 'track_pos':
            # Relative position in track area (0-1 range)
            rel_x = target_spec[1]
            rel_y = target_spec[2]

            # Get canvas window dimensions
            canvas_rect = dpg.get_item_rect_size("canvas_window")
            return (canvas_rect[0] * rel_x + 280, canvas_rect[1] * rel_y)  # +280 for control panel

        return None

    def render(self, canvas):
        """Render demo cursor.

        Args:
            canvas: Canvas tag to render on
        """
        if self.is_running:
            self.cursor.render(canvas)
