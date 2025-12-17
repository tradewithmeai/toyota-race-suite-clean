"""Video export functionality for recording viewport to MP4."""

import os
import time
from datetime import datetime
from threading import Thread
import numpy as np

# Try to import video encoding libraries
try:
    import cv2
    CV2_AVAILABLE = True
except ImportError:
    CV2_AVAILABLE = False

try:
    from moviepy.editor import ImageSequenceClip
    MOVIEPY_AVAILABLE = True
except ImportError:
    MOVIEPY_AVAILABLE = False


class VideoExporter:
    """Handles video recording and export to MP4 files."""

    def __init__(self, screenshot_exporter, output_dir="recordings", fps=60, resolution=(1920, 1080)):
        """Initialize video exporter.

        Args:
            screenshot_exporter: ScreenshotExporter instance for frame capture
            output_dir: Directory to save videos (default: 'recordings/')
            fps: Frames per second (default: 60)
            resolution: Video resolution (default: 1920x1080)
        """
        self.screenshot_exporter = screenshot_exporter
        self.output_dir = output_dir
        self.fps = fps
        self.resolution = resolution

        self.is_recording = False
        self.frames = []  # Buffer for captured frames
        self.start_time = None
        self.frame_count = 0
        self.last_capture_time = 0.0
        self.frame_interval = 1.0 / fps  # Time between frames

        self.output_path = None
        self.writer = None

        self.ensure_output_dir()

    def ensure_output_dir(self):
        """Create output directory if it doesn't exist."""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"Created video output directory: {self.output_dir}")

    def start_recording(self):
        """Start video recording."""
        if self.is_recording:
            print("Recording already in progress")
            return False

        # Generate output filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"video_{timestamp}.mp4"
        self.output_path = os.path.join(self.output_dir, filename)

        self.is_recording = True
        self.frames = []
        self.frame_count = 0
        self.start_time = time.time()
        self.last_capture_time = time.time()

        # Initialize writer if using OpenCV
        if CV2_AVAILABLE:
            fourcc = cv2.VideoWriter_fourcc(*'mp4v')
            self.writer = cv2.VideoWriter(
                self.output_path,
                fourcc,
                self.fps,
                self.resolution
            )
            print(f"Started recording (OpenCV): {self.output_path}")
        else:
            print(f"Started recording (frame buffer): {self.output_path}")

        return True

    def capture_frame(self):
        """Capture a frame if enough time has passed since last frame.

        Returns:
            bool: True if frame was captured, False if skipped
        """
        if not self.is_recording:
            return False

        current_time = time.time()

        # Check if enough time has passed for next frame
        if current_time - self.last_capture_time < self.frame_interval:
            return False

        # Capture screenshot
        frame = self.screenshot_exporter.capture_viewport()
        if frame is None:
            return False

        # Resize to target resolution if needed
        if frame.size != self.resolution:
            from PIL import Image
            frame = frame.resize(self.resolution, Image.LANCZOS)

        if CV2_AVAILABLE and self.writer is not None:
            # Write directly to video file
            import numpy as np
            frame_array = np.array(frame)
            # Convert RGB to BGR for OpenCV
            frame_bgr = cv2.cvtColor(frame_array, cv2.COLOR_RGB2BGR)
            self.writer.write(frame_bgr)
        else:
            # Store in buffer (for moviepy)
            self.frames.append(frame)

        self.frame_count += 1
        self.last_capture_time = current_time

        return True

    def stop_recording(self):
        """Stop recording and save video file.

        Returns:
            str: Path to saved video file, or None if failed
        """
        if not self.is_recording:
            print("No recording in progress")
            return None

        self.is_recording = False
        duration = time.time() - self.start_time

        print(f"Stopping recording: {self.frame_count} frames in {duration:.1f}s")

        if CV2_AVAILABLE and self.writer is not None:
            # Finalize OpenCV writer
            self.writer.release()
            self.writer = None
            print(f"Video saved: {self.output_path}")
            return self.output_path

        elif MOVIEPY_AVAILABLE and len(self.frames) > 0:
            # Save using moviepy in background thread
            print(f"Encoding {len(self.frames)} frames with moviepy...")

            def encode_video():
                try:
                    import numpy as np
                    # Convert PIL images to numpy arrays
                    frame_arrays = [np.array(frame) for frame in self.frames]

                    # Create video clip
                    clip = ImageSequenceClip(frame_arrays, fps=self.fps)

                    # Write video file
                    clip.write_videofile(
                        self.output_path,
                        codec='libx264',
                        audio=False,
                        verbose=False,
                        logger=None
                    )

                    print(f"Video saved: {self.output_path}")
                except Exception as e:
                    print(f"Error encoding video: {e}")
                    import traceback
                    traceback.print_exc()

            # Encode in background thread to avoid blocking UI
            thread = Thread(target=encode_video, daemon=True)
            thread.start()

            return self.output_path

        else:
            print("ERROR: No video encoding library available")
            print("Install opencv-python: pip install opencv-python")
            print("Or install moviepy: pip install moviepy")
            return None

    def get_recording_status(self):
        """Get current recording status.

        Returns:
            dict: Status information
        """
        return {
            'is_recording': self.is_recording,
            'frame_count': self.frame_count,
            'duration': time.time() - self.start_time if self.is_recording else 0.0,
            'fps': self.fps,
            'resolution': self.resolution,
            'output_path': self.output_path
        }

    def record_playthrough(self, world_model, renderer, vehicle_id, lap_number, speed_factor=1.0):
        """Automatically record a full lap playthrough.

        This is useful for creating demo videos without manual recording.

        Args:
            world_model: WorldModel instance
            renderer: Renderer instance
            vehicle_id: Vehicle to follow
            lap_number: Lap number to record
            speed_factor: Playback speed multiplier (1.0 = real-time)

        Returns:
            str: Path to saved video, or None if failed
        """
        if vehicle_id not in world_model.trajectories:
            print(f"Vehicle {vehicle_id} not found")
            return None

        traj = world_model.trajectories[vehicle_id]

        # Find lap start and end indices
        lap_mask = traj[:, 10] == lap_number
        lap_indices = np.where(lap_mask)[0]

        if len(lap_indices) == 0:
            print(f"Lap {lap_number} not found for vehicle {vehicle_id}")
            return None

        start_idx = lap_indices[0]
        end_idx = lap_indices[-1]

        print(f"Recording lap {lap_number} for vehicle {vehicle_id}")
        print(f"Frames: {start_idx} to {end_idx} ({len(lap_indices)} samples)")

        # Start recording
        if not self.start_recording():
            return None

        # Step through lap at target FPS
        dt_ms = (1000.0 / self.fps) * speed_factor  # Milliseconds per frame

        for idx in range(start_idx, end_idx + 1):
            # Set world time
            world_model.current_time_ms = idx * 10  # Each sample is 10ms

            # Render frame
            renderer.render_frame()

            # Capture frame
            self.capture_frame()

            # Small delay to maintain FPS
            time.sleep(1.0 / (self.fps * 2))  # Half-speed to allow rendering

        # Stop recording
        return self.stop_recording()
