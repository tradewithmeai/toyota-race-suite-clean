"""Test script for message overlay system.

This script demonstrates the three required tests:
1. Basic display - single message
2. Message queueing - multiple messages
3. During simulation - no performance impact

To use this script, start the racing sim application and then run
these commands in a Python console or add them to the controls.
"""

from app.message_overlay import show_message


def test_basic_display():
    """Test 1: Basic Display - show a single message for 2 seconds."""
    print("Test 1: Basic Display")
    show_message("Hello World", duration=2)
    print("Expected: Message appears bottom-centre, fades out after 2 seconds")


def test_queueing():
    """Test 2: Queueing - show multiple messages in sequence."""
    print("\nTest 2: Message Queueing")
    show_message("One", duration=1)
    show_message("Two", duration=1)
    show_message("Three", duration=1)
    print("Expected: 'One' appears, then 'Two', then 'Three' - no overlap")


def test_during_simulation():
    """Test 3: During Simulation - show message while replay is running."""
    print("\nTest 3: During Simulation")
    show_message("Car Selected")
    print("Expected: No FPS drop, simulation continues smoothly")


def run_all_tests():
    """Run all three tests sequentially."""
    print("=== Message Overlay Test Suite ===\n")

    # Test 1
    test_basic_display()
    input("\nPress Enter to run Test 2...")

    # Test 2
    test_queueing()
    input("\nPress Enter to run Test 3...")

    # Test 3
    test_during_simulation()

    print("\n=== All tests completed ===")
    print("Check the application window to verify results.")


if __name__ == '__main__':
    print("This test script requires the racing sim to be running.")
    print("Import this module and call the test functions, or integrate")
    print("the show_message() calls into your application controls.")
    print("\nExample usage:")
    print("  from app.message_overlay import show_message")
    print("  show_message('Test Message', duration=3)")
