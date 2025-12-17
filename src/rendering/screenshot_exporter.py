"""Screenshot export functionality for capturing viewport to PNG."""

import os
from datetime import datetime
from PIL import Image
import dearpygui.dearpygui as dpg

# Try to import screen capture libraries
try:
    import pyautogui
    PYAUTOGUI_AVAILABLE = True
except ImportError:
    PYAUTOGUI_AVAILABLE = False

try:
    import win32gui
    import win32ui
    import win32con
    WIN32_AVAILABLE = True
except ImportError:
    WIN32_AVAILABLE = False


class ScreenshotExporter:
    """Handles screenshot capture and export to PNG files."""

    def __init__(self, output_dir="screenshots"):
        """Initialize screenshot exporter.

        Args:
            output_dir: Directory to save screenshots (default: 'screenshots/')
        """
        self.output_dir = output_dir
        self.ensure_output_dir()

    def ensure_output_dir(self):
        """Create output directory if it doesn't exist."""
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            print(f"Created screenshot directory: {self.output_dir}")

    def capture_viewport(self, window_title="Race Replay - Toyota GR86"):
        """Capture current viewport as image array.

        Args:
            window_title: Title of the window to capture

        Returns:
            PIL.Image or None if capture failed
        """
        # Try Win32 API first (more reliable on Windows)
        if WIN32_AVAILABLE:
            try:
                return self._capture_win32(window_title)
            except Exception as e:
                print(f"Win32 capture failed: {e}")

        # Fallback to pyautogui
        if PYAUTOGUI_AVAILABLE:
            try:
                return self._capture_pyautogui(window_title)
            except Exception as e:
                print(f"PyAutoGUI capture failed: {e}")

        print("ERROR: No screen capture library available")
        print("Install pyautogui: pip install pyautogui")
        return None

    def _capture_win32(self, window_title):
        """Capture using Win32 API (Windows only).

        Args:
            window_title: Title of the window to capture

        Returns:
            PIL.Image
        """
        import win32gui
        import win32ui
        import win32con
        from ctypes import windll

        # Find window by title
        hwnd = win32gui.FindWindow(None, window_title)
        if not hwnd:
            # Try partial match
            def enum_callback(hwnd, results):
                if window_title.lower() in win32gui.GetWindowText(hwnd).lower():
                    results.append(hwnd)
            results = []
            win32gui.EnumWindows(enum_callback, results)
            if results:
                hwnd = results[0]
            else:
                raise Exception(f"Window not found: {window_title}")

        # Get window dimensions
        left, top, right, bottom = win32gui.GetWindowRect(hwnd)
        width = right - left
        height = bottom - top

        # Get window device context
        hwndDC = win32gui.GetWindowDC(hwnd)
        mfcDC = win32ui.CreateDCFromHandle(hwndDC)
        saveDC = mfcDC.CreateCompatibleDC()

        # Create bitmap
        saveBitMap = win32ui.CreateBitmap()
        saveBitMap.CreateCompatibleBitmap(mfcDC, width, height)
        saveDC.SelectObject(saveBitMap)

        # Copy window to bitmap
        result = windll.user32.PrintWindow(hwnd, saveDC.GetSafeHdc(), 3)

        # Convert to PIL Image
        bmpinfo = saveBitMap.GetInfo()
        bmpstr = saveBitMap.GetBitmapBits(True)
        img = Image.frombuffer(
            'RGB',
            (bmpinfo['bmWidth'], bmpinfo['bmHeight']),
            bmpstr, 'raw', 'BGRX', 0, 1
        )

        # Clean up
        win32gui.DeleteObject(saveBitMap.GetHandle())
        saveDC.DeleteDC()
        mfcDC.DeleteDC()
        win32gui.ReleaseDC(hwnd, hwndDC)

        return img

    def _capture_pyautogui(self, window_title):
        """Capture using pyautogui (cross-platform).

        Args:
            window_title: Title of the window to capture (ignored for now)

        Returns:
            PIL.Image
        """
        import pyautogui

        # PyAutoGUI captures the entire screen
        # For better targeting, we'd need pygetwindow to find window bounds
        # For now, just capture the whole screen
        screenshot = pyautogui.screenshot()
        return screenshot

    def save_screenshot(self, image=None, filename=None):
        """Save screenshot to file.

        Args:
            image: PIL.Image to save (if None, will capture new screenshot)
            filename: Custom filename (if None, will generate timestamped name)

        Returns:
            str: Path to saved file, or None if failed
        """
        # Capture if no image provided
        if image is None:
            image = self.capture_viewport()
            if image is None:
                return None

        # Generate filename if not provided
        if filename is None:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"screenshot_{timestamp}.png"

        # Ensure .png extension
        if not filename.lower().endswith('.png'):
            filename += '.png'

        # Full path
        filepath = os.path.join(self.output_dir, filename)

        # Save image
        try:
            image.save(filepath, 'PNG')
            print(f"Screenshot saved: {filepath}")
            return filepath
        except Exception as e:
            print(f"Error saving screenshot: {e}")
            return None

    def take_screenshot(self, show_message=True):
        """Convenience method to capture and save screenshot in one call.

        Args:
            show_message: Whether to show success message (requires message_overlay)

        Returns:
            str: Path to saved file, or None if failed
        """
        self.ensure_output_dir()

        image = self.capture_viewport()
        if image is None:
            return None

        filepath = self.save_screenshot(image)

        if filepath and show_message:
            # Try to show message overlay if available
            try:
                from app.message_overlay import show_message
                filename = os.path.basename(filepath)
                show_message(f"Screenshot saved: {filename}", duration=3.0)
            except ImportError:
                pass

        return filepath
