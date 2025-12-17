"""Launch app with HACKATHON DEMO for video recording.

USAGE:
1. Start screen recording (OBS, Windows Game Bar, etc.)
2. Run this script: python run_hackathon_demo.py
3. App loads → Demo starts automatically in 2 seconds
4. Record for 2.5 minutes
5. Stop recording, upload to YouTube

The demo will:
- Show delta trails (your star feature)
- Demonstrate data pipeline (20 cars, 100Hz)
- Prove extensibility (switch references)
- Show all visualizations
- Demonstrate engineer workflow
- Professional finish

Total: 2 minutes 30 seconds
"""

import os
import sys

# Add src to path
src_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'src')
sys.path.insert(0, src_dir)

# Force hackathon demo mode
os.environ['HACKATHON_DEMO'] = '1'

# Launch app
from app.main import main

if __name__ == '__main__':
    print("="*60)
    print("🏁 HACKATHON DEMO MODE - 2.5 Minute Automated Sequence")
    print("="*60)
    print()
    print("📹 START YOUR SCREEN RECORDING NOW!")
    print()
    print("The demo will:")
    print("  ✓ Run automatically for 2.5 minutes")
    print("  ✓ Showcase delta trails (star feature)")
    print("  ✓ Demonstrate data pipeline")
    print("  ✓ Show all visualizations")
    print("  ✓ Prove extensibility")
    print()
    print("After recording:")
    print("  1. Stop recording")
    print("  2. Upload to YouTube (public/unlisted)")
    print("  3. Submit link to hackathon")
    print()
    print("="*60)
    print("Demo starting in 3 seconds...")
    print("="*60)

    import time
    time.sleep(3)

    main()
