"""Message overlay system for displaying subtitle-style messages in the racing sim."""

import time
import dearpygui.dearpygui as dpg


# Module-level state
message_queue = []
active_message = None
active_until = 0
canvas_tag = None


def init_message_overlay(canvas: str):
    """Initialize the message overlay system with a canvas tag.

    Args:
        canvas: The DearPyGUI canvas tag to draw messages on
    """
    global canvas_tag
    canvas_tag = canvas


def show_message(text: str, duration: float = 3.0):
    """Queue a message for display.

    Args:
        text: The message text to display
        duration: How long to show the message in seconds (default 3.0)
    """
    message_queue.append({
        'text': text,
        'duration': duration
    })


def _activate_next_message():
    """Activate the next message from the queue."""
    global active_message, active_until

    if message_queue:
        msg = message_queue.pop(0)
        active_message = msg
        active_until = time.time() + msg['duration']


def render_overlay():
    """Render the active message with fade-out effect.

    Should be called once per frame in the main render loop.
    """
    global active_message, active_until

    if canvas_tag is None:
        return

    # Clean up old message tags
    for tag in ['message_bg', 'message_text', 'message_shadow']:
        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)

    # Check if we need to activate next message
    if active_message is None and message_queue:
        _activate_next_message()

    # Check if active message expired
    if active_message is not None:
        current_time = time.time()

        if current_time >= active_until:
            # Message expired, deactivate it
            active_message = None
            # Try to activate next message
            if message_queue:
                _activate_next_message()
            return

        # Calculate fade-out alpha
        time_remaining = active_until - current_time
        fade_duration = 0.5  # Fade out over last 0.5 seconds

        if time_remaining < fade_duration:
            # Fade out
            alpha = int(255 * (time_remaining / fade_duration))
        else:
            # Full opacity
            alpha = 255

        # Get viewport dimensions for centering
        try:
            viewport_width = dpg.get_viewport_width()
            viewport_height = dpg.get_viewport_height()
        except:
            # Fallback if viewport not available
            viewport_width = 1280
            viewport_height = 720

        # Calculate text position (bottom-center at 8% from bottom)
        text = active_message['text']

        # Font size based on viewport (32-48px range)
        font_size = max(32, min(48, int(viewport_height * 0.05)))

        # Rough text width estimation (will center based on this)
        char_width = font_size * 0.6  # Approximate character width
        text_width = len(text) * char_width
        text_height = font_size * 1.2

        # Position at bottom-center (8% from bottom)
        center_x = viewport_width / 2
        bottom_offset = viewport_height * 0.08
        text_y = viewport_height - bottom_offset - text_height
        text_x = center_x - (text_width / 2)

        # Background padding
        padding_x = 20
        padding_y = 10

        # Draw semi-transparent dark background
        bg_x1 = text_x - padding_x
        bg_y1 = text_y - padding_y
        bg_x2 = text_x + text_width + padding_x
        bg_y2 = text_y + text_height + padding_y

        bg_alpha = int(alpha * 0.7)  # Background slightly more transparent
        dpg.draw_rectangle(
            [bg_x1, bg_y1],
            [bg_x2, bg_y2],
            fill=(0, 0, 0, bg_alpha),
            parent=canvas_tag,
            tag='message_bg'
        )

        # Draw shadow (offset by 2px for depth)
        shadow_offset = 2
        dpg.draw_text(
            [text_x + shadow_offset, text_y + shadow_offset],
            text,
            color=(0, 0, 0, alpha),
            size=font_size,
            parent=canvas_tag,
            tag='message_shadow'
        )

        # Draw main text (white)
        dpg.draw_text(
            [text_x, text_y],
            text,
            color=(255, 255, 255, alpha),
            size=font_size,
            parent=canvas_tag,
            tag='message_text'
        )


def clear_all_messages():
    """Clear all queued and active messages."""
    global active_message, message_queue
    message_queue.clear()
    active_message = None

    # Clean up rendered elements
    for tag in ['message_bg', 'message_text', 'message_shadow']:
        if dpg.does_item_exist(tag):
            dpg.delete_item(tag)
