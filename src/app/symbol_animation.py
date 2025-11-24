"""Falling keyboard symbols animation for loading screen."""

import random
import math
import os
from dataclasses import dataclass, field
from enum import Enum
from typing import List, Optional
import dearpygui.dearpygui as dpg

try:
    from PIL import Image
    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class AnimationPhase(Enum):
    """Animation phase states."""
    FILL_1 = "fill_1"
    DRAIN_1 = "drain_1"
    FILL_2 = "fill_2"
    DRAIN_2 = "drain_2"
    FINAL_FILL = "final_fill"
    REVEAL = "reveal"
    COMPLETE = "complete"


class AnimationMode(Enum):
    """Animation mode options."""
    FILL_DRAIN_CYCLES = "fill_drain"  # Original fill/drain cycling
    LOGO_CYCLE = "logo_cycle"  # Just the Toyota logo forming/dispersing


@dataclass
class Symbol:
    """A single falling keyboard symbol."""
    char: str
    x: float
    y: float
    vx: float = 0.0
    vy: float = 0.0
    rotation: float = 0.0
    rotation_speed: float = 0.0
    color: tuple = (212, 165, 116, 255)  # Golden/amber
    size: int = 12
    tag: str = ""
    # Final position for portrait reveal
    final_x: float = 0.0
    final_y: float = 0.0
    is_settled: bool = False
    settle_y: float = 0.0  # Y position when settled in pile


class SymbolAnimator:
    """Manages the falling symbols animation."""

    # Characters to use
    CHARS = list("0123456789+-*/=?!()@#$%&")

    def __init__(self, canvas_tag: str, width: int = 420, height: int = 300,
                 mode: AnimationMode = AnimationMode.LOGO_CYCLE):
        self.canvas_tag = canvas_tag
        self.width = width
        self.height = height
        self.symbols: List[Symbol] = []
        self.phase = AnimationPhase.FILL_1
        self.progress = 0.0
        self.time = 0.0
        self.symbol_counter = 0
        self.mode = mode

        # Physics parameters
        self.gravity = 400.0  # pixels per second^2
        self.floor_y = height - 10
        self.spawn_rate = 50  # symbols per second
        self.max_symbols = 800

        # Pile tracking
        self.pile_heights = {}  # x_bucket -> current pile height
        self.bucket_width = 8

        # Portrait data
        self.portrait_positions: List[tuple] = []  # (x, y, char)
        self.portrait_loaded = False

        # Animation timing (progress ranges for each phase) - for FILL_DRAIN mode
        self.phase_ranges = {
            AnimationPhase.FILL_1: (0.0, 0.20),
            AnimationPhase.DRAIN_1: (0.20, 0.35),
            AnimationPhase.FILL_2: (0.35, 0.60),
            AnimationPhase.DRAIN_2: (0.60, 0.75),
            AnimationPhase.FINAL_FILL: (0.75, 0.95),
            AnimationPhase.REVEAL: (0.95, 1.0),
            AnimationPhase.COMPLETE: (1.0, 1.0),
        }

        # Logo cycle parameters
        self.cycle_duration = 4.0  # seconds per cycle
        self.cycle_time = 0.0
        self.is_forming = True  # True = forming logo, False = dispersing
        self.symbols_initialized = False

        # Colors
        self.base_color = (212, 165, 116)  # Golden/amber
        self.dark_color = (80, 60, 40)  # Darker for background symbols

    def load_portrait(self, image_path: str):
        """Load the ASCII portrait image and create symbol positions."""
        if not HAS_PIL:
            print("PIL not available, using random portrait positions")
            self._create_random_portrait()
            return

        if not os.path.exists(image_path):
            print(f"Portrait image not found: {image_path}")
            self._create_random_portrait()
            return

        try:
            img = Image.open(image_path)
            # Resize to fit our canvas
            aspect = img.width / img.height
            if aspect > self.width / self.height:
                new_width = self.width
                new_height = int(self.width / aspect)
            else:
                new_height = self.height
                new_width = int(self.height * aspect)

            img = img.resize((new_width, new_height), Image.Resampling.LANCZOS)
            img = img.convert('L')  # Grayscale

            # Sample pixels to create symbol positions
            # Higher density where image is brighter
            self.portrait_positions = []

            # Grid sampling
            step_x = max(1, new_width // 60)
            step_y = max(1, new_height // 80)

            offset_x = (self.width - new_width) // 2
            offset_y = (self.height - new_height) // 2

            for y in range(0, new_height, step_y):
                for x in range(0, new_width, step_x):
                    brightness = img.getpixel((x, y))
                    # Only place symbols where there's content (brightness > threshold)
                    if brightness > 30:
                        char = random.choice(self.CHARS)
                        px = offset_x + x
                        py = offset_y + y
                        # Color based on brightness
                        intensity = brightness / 255.0
                        self.portrait_positions.append((px, py, char, intensity))

            self.portrait_loaded = True
            self.max_symbols = len(self.portrait_positions)
            print(f"Loaded portrait with {len(self.portrait_positions)} symbol positions")

        except Exception as e:
            print(f"Error loading portrait: {e}")
            self._create_random_portrait()

    def _create_random_portrait(self):
        """Create random portrait positions as fallback."""
        self.portrait_positions = []
        for _ in range(600):
            x = random.uniform(50, self.width - 50)
            y = random.uniform(50, self.height - 50)
            char = random.choice(self.CHARS)
            intensity = random.uniform(0.3, 1.0)
            self.portrait_positions.append((x, y, char, intensity))
        self.portrait_loaded = True
        self.max_symbols = len(self.portrait_positions)

    def set_progress(self, progress: float):
        """Update animation based on progress (0.0 to 1.0)."""
        self.progress = max(0.0, min(1.0, progress))

        # Determine current phase based on progress
        for phase, (start, end) in self.phase_ranges.items():
            if start <= self.progress < end:
                if self.phase != phase:
                    self._on_phase_change(phase)
                self.phase = phase
                break
        else:
            if self.progress >= 1.0:
                self.phase = AnimationPhase.COMPLETE

    def _on_phase_change(self, new_phase: AnimationPhase):
        """Handle phase transitions."""
        if new_phase in [AnimationPhase.DRAIN_1, AnimationPhase.DRAIN_2]:
            # Start draining - give symbols horizontal velocity
            for symbol in self.symbols:
                if symbol.is_settled:
                    # Push symbols outward
                    if symbol.x < self.width / 2:
                        symbol.vx = -random.uniform(100, 300)
                    else:
                        symbol.vx = random.uniform(100, 300)
                    symbol.vy = -random.uniform(50, 150)
                    symbol.is_settled = False
            # Reset pile heights
            self.pile_heights = {}

        elif new_phase == AnimationPhase.REVEAL:
            # Assign final positions to symbols
            if self.portrait_positions:
                for i, symbol in enumerate(self.symbols):
                    if i < len(self.portrait_positions):
                        px, py, char, intensity = self.portrait_positions[i]
                        symbol.final_x = px
                        symbol.final_y = py
                        symbol.char = char
                        # Color based on intensity
                        r = int(self.base_color[0] * intensity)
                        g = int(self.base_color[1] * intensity)
                        b = int(self.base_color[2] * intensity)
                        symbol.color = (r, g, b, 255)

    def update(self, dt: float):
        """Update animation state."""
        self.time += dt

        if self.mode == AnimationMode.LOGO_CYCLE:
            self._update_logo_cycle(dt)
            return

        # FILL_DRAIN_CYCLES mode (original behavior)
        if self.phase == AnimationPhase.COMPLETE:
            return

        # Spawn new symbols during fill phases
        if self.phase in [AnimationPhase.FILL_1, AnimationPhase.FILL_2, AnimationPhase.FINAL_FILL]:
            self._spawn_symbols(dt)

        # Update symbol physics
        if self.phase == AnimationPhase.REVEAL:
            self._update_reveal(dt)
        else:
            self._update_physics(dt)

        # Remove symbols that have left the screen (during drain)
        if self.phase in [AnimationPhase.DRAIN_1, AnimationPhase.DRAIN_2]:
            self.symbols = [s for s in self.symbols
                          if -50 < s.x < self.width + 50 and s.y < self.height + 50]

    def _update_logo_cycle(self, dt: float):
        """Update the logo cycle animation (form/disperse continuously)."""
        # Initialize symbols if needed
        if not self.symbols_initialized and self.portrait_positions:
            self._initialize_logo_symbols()
            self.symbols_initialized = True

        if not self.symbols:
            return

        self.cycle_time += dt

        # Check for cycle completion
        if self.cycle_time >= self.cycle_duration:
            self.cycle_time = 0.0
            self.is_forming = not self.is_forming

        # Calculate animation progress within cycle (0 to 1)
        t = self.cycle_time / self.cycle_duration

        # Ease function (smooth step)
        t_smooth = t * t * (3 - 2 * t)

        if self.is_forming:
            # Symbols converge to logo positions
            self._animate_to_logo(t_smooth, dt)
        else:
            # Symbols disperse from logo
            self._animate_from_logo(t_smooth, dt)

    def _initialize_logo_symbols(self):
        """Create all symbols at scattered positions, ready to form logo."""
        self.symbols = []

        for i, (px, py, char, intensity) in enumerate(self.portrait_positions):
            # Start at random scattered positions
            start_x = random.uniform(0, self.width)
            start_y = random.uniform(0, self.height)

            # Color based on intensity
            r = int(self.base_color[0] * intensity)
            g = int(self.base_color[1] * intensity)
            b = int(self.base_color[2] * intensity)

            symbol = Symbol(
                char=char,
                x=start_x,
                y=start_y,
                vx=0,
                vy=0,
                rotation=random.uniform(0, 360),
                # DEBUG: Use BLACK on WHITE background to ensure visibility
                color=(0, 0, 0, 255),
                size=random.randint(12, 16),
                tag=f"sym_{self.symbol_counter}",
                final_x=px,
                final_y=py
            )
            self.symbol_counter += 1
            self.symbols.append(symbol)

    def _animate_to_logo(self, t: float, dt: float):
        """Animate symbols converging to their logo positions."""
        for symbol in self.symbols:
            # Interpolate from current to final position
            target_x = symbol.final_x
            target_y = symbol.final_y

            # Smooth interpolation
            symbol.x = symbol.x + (target_x - symbol.x) * t * 3 * dt
            symbol.y = symbol.y + (target_y - symbol.y) * t * 3 * dt

            # Reduce scatter offset as we approach target
            if t > 0.7:
                # Snap closer when nearly formed
                lerp = (t - 0.7) / 0.3
                symbol.x = symbol.x + (target_x - symbol.x) * lerp * 0.3
                symbol.y = symbol.y + (target_y - symbol.y) * lerp * 0.3

    def _animate_from_logo(self, t: float, dt: float):
        """Animate symbols dispersing from their logo positions."""
        for symbol in self.symbols:
            # Move away from final position
            dx = symbol.x - symbol.final_x
            dy = symbol.y - symbol.final_y

            # If too close to final, give initial push
            dist = math.sqrt(dx*dx + dy*dy)
            if dist < 5:
                angle = random.uniform(0, 2 * math.pi)
                dx = math.cos(angle) * 10
                dy = math.sin(angle) * 10

            # Accelerate outward
            speed = 50 + 150 * t
            if dist > 0:
                symbol.x += (dx / dist) * speed * dt
                symbol.y += (dy / dist) * speed * dt

            # Wrap around screen edges
            if symbol.x < -20:
                symbol.x = self.width + 20
            elif symbol.x > self.width + 20:
                symbol.x = -20
            if symbol.y < -20:
                symbol.y = self.height + 20
            elif symbol.y > self.height + 20:
                symbol.y = -20

    def complete_animation(self):
        """Ensure logo is fully formed (call before screen transition)."""
        if self.mode == AnimationMode.LOGO_CYCLE and self.symbols:
            # Snap all symbols to final positions
            for symbol in self.symbols:
                symbol.x = symbol.final_x
                symbol.y = symbol.final_y
            self.is_forming = True
            self.cycle_time = self.cycle_duration  # At end of forming cycle

    def _spawn_symbols(self, dt: float):
        """Spawn new symbols from the edges."""
        if len(self.symbols) >= self.max_symbols:
            return

        # Determine how many to spawn this frame
        num_to_spawn = int(self.spawn_rate * dt)
        if random.random() < (self.spawn_rate * dt) % 1:
            num_to_spawn += 1

        for _ in range(num_to_spawn):
            if len(self.symbols) >= self.max_symbols:
                break

            # Spawn from left or right edge
            from_left = random.random() < 0.5

            if from_left:
                x = -10
                vx = random.uniform(50, 200)
            else:
                x = self.width + 10
                vx = -random.uniform(50, 200)

            y = random.uniform(-50, self.height * 0.3)
            vy = random.uniform(0, 100)

            symbol = Symbol(
                char=random.choice(self.CHARS),
                x=x,
                y=y,
                vx=vx,
                vy=vy,
                rotation=random.uniform(0, 360),
                rotation_speed=random.uniform(-180, 180),
                color=self.base_color + (255,),
                size=random.randint(10, 14),
                tag=f"sym_{self.symbol_counter}"
            )
            self.symbol_counter += 1
            self.symbols.append(symbol)

    def _update_physics(self, dt: float):
        """Update symbol positions with physics."""
        for symbol in self.symbols:
            if symbol.is_settled:
                continue

            # Apply gravity
            symbol.vy += self.gravity * dt

            # Update position
            symbol.x += symbol.vx * dt
            symbol.y += symbol.vy * dt

            # Update rotation
            symbol.rotation += symbol.rotation_speed * dt

            # Check floor/pile collision
            bucket = int(symbol.x / self.bucket_width)
            pile_height = self.pile_heights.get(bucket, 0)
            floor = self.floor_y - pile_height

            if symbol.y >= floor and symbol.vy > 0:
                # Symbol has landed
                symbol.y = floor
                symbol.vy = 0
                symbol.vx *= 0.3  # Friction
                symbol.rotation_speed *= 0.5

                # Settle if slow enough
                if abs(symbol.vx) < 10:
                    symbol.is_settled = True
                    symbol.vx = 0
                    symbol.settle_y = symbol.y
                    # Update pile height
                    self.pile_heights[bucket] = pile_height + symbol.size * 0.8

            # Bounce off walls
            if symbol.x < 0:
                symbol.x = 0
                symbol.vx = abs(symbol.vx) * 0.5
            elif symbol.x > self.width:
                symbol.x = self.width
                symbol.vx = -abs(symbol.vx) * 0.5

    def _update_reveal(self, dt: float):
        """Smoothly move symbols to their final portrait positions."""
        # Calculate interpolation factor based on progress within reveal phase
        reveal_start = self.phase_ranges[AnimationPhase.REVEAL][0]
        reveal_end = self.phase_ranges[AnimationPhase.REVEAL][1]
        t = (self.progress - reveal_start) / (reveal_end - reveal_start)
        t = max(0.0, min(1.0, t))

        # Ease function (smooth step)
        t = t * t * (3 - 2 * t)

        for symbol in self.symbols:
            # Interpolate to final position
            symbol.x = symbol.x + (symbol.final_x - symbol.x) * t * dt * 5
            symbol.y = symbol.y + (symbol.final_y - symbol.y) * t * dt * 5

            # Reduce rotation
            symbol.rotation *= (1 - t * dt * 3)

    def draw(self):
        """Draw all symbols to the canvas."""
        if not dpg.does_item_exist(self.canvas_tag):
            return

        if not self.symbols:
            return

        # Clear old symbol drawings (but not the background)
        for symbol in self.symbols:
            if symbol.tag and dpg.does_item_exist(symbol.tag):
                dpg.delete_item(symbol.tag)

        # Draw each symbol
        drawn_count = 0
        for symbol in self.symbols:
            if symbol.tag:
                tag = symbol.tag
            else:
                tag = f"sym_{id(symbol)}"
                symbol.tag = tag

            # Skip if out of bounds
            if not (-20 < symbol.x < self.width + 20 and -20 < symbol.y < self.height + 20):
                continue

            drawn_count += 1

            try:
                dpg.draw_text(
                    pos=(symbol.x, symbol.y),
                    text=symbol.char,
                    color=symbol.color,
                    size=symbol.size,
                    parent=self.canvas_tag,
                    tag=tag
                )
            except Exception:
                pass  # Ignore drawing errors

    def clear(self):
        """Clear all symbols."""
        for symbol in self.symbols:
            if symbol.tag and dpg.does_item_exist(symbol.tag):
                dpg.delete_item(symbol.tag)
        self.symbols = []
        self.pile_heights = {}
        self.symbol_counter = 0

    def reset(self):
        """Reset animation to initial state."""
        self.clear()
        self.phase = AnimationPhase.FILL_1
        self.progress = 0.0
        self.time = 0.0
