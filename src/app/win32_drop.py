"""Windows drag-and-drop handler for DearPyGUI windows using message polling."""

import ctypes
from ctypes import wintypes
import win32gui
import win32con
import win32api
import time

# Windows API constants
WM_DROPFILES = 0x0233
GWL_WNDPROC = -4

# Shell32 functions
shell32 = ctypes.windll.shell32
DragQueryFileW = shell32.DragQueryFileW
DragQueryFileW.argtypes = [wintypes.HANDLE, wintypes.UINT, wintypes.LPWSTR, wintypes.UINT]
DragQueryFileW.restype = wintypes.UINT

DragFinish = shell32.DragFinish
DragFinish.argtypes = [wintypes.HANDLE]

DragAcceptFiles = shell32.DragAcceptFiles
DragAcceptFiles.argtypes = [wintypes.HWND, wintypes.BOOL]

# User32 functions for message peeking
user32 = ctypes.windll.user32

class MSG(ctypes.Structure):
    _fields_ = [
        ("hWnd", wintypes.HWND),
        ("message", wintypes.UINT),
        ("wParam", wintypes.WPARAM),
        ("lParam", wintypes.LPARAM),
        ("time", wintypes.DWORD),
        ("pt", wintypes.POINT),
    ]

PeekMessageW = user32.PeekMessageW
PeekMessageW.argtypes = [ctypes.POINTER(MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
PeekMessageW.restype = wintypes.BOOL

PM_REMOVE = 0x0001
PM_NOREMOVE = 0x0000


class Win32DropHandler:
    """Handles Windows drag-and-drop for a DearPyGUI window using message polling."""

    def __init__(self, on_drop_callback):
        """
        Initialize the drop handler.

        Args:
            on_drop_callback: Function to call with list of dropped file paths
        """
        self.on_drop = on_drop_callback
        self.hwnd = None
        self.enabled = False

    def enable(self, window_title="Race Replay - Toyota GR86"):
        """
        Enable drag-and-drop for the specified window.

        Args:
            window_title: Title of the DearPyGUI window
        """
        # Find the window by title
        self.hwnd = win32gui.FindWindow(None, window_title)
        if not self.hwnd:
            print(f"Warning: Could not find window '{window_title}' for drag-drop")
            return False

        # Enable the window to accept dropped files
        DragAcceptFiles(self.hwnd, True)
        self.enabled = True
        print(f"Drag-drop enabled for window: {window_title} (hwnd: {self.hwnd})")
        return True

    def poll(self):
        """
        Poll for drop messages. Call this from the main render loop.

        Returns:
            True if a drop was handled, False otherwise
        """
        if not self.enabled or not self.hwnd:
            return False

        # Check for WM_DROPFILES message
        msg = MSG()
        if PeekMessageW(ctypes.byref(msg), self.hwnd, WM_DROPFILES, WM_DROPFILES, PM_REMOVE):
            self._handle_drop(msg.wParam)
            return True

        return False

    def _handle_drop(self, hdrop):
        """Handle the WM_DROPFILES message."""
        try:
            # Get number of files dropped
            file_count = DragQueryFileW(hdrop, 0xFFFFFFFF, None, 0)
            print(f"Files dropped: {file_count}")

            dropped_files = []
            for i in range(file_count):
                # Get the length of the file path
                length = DragQueryFileW(hdrop, i, None, 0)
                if length:
                    # Create buffer and get file path
                    buffer = ctypes.create_unicode_buffer(length + 1)
                    DragQueryFileW(hdrop, i, buffer, length + 1)
                    dropped_files.append(buffer.value)
                    print(f"  File {i}: {buffer.value}")

            # Finish the drag operation
            DragFinish(hdrop)

            # Call the callback with dropped files
            if dropped_files and self.on_drop:
                self.on_drop(dropped_files)

        except Exception as e:
            print(f"Error handling file drop: {e}")
            import traceback
            traceback.print_exc()

    def disable(self):
        """Disable drag-and-drop."""
        if self.hwnd:
            DragAcceptFiles(self.hwnd, False)
        self.hwnd = None
        self.enabled = False
