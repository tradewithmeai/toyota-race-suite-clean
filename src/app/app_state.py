"""Application state manager for Race Replay."""

from enum import Enum
from typing import Callable, Optional


class AppState(Enum):
    """Application states."""
    WAITING_FOR_FILE = "waiting_for_file"
    PROCESSING = "processing"
    READY = "ready"
    ERROR = "error"


class StateManager:
    """Manages application state transitions."""

    def __init__(self):
        self.state = AppState.WAITING_FOR_FILE
        self.input_file_path: Optional[str] = None
        self.output_dir: Optional[str] = None
        self.error_message: Optional[str] = None
        self.progress_message: str = ""
        self.progress_percent: float = 0.0

        # Callbacks for state changes
        self._on_state_change: Optional[Callable] = None

    def set_state_change_callback(self, callback: Callable):
        """Set callback to be called when state changes."""
        self._on_state_change = callback

    def transition_to(self, new_state: AppState):
        """Transition to a new state."""
        old_state = self.state
        self.state = new_state

        if self._on_state_change:
            self._on_state_change(old_state, new_state)

    def set_input_file(self, file_path: str):
        """Set the input file and transition to processing."""
        self.input_file_path = file_path
        self.error_message = None
        self.transition_to(AppState.PROCESSING)

    def set_processed_dir(self, dir_path: str):
        """Set the processed data directory and skip to ready state."""
        self.output_dir = dir_path
        self.input_file_path = None  # No raw file needed
        self.error_message = None
        self.transition_to(AppState.READY)

    def set_processing_progress(self, message: str, percent: float):
        """Update processing progress."""
        self.progress_message = message
        self.progress_percent = percent

    def set_ready(self, output_dir: str):
        """Mark processing as complete and transition to ready."""
        self.output_dir = output_dir
        self.transition_to(AppState.READY)

    def set_error(self, message: str):
        """Set error state with message."""
        self.error_message = message
        self.transition_to(AppState.ERROR)

    def reset(self):
        """Reset to waiting for file state."""
        self.input_file_path = None
        self.output_dir = None
        self.error_message = None
        self.progress_message = ""
        self.progress_percent = 0.0
        self.transition_to(AppState.WAITING_FOR_FILE)
