"""Background preprocessing runner with progress reporting."""

import os
import sys
import threading
from typing import Callable

# Add src directory to path
src_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, src_dir)

from processing.generate_all_trajectories import generate_all_trajectories


class PreprocessingRunner:
    """Runs preprocessing in background thread with progress callbacks."""

    def __init__(self, on_progress: Callable, on_complete: Callable, on_error: Callable):
        """Initialize runner with callbacks.

        Args:
            on_progress: Called with (message, percent) during processing
            on_complete: Called with (output_dir) when complete
            on_error: Called with (error_message) on failure
        """
        self.on_progress = on_progress
        self.on_complete = on_complete
        self.on_error = on_error
        self._thread = None
        self._cancelled = False

    def start(self, input_file: str, output_dir: str):
        """Start preprocessing in background thread.

        Args:
            input_file: Path to input CSV file
            output_dir: Output directory for processed data
        """
        self._cancelled = False
        self._thread = threading.Thread(
            target=self._run_preprocessing,
            args=(input_file, output_dir),
            daemon=True
        )
        self._thread.start()

    def cancel(self):
        """Request cancellation of preprocessing."""
        self._cancelled = True

    def _run_preprocessing(self, input_file: str, output_dir: str):
        """Run preprocessing (called in background thread)."""
        try:
            # Run the main preprocessing function with progress callback
            result = generate_all_trajectories(
                input_file,
                output_dir,
                progress_callback=self.on_progress
            )

            if self._cancelled:
                return

            if result is None:
                self.on_error("No vehicles processed successfully. Check input file format.")
                return

            self.on_progress("Complete!", 1.0)
            self.on_complete(output_dir)

        except FileNotFoundError as e:
            self.on_error(f"File not found: {e}")
        except PermissionError as e:
            self.on_error(f"Permission denied: {e}")
        except Exception as e:
            self.on_error(f"Processing failed: {str(e)}")


def get_default_output_dir(input_file: str) -> str:
    """Get default output directory based on input file location.

    Places output in data/processed relative to project root,
    or next to input file if not in expected location.
    """
    # Try to find project root (look for src directory)
    current = os.path.dirname(os.path.abspath(input_file))
    for _ in range(5):  # Look up to 5 levels
        if os.path.exists(os.path.join(current, 'src')):
            return os.path.join(current, 'data', 'processed')
        parent = os.path.dirname(current)
        if parent == current:
            break
        current = parent

    # Fallback: place next to input file
    input_dir = os.path.dirname(os.path.abspath(input_file))
    return os.path.join(input_dir, 'processed')
