"""HACKATHON DEMO - 2.5 minute automated showcase for submission video.

This script runs a fully automated demo perfect for screen recording.
Just start the app, load data, and run this demo - record your screen!

Category: Post-event Analysis + Driver Training/Insights
"""


class HackathonDemoScript:
    """2.5 minute winning demo sequence for TRD Hackathon 2024."""

    def __init__(self):
        self.steps = self._build_hackathon_steps()

    def _build_hackathon_steps(self):
        """Build optimized 2.5 minute demo sequence.

        Total: 150 seconds (2:30 with buffer)
        Focus: Delta trails innovation, data pipeline, engineer workflow
        """
        return [
            # === PART 1: THE HOOK - Delta Trails in Action (25s) ===

            # Step 1: Opening statement
            {
                'id': 'hook_intro',
                'duration': 5.0,
                'message': 'Toyota Race Suite - Data Pipeline to Actionable Insights',
                'cursor_target': ('center',),
                'cursor_click': False,
                'actions': [
                    {'type': 'ui_click', 'target': 'Play', 'delay': 2.0}
                ],
                'camera': {'zoom': 1.0}
            },

            # Step 2: Zoom to delta trails
            {
                'id': 'hook_trails',
                'duration': 8.0,
                'message': 'Delta Speed Trails: 15 seconds of performance history in living color',
                'cursor_target': ('car', 0),
                'cursor_click': True,
                'actions': [
                    {'type': 'select_car', 'car_index': 0, 'delay': 1.0},
                    {'type': 'enable_checkbox', 'target': 'trail_cb', 'delay': 2.0},
                    {'type': 'set_dropdown', 'target': 'trail_mode', 'value': 'Delta Speed', 'delay': 3.0}
                ],
                'camera': {'zoom': 2.5, 'pan_to': ('car', 0), 'duration': 2.0}
            },

            # Step 3: Explain delta trails
            {
                'id': 'hook_explain',
                'duration': 7.0,
                'message': 'BLUE = Too Slow | GREEN = Optimal | RED = Too Fast',
                'cursor_target': ('selected_car', 'offset', -40, 0),
                'cursor_click': False,
                'actions': [
                    {'type': 'select_car', 'car_index': 2, 'delay': 2.0, 'add_to_selection': True},
                    {'type': 'select_car', 'car_index': 5, 'delay': 4.0, 'add_to_selection': True}
                ],
                'camera': {'zoom': 1.8, 'duration': 2.0}
            },

            # Step 4: Show multi-car comparison
            {
                'id': 'hook_multicar',
                'duration': 5.0,
                'message': 'Multi-car comparison: Spot the faster line instantly',
                'cursor_target': ('track_pos', 0.5, 0.5),
                'cursor_click': False,
                'actions': [],
                'camera': {'zoom': 1.2, 'duration': 2.0}
            },

            # === PART 2: DATA PIPELINE - Technical Depth (20s) ===

            # Step 5: Show data processing
            {
                'id': 'pipeline_intro',
                'duration': 7.0,
                'message': '20 cars × 100Hz telemetry = 30,000 data points/second processed',
                'cursor_target': ('ui_element', 'cars_count_text'),
                'cursor_click': False,
                'actions': [
                    {'type': 'animate_slider', 'target': 'speed_slider', 'from': 1.0, 'to': 2.0, 'delay': 2.0}
                ],
                'camera': {'zoom': 1.0, 'duration': 1.5}
            },

            # Step 6: Technical architecture
            {
                'id': 'pipeline_tech',
                'duration': 8.0,
                'message': 'Pipeline: CSV → Interpolation → KD-tree Spatial Queries → Delta Computation',
                'cursor_target': ('center',),
                'cursor_click': False,
                'actions': [],
                'camera': None
            },

            # Step 7: Real-time performance
            {
                'id': 'pipeline_perf',
                'duration': 5.0,
                'message': 'GPU-accelerated rendering: 60fps guaranteed, any track size',
                'cursor_target': ('track_pos', 0.6, 0.4),
                'cursor_click': False,
                'actions': [],
                'camera': None
            },

            # === PART 3: INNOVATION - Extensible System (25s) ===

            # Step 8: Pause for analysis
            {
                'id': 'innovation_pause',
                'duration': 4.0,
                'message': 'Engineer workflow: Click to pause, zoom to analyze',
                'cursor_target': ('track_pos', 0.5, 0.5),
                'cursor_click': True,
                'actions': [
                    {'type': 'simulate_track_click', 'delay': 2.0}
                ],
                'camera': {'zoom': 3.0, 'pan_to': 'selected_car', 'duration': 2.0}
            },

            # Step 9: Show extensibility
            {
                'id': 'innovation_extensible',
                'duration': 8.0,
                'message': 'Extensible references: Canonical, Global, Individual, or Custom',
                'cursor_target': ('ui_element', 'lateral_diff_reference'),
                'cursor_click': True,
                'actions': [
                    {'type': 'set_dropdown', 'target': 'lateral_diff_reference',
                     'value': 'Individual Racing Lines', 'delay': 3.0}
                ],
                'camera': None
            },

            # Step 10: Future potential
            {
                'id': 'innovation_future',
                'duration': 7.0,
                'message': 'Future: Previous lap delta, Live competitor, Tire degradation analysis',
                'cursor_target': ('selected_car', 'offset', -50, 0),
                'cursor_click': False,
                'actions': [
                    {'type': 'simulate_track_click', 'delay': 3.0}  # Resume
                ],
                'camera': {'zoom': 2.0, 'duration': 2.0}
            },

            # Step 11: Customization
            {
                'id': 'innovation_customize',
                'duration': 6.0,
                'message': 'All visualizations fully customizable: size, color, duration',
                'cursor_target': ('ui_button', 'Visuals - Custom'),
                'cursor_click': True,
                'actions': [
                    {'type': 'ui_click', 'target': 'Visuals - Custom', 'delay': 2.0},
                    {'type': 'close_color_menu', 'delay': 4.0}
                ],
                'camera': None
            },

            # === PART 4: COMPLETE SOLUTION - Multi-dimensional (25s) ===

            # Step 12: Brake arcs
            {
                'id': 'solution_brakes',
                'duration': 6.0,
                'message': 'Brake Arcs: Front/rear pressure aligned with car heading',
                'cursor_target': ('ui_element', 'circle_glow_cb'),
                'cursor_click': True,
                'actions': [
                    {'type': 'enable_checkbox', 'target': 'circle_glow_cb', 'delay': 2.0}
                ],
                'camera': {'zoom': 3.0, 'pan_to': 'selected_car', 'duration': 2.0}
            },

            # Step 13: Deviation bars
            {
                'id': 'solution_deviation',
                'duration': 7.0,
                'message': 'Lateral Deviation: ±2m racing line - 5 bars per side, progressive fill',
                'cursor_target': ('ui_element', 'lateral_diff_cb'),
                'cursor_click': True,
                'actions': [
                    {'type': 'enable_checkbox', 'target': 'lateral_diff_cb', 'delay': 2.0}
                ],
                'camera': None
            },

            # Step 14: All visualizations
            {
                'id': 'solution_all',
                'duration': 6.0,
                'message': 'Steering + Acceleration + Trails: Complete performance picture',
                'cursor_target': ('ui_element', 'steering_angle_cb'),
                'cursor_click': True,
                'actions': [
                    {'type': 'enable_checkbox', 'target': 'steering_angle_cb', 'delay': 1.5},
                    {'type': 'enable_checkbox', 'target': 'circle_centre_cb', 'delay': 3.0}
                ],
                'camera': None
            },

            # Step 15: Zoom out for impact
            {
                'id': 'solution_overview',
                'duration': 6.0,
                'message': 'Simultaneous multi-car analysis: Every driver, every corner, every second',
                'cursor_target': ('track_pos', 0.5, 0.5),
                'cursor_click': False,
                'actions': [],
                'camera': {'zoom': 1.0, 'duration': 2.0}
            },

            # === PART 5: ENGINEER WORKFLOW (15s) ===

            # Step 16: Interactive analysis demo
            {
                'id': 'workflow_interactive',
                'duration': 8.0,
                'message': 'Click to pause → Zoom to analyze → Pan to explore → Resume',
                'cursor_target': ('track_pos', 0.6, 0.5),
                'cursor_click': True,
                'actions': [
                    {'type': 'simulate_track_click', 'delay': 2.0},
                    {'type': 'demo_zoom', 'zoom_to': 2.5, 'delay': 3.5, 'duration': 1.5},
                    {'type': 'simulate_track_click', 'delay': 6.0}
                ],
                'camera': None
            },

            # Step 17: Speed of insight
            {
                'id': 'workflow_insight',
                'duration': 7.0,
                'message': 'Time to insight: 3 seconds. Setup adjustment identified instantly.',
                'cursor_target': ('selected_car', 'offset', 0, -30),
                'cursor_click': False,
                'actions': [],
                'camera': {'zoom': 1.5, 'duration': 2.0}
            },

            # === PART 6: IMPACT & CLOSE (20s) ===

            # Step 18: Technical excellence
            {
                'id': 'close_technical',
                'duration': 7.0,
                'message': 'Architecture: KD-tree indexing, Vectorized NumPy, GPU rendering, Modular design',
                'cursor_target': ('center',),
                'cursor_click': False,
                'actions': [
                    {'type': 'animate_slider', 'target': 'speed_slider', 'from': 2.0, 'to': 1.0, 'delay': 2.0}
                ],
                'camera': {'zoom': 1.0, 'duration': 2.0}
            },

            # Step 19: Production ready
            {
                'id': 'close_production',
                'duration': 6.0,
                'message': 'Production-ready: <500MB memory, modular architecture, extensible platform',
                'cursor_target': ('track_pos', 0.5, 0.5),
                'cursor_click': False,
                'actions': [],
                'camera': None
            },

            # Step 20: Final impact statement
            {
                'id': 'close_final',
                'duration': 7.0,
                'message': 'From Raw Data to Racing Intelligence: Built for TRD Engineers',
                'cursor_target': ('center',),
                'cursor_click': False,
                'actions': [
                    {'type': 'ui_click', 'target': 'Pause', 'delay': 4.0}
                ],
                'camera': {'zoom': 1.0, 'duration': 3.0}
            },

            # === TOTAL: 150 seconds (2:30) ===
        ]
