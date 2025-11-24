"""Smoke tests to verify basic functionality."""

import os
import sys

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))


def test_imports():
    """Test that all modules can be imported."""
    # Skip GUI imports as they require dearpygui
    from processing import load_raw_data
    from processing import time_alignment
    from processing import interpolate_trajectories
    from processing import generate_racing_line
    from processing import generate_all_trajectories
    print("Processing imports: OK")


def test_utils():
    """Test utility functions."""
    from utils.logging_utils import get_logger
    logger = get_logger(__name__)
    logger.info("Test log message")
    print("Utils: OK")


def test_sample_data():
    """Test that sample data exists."""
    sample_dir = os.path.join(os.path.dirname(__file__), '..', 'data', 'sample')
    assert os.path.exists(os.path.join(sample_dir, 'metadata.json')), "metadata.json missing"
    assert os.path.exists(os.path.join(sample_dir, 'racing_line.npy')), "racing_line.npy missing"
    print("Sample data: OK")


if __name__ == '__main__':
    test_imports()
    test_utils()
    test_sample_data()
    print("\nAll smoke tests passed!")
