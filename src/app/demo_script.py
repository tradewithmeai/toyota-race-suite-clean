"""Demo script - complete sequence of training demo steps."""


class DemoScript:
    """Container for demo step definitions."""

    def __init__(self):
        self.steps = self._build_steps()

    def _build_steps(self):
        """Build complete demo sequence.

        Returns:
            List of step dictionaries
        """
        return [
            # Step 1: Introduction
            {
                'id': 'intro',
                'duration': 5.0,
                'message': 'Welcome to Toyota Race Suite - Data Pipeline & Visualization System',
                'cursor_target': ('center',),
                'cursor_click': False,
                'actions': [],
                'camera': {'zoom': 1.0}
            },

            # Step 2: Data Pipeline Overview
            {
                'id': 'data_overview',
                'duration': 8.0,
                'message': 'Processing telemetry from 20 race cars in real-time',
                'cursor_target': ('ui_element', 'cars_count_text'),
                'cursor_click': False,
                'actions': [],
                'camera': {'zoom': 1.0}
            },

            # Step 3: Playback - Play
            {
                'id': 'playback_play',
                'duration': 3.0,
                'message': 'Control replay with play, pause, and speed adjustment',
                'cursor_target': ('ui_button', 'Play'),
                'cursor_click': True,
                'actions': [
                    {'type': 'ui_click', 'target': 'Play', 'delay': 1.5}
                ],
                'camera': None
            },

            # Step 4: Speed Control
            {
                'id': 'playback_speed',
                'duration': 4.0,
                'message': 'Adjust playback speed from 0.1x to 4x',
                'cursor_target': ('ui_element', 'speed_slider'),
                'cursor_click': True,
                'actions': [
                    {'type': 'animate_slider', 'target': 'speed_slider',
                     'from': 1.0, 'to': 2.0, 'duration': 2.0, 'delay': 1.0}
                ],
                'camera': None
            },

            # Step 5: Time Scrubber
            {
                'id': 'time_scrub',
                'duration': 5.0,
                'message': 'Jump to any point in the race',
                'cursor_target': ('ui_element', 'time_scrubber'),
                'cursor_click': True,
                'actions': [
                    {'type': 'animate_slider', 'target': 'time_scrubber',
                     'from_current': True, 'to': 30, 'duration': 2.5, 'delay': 1.0}
                ],
                'camera': None
            },

            # Step 6: Track Click Pause
            {
                'id': 'track_click_pause',
                'duration': 4.0,
                'message': 'Click anywhere on track for instant pause/play',
                'cursor_target': ('track_pos', 0.5, 0.5),
                'cursor_click': True,
                'actions': [
                    {'type': 'simulate_track_click', 'delay': 2.0}
                ],
                'camera': None
            },

            # Step 7: Track Click Resume
            {
                'id': 'track_click_resume',
                'duration': 4.0,
                'message': 'One click to pause, another to resume',
                'cursor_target': ('track_pos', 0.6, 0.4),
                'cursor_click': True,
                'actions': [
                    {'type': 'simulate_track_click', 'delay': 2.0}
                ],
                'camera': None
            },

            # Step 8: Car Selection
            {
                'id': 'car_select_1',
                'duration': 5.0,
                'message': 'Click cars to select them for detailed analysis',
                'cursor_target': ('car', 0),
                'cursor_click': True,
                'actions': [
                    {'type': 'select_car', 'car_index': 0, 'delay': 2.0}
                ],
                'camera': {'zoom': 2.0, 'pan_to': ('car', 0), 'duration': 2.0}
            },

            # Step 9: Multi-car Selection
            {
                'id': 'car_select_2',
                'duration': 5.0,
                'message': 'Select multiple cars for comparison',
                'cursor_target': ('car', 2),
                'cursor_click': True,
                'actions': [
                    {'type': 'select_car', 'car_index': 2, 'delay': 2.0, 'add_to_selection': True}
                ],
                'camera': {'zoom': 1.5, 'duration': 1.5}
            },

            # Step 10: Brake Arcs Introduction
            {
                'id': 'brake_arcs_enable',
                'duration': 8.0,
                'message': 'Brake Arcs: Expanding semi-rings show front and rear brake pressure',
                'cursor_target': ('ui_element', 'circle_glow_cb'),
                'cursor_click': True,
                'actions': [
                    {'type': 'enable_checkbox', 'target': 'circle_glow_cb', 'delay': 2.0}
                ],
                'camera': {'zoom': 3.0, 'pan_to': 'selected_car', 'duration': 2.0}
            },

            # Step 11: Brake Arcs Detail
            {
                'id': 'brake_arcs_detail',
                'duration': 7.0,
                'message': 'Front and rear arcs align with car motion for intuitive feedback',
                'cursor_target': ('selected_car', 'offset', 0, -30),
                'cursor_click': False,
                'actions': [],
                'camera': None
            },

            # Step 12: Lateral Deviation Enable
            {
                'id': 'lateral_diff_enable',
                'duration': 8.0,
                'message': 'Lateral Diff: Deviation from racing line as -1 to 1 metric',
                'cursor_target': ('ui_element', 'lateral_diff_cb'),
                'cursor_click': True,
                'actions': [
                    {'type': 'enable_checkbox', 'target': 'lateral_diff_cb', 'delay': 2.0}
                ],
                'camera': None
            },

            # Step 13: Lateral Deviation Detail
            {
                'id': 'lateral_diff_detail',
                'duration': 10.0,
                'message': '5 bars each side with progressive animation - instant visual feedback',
                'cursor_target': ('selected_car', 'offset', 25, 0),
                'cursor_click': False,
                'actions': [],
                'camera': None
            },

            # Step 14: Lateral Diff Reference
            {
                'id': 'lateral_diff_reference',
                'duration': 6.0,
                'message': 'Compare against different racing lines',
                'cursor_target': ('ui_element', 'lateral_diff_reference'),
                'cursor_click': True,
                'actions': [
                    {'type': 'set_dropdown', 'target': 'lateral_diff_reference',
                     'value': 'Global Racing Line', 'delay': 2.0}
                ],
                'camera': None
            },

            # Step 15: Steering Angle
            {
                'id': 'steering_enable',
                'duration': 12.0,
                'message': 'Steering Angle: Arrow shows steering input combined with heading',
                'cursor_target': ('ui_element', 'steering_angle_cb'),
                'cursor_click': True,
                'actions': [
                    {'type': 'enable_checkbox', 'target': 'steering_angle_cb', 'delay': 2.0}
                ],
                'camera': None
            },

            # Step 16: Acceleration Enable
            {
                'id': 'accel_enable',
                'duration': 8.0,
                'message': 'Accel Fill: Expanding circle shows acceleration intensity',
                'cursor_target': ('ui_element', 'circle_centre_cb'),
                'cursor_click': True,
                'actions': [
                    {'type': 'enable_checkbox', 'target': 'circle_centre_cb', 'delay': 2.0}
                ],
                'camera': None
            },

            # Step 17: Acceleration Detail
            {
                'id': 'accel_detail',
                'duration': 7.0,
                'message': 'Two metrics combined: magnitude and direction via color gradient',
                'cursor_target': ('selected_car', 'offset', 0, 0),
                'cursor_click': False,
                'actions': [],
                'camera': None
            },

            # Step 18: Delta Trail Enable
            {
                'id': 'trail_enable',
                'duration': 10.0,
                'message': 'Delta Trail: Most insightful - shows 1-15s historical path',
                'cursor_target': ('ui_element', 'trail_cb'),
                'cursor_click': True,
                'actions': [
                    {'type': 'enable_checkbox', 'target': 'trail_cb', 'delay': 2.0},
                    {'type': 'wait', 'duration': 1.0},
                    {'type': 'set_dropdown', 'target': 'trail_mode',
                     'value': 'Delta Speed', 'delay': 4.0}
                ],
                'camera': {'zoom': 2.0, 'duration': 2.0}
            },

            # Step 19: Delta Trail Detail
            {
                'id': 'trail_detail',
                'duration': 10.0,
                'message': 'Trail colored by speed delta from canonical racing line',
                'cursor_target': ('selected_car', 'offset', -50, 0),
                'cursor_click': False,
                'actions': [],
                'camera': {'zoom': 1.5, 'duration': 3.0}
            },

            # Step 20: Color Customization
            {
                'id': 'color_custom_open',
                'duration': 6.0,
                'message': 'Customize color and size of all visualizations',
                'cursor_target': ('ui_button', 'Visuals - Custom'),
                'cursor_click': True,
                'actions': [
                    {'type': 'ui_click', 'target': 'Visuals - Custom', 'delay': 2.0}
                ],
                'camera': {'zoom': 1.2, 'duration': 1.5}
            },

            # Step 21: Customization Demo (wait for menu)
            {
                'id': 'color_custom_demo',
                'duration': 5.0,
                'message': 'Adjust size and colors to match your preferences',
                'cursor_target': ('center',),
                'cursor_click': False,
                'actions': [
                    {'type': 'close_color_menu', 'delay': 3.0}
                ],
                'camera': None
            },

            # Step 22: Multi-car Comparison
            {
                'id': 'multi_car_compare',
                'duration': 12.0,
                'message': 'Apply trail to multiple cars for driver comparison',
                'cursor_target': ('car', 5),
                'cursor_click': True,
                'actions': [
                    {'type': 'select_car', 'car_index': 5, 'delay': 1.0, 'add_to_selection': True},
                    {'type': 'select_car', 'car_index': 7, 'delay': 3.0, 'add_to_selection': True},
                ],
                'camera': {'zoom': 1.0, 'duration': 3.0}
            },

            # Step 23: Zoom Demonstration
            {
                'id': 'zoom_demo',
                'duration': 8.0,
                'message': 'Zoom with scroll wheel, pan with right-click drag',
                'cursor_target': ('track_pos', 0.5, 0.5),
                'cursor_click': False,
                'actions': [
                    {'type': 'demo_zoom', 'zoom_to': 2.5, 'delay': 2.0, 'duration': 3.0},
                ],
                'camera': None  # Manual zoom via action
            },

            # Step 24: Pan Demonstration
            {
                'id': 'pan_demo',
                'duration': 7.0,
                'message': 'Pan around the track to explore different areas',
                'cursor_target': ('track_pos', 0.6, 0.5),
                'cursor_click': False,
                'actions': [
                    {'type': 'demo_pan', 'pan_x': 0.2, 'pan_y': 0, 'delay': 1.0, 'duration': 4.0}
                ],
                'camera': None  # Manual pan via action
            },

            # Step 25: Reset View
            {
                'id': 'reset_view',
                'duration': 4.0,
                'message': 'Reset view to see the entire track',
                'cursor_target': ('ui_button', 'Reset View'),
                'cursor_click': True,
                'actions': [
                    {'type': 'ui_click', 'target': 'Reset View', 'delay': 2.0}
                ],
                'camera': None
            },

            # Step 26: Racing Line Toggle
            {
                'id': 'racing_line_toggle',
                'duration': 6.0,
                'message': 'Compare against canonical, global, or individual racing lines',
                'cursor_target': ('ui_element', 'global_racing_line_cb'),
                'cursor_click': True,
                'actions': [
                    {'type': 'enable_checkbox', 'target': 'global_racing_line_cb', 'delay': 2.0}
                ],
                'camera': {'zoom': 1.2, 'duration': 2.0}
            },

            # Step 27: Best Lap Comparison
            {
                'id': 'best_lap_compare',
                'duration': 10.0,
                'message': "Compare against driver's own best lap performance",
                'cursor_target': ('ui_element', 'lateral_diff_reference'),
                'cursor_click': True,
                'actions': [
                    {'type': 'set_dropdown', 'target': 'lateral_diff_reference',
                     'value': 'Individual Racing Lines', 'delay': 2.0}
                ],
                'camera': None
            },

            # Step 28: Conclusion
            {
                'id': 'conclusion',
                'duration': 8.0,
                'message': 'Toyota Race Suite: Complete pipeline from raw data to actionable insights',
                'cursor_target': ('center',),
                'cursor_click': False,
                'actions': [],
                'camera': {'zoom': 1.0, 'duration': 3.0}
            },
        ]
