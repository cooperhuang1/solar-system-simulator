from __future__ import annotations

import math
import random
import time
import tkinter as tk
from tkinter import font

from .camera import Camera
from .models import CelestialBody, RenderBody, SimulationState, Vector3
from .orbit import OrbitEngine


class SolarSystemRenderer:
    """Canvas renderer with a restrained mission-control visual language."""

    SIDEBAR_WIDTH = 392
    BOTTOM_BAR_HEIGHT = 82

    BG = "#05070B"
    PANEL = "#0B0F16"
    PANEL_2 = "#0F141D"
    BORDER = "#263142"
    GRID = "#111A27"
    TEXT = "#E6EDF7"
    MUTED = "#8793A6"
    FAINT = "#4E5B6F"
    ACCENT = "#77A7FF"
    WARNING = "#F2C166"

    def __init__(self, canvas: tk.Canvas, fonts: dict[str, font.Font]) -> None:
        self.canvas = canvas
        self.fonts = fonts
        self.starfield = self._make_starfield(520)
        self.ui_hitboxes: list[tuple[str, str, tuple[float, float, float, float]]] = []
        self.render_cache: dict[str, RenderBody] = {}

    def draw(
        self,
        bodies: list[CelestialBody],
        body_map: dict[str, CelestialBody],
        state: SimulationState,
        orbit: OrbitEngine,
        camera: Camera,
        mouse: tuple[int, int],
        hover: str | None,
    ) -> None:
        self.canvas.delete("all")
        self.ui_hitboxes.clear()
        self.render_cache.clear()

        width = max(1000, self.canvas.winfo_width())
        height = max(680, self.canvas.winfo_height())
        center = self.center(width, height)
        positions = orbit.positions(bodies, state.sim_days)
        focus_offset = self._focus_offset(state, positions)

        self._draw_background(width, height)
        self._draw_reference_grid(width, height)
        self._draw_orbits(bodies, state, orbit, camera, center, focus_offset)
        if state.show_trails:
            self._draw_trails(bodies, state, orbit, camera, center, focus_offset)

        render_bodies = self._prepare_render_bodies(bodies, positions, camera, center, focus_offset)
        self._draw_bodies(render_bodies, state, hover)
        self._draw_header(state, orbit, width, height)
        self._draw_sidebar(width, height, bodies, body_map, state)
        self._draw_bottom_bar(width, height, state)
        self._draw_hover(mouse, hover, state)

    def viewport(self, width: int, height: int) -> tuple[int, int, int, int]:
        return 0, 0, width - self.SIDEBAR_WIDTH, height - self.BOTTOM_BAR_HEIGHT

    def center(self, width: int, height: int) -> tuple[float, float]:
        x1, y1, x2, y2 = self.viewport(width, height)
        return (x1 + x2) / 2, (y1 + y2) / 2 + 8

    def _make_starfield(self, count: int) -> list[tuple[float, float, float, int]]:
        random.seed(20260515)
        return [
            (
                random.random(),
                random.random(),
                random.choice([0.45, 0.55, 0.7, 0.85]),
                random.randrange(85, 170),
            )
            for _ in range(count)
        ]

    def _focus_offset(self, state: SimulationState, positions: dict[str, Vector3]) -> Vector3:
        if not state.follow_focus or state.focus == "Sun":
            return 0.0, 0.0, 0.0
        return positions.get(state.focus, (0.0, 0.0, 0.0))

    def _draw_background(self, width: int, height: int) -> None:
        self.canvas.create_rectangle(0, 0, width, height, fill=self.BG, outline="")
        vx1, vy1, vx2, vy2 = self.viewport(width, height)
        for xf, yf, size, shade in self.starfield:
            x = vx1 + xf * (vx2 - vx1)
            y = vy1 + yf * (vy2 - vy1)
            color = f"#{shade:02x}{shade:02x}{min(255, shade + 12):02x}"
            self.canvas.create_oval(x, y, x + size, y + size, fill=color, outline="")

    def _draw_reference_grid(self, width: int, height: int) -> None:
        vx1, vy1, vx2, vy2 = self.viewport(width, height)
        step = 96
        for x in range(vx1, vx2, step):
            self.canvas.create_line(x, vy1, x, vy2, fill=self.GRID, width=1)
        for y in range(vy1, vy2, step):
            self.canvas.create_line(vx1, y, vx2, y, fill=self.GRID, width=1)
        self.canvas.create_rectangle(vx1 + 18, vy1 + 18, vx2 - 18, vy2 - 18, outline="#172233", width=1)

    def _draw_orbits(
        self,
        bodies: list[CelestialBody],
        state: SimulationState,
        orbit: OrbitEngine,
        camera: Camera,
        center: tuple[float, float],
        focus_offset: Vector3,
    ) -> None:
        for body in bodies:
            if body.elements is None:
                continue
            coords: list[float] = []
            for world in orbit.orbit_polyline(body):
                sx, sy, _, _ = camera.project(world, center, focus_offset)
                coords.extend((sx, sy))
            if len(coords) < 4:
                continue
            selected = body.name == state.selected
            color = self.ACCENT if selected else "#273348"
            width = 1.4 if selected else 0.8
            self.canvas.create_line(*coords, fill=color, width=width, smooth=True)

    def _draw_trails(
        self,
        bodies: list[CelestialBody],
        state: SimulationState,
        orbit: OrbitEngine,
        camera: Camera,
        center: tuple[float, float],
        focus_offset: Vector3,
    ) -> None:
        for body in bodies:
            if body.elements is None:
                continue
            coords: list[float] = []
            for world in orbit.trail_polyline(body, state.sim_days, samples=36):
                sx, sy, _, _ = camera.project(world, center, focus_offset)
                coords.extend((sx, sy))
            if len(coords) >= 4:
                self.canvas.create_line(*coords, fill=self._mix(body.color, "#05070B", 0.45), width=1.2, smooth=True)

    def _prepare_render_bodies(
        self,
        bodies: list[CelestialBody],
        positions: dict[str, Vector3],
        camera: Camera,
        center: tuple[float, float],
        focus_offset: Vector3,
    ) -> list[RenderBody]:
        rendered: list[RenderBody] = []
        for body in bodies:
            sx, sy, depth, perspective = camera.project(positions[body.name], center, focus_offset)
            radius = max(2.8, min(12.0, body.visual_radius * 0.55 * camera.zoom * perspective))
            if body.name == "Sun":
                radius = max(7.0, min(18.0, body.visual_radius * 0.34 * math.sqrt(camera.zoom) * perspective))
            item = RenderBody(body, positions[body.name], (sx, sy), depth, radius, perspective)
            rendered.append(item)
            self.render_cache[body.name] = item
        return sorted(rendered, key=lambda item: item.depth)

    def _draw_bodies(self, render_bodies: list[RenderBody], state: SimulationState, hover: str | None) -> None:
        for item in render_bodies:
            body = item.body
            x, y = item.screen
            selected = body.name == state.selected
            active = selected or body.name == hover or body.name == state.focus

            if body.name == "Sun":
                self._draw_solar_marker(x, y, item.radius, selected)
            else:
                self._draw_body_marker(body, x, y, item.radius, active)

            if state.follow_focus and body.name == state.focus:
                r = item.radius + 8
                self.canvas.create_oval(x - r, y - r, x + r, y + r, outline=self.ACCENT, width=1)
                self.canvas.create_line(x - r - 6, y, x - r + 2, y, fill=self.ACCENT)
                self.canvas.create_line(x + r - 2, y, x + r + 6, y, fill=self.ACCENT)
                self.canvas.create_line(x, y - r - 6, x, y - r + 2, fill=self.ACCENT)
                self.canvas.create_line(x, y + r - 2, x, y + r + 6, fill=self.ACCENT)

            if state.show_labels:
                self._draw_label(body, x, y, item.radius, selected)

    def _draw_solar_marker(self, x: float, y: float, r: float, selected: bool) -> None:
        halo = r + 8
        self.canvas.create_oval(x - halo, y - halo, x + halo, y + halo, outline="#5A421F", width=1)
        self.canvas.create_oval(x - r, y - r, x + r, y + r, fill="#E8B75B", outline="#F5D28C", width=1)
        if selected:
            self.canvas.create_rectangle(x - r - 5, y - r - 5, x + r + 5, y + r + 5, outline=self.ACCENT, width=1)

    def _draw_body_marker(self, body: CelestialBody, x: float, y: float, r: float, active: bool) -> None:
        self.canvas.create_oval(x - r, y - r, x + r, y + r, fill=body.color, outline="#0A0F18", width=1)
        self.canvas.create_oval(x - r * 0.35, y - r * 0.35, x + r * 0.12, y + r * 0.12, fill=self._mix(body.color, "#FFFFFF", 0.28), outline="")
        if body.name == "Saturn":
            self.canvas.create_oval(x - r * 1.7, y - r * 0.55, x + r * 1.7, y + r * 0.55, outline="#9C8A66", width=1)
        if active:
            outer = r + 5
            self.canvas.create_oval(x - outer, y - outer, x + outer, y + outer, outline=self.ACCENT, width=1)

    def _draw_label(self, body: CelestialBody, x: float, y: float, r: float, selected: bool) -> None:
        text = f"{body.name.upper()}  {body.cn_name}"
        fill = self.TEXT if selected else self.MUTED
        self.canvas.create_text(x + r + 7, y - r - 1, text=text, fill=fill, font=self.fonts["small"], anchor="sw")

    def _draw_header(self, state: SimulationState, orbit: OrbitEngine, width: int, height: int) -> None:
        vx1, vy1, _, _ = self.viewport(width, height)
        self._panel(vx1 + 18, vy1 + 18, vx1 + 560, vy1 + 78)
        self.canvas.create_text(vx1 + 38, vy1 + 32, text="SOLAR SYSTEM SIMULATION", fill=self.TEXT, font=self.fonts["title"], anchor="nw")
        mode = "PAUSED" if state.paused else "RUNNING"
        date_text = orbit.date_from_days(state.sim_days).strftime("%Y-%m-%d UTC")
        compact = "COMPACT SCALE" if state.compact_orbits else "LINEAR AU SCALE"
        self.canvas.create_text(
            vx1 + 38,
            vy1 + 58,
            text=f"{mode}   DATE {date_text}   RATE {state.time_scale:.1f} days/s   {compact}",
            fill=self.MUTED,
            font=self.fonts["small"],
            anchor="nw",
        )

    def _draw_sidebar(
        self,
        width: int,
        height: int,
        bodies: list[CelestialBody],
        body_map: dict[str, CelestialBody],
        state: SimulationState,
    ) -> None:
        side_x = width - self.SIDEBAR_WIDTH
        self.canvas.create_rectangle(side_x, 0, width, height, fill=self.PANEL, outline="")
        self.canvas.create_line(side_x, 0, side_x, height, fill=self.BORDER)

        self.canvas.create_text(side_x + 22, 24, text="TELEMETRY", fill=self.TEXT, font=self.fonts["title"], anchor="nw")
        self.canvas.create_text(side_x + 22, 52, text="Object parameters and navigation", fill=self.MUTED, font=self.fonts["small"], anchor="nw")

        self._draw_body_card(side_x + 18, 86, 356, body_map[state.selected])
        self._draw_object_table(side_x + 18, 456, 356, bodies, state)
        self._draw_shortcuts(side_x + 18, height - 148, 356)

    def _draw_body_card(self, x: float, y: float, width: float, body: CelestialBody) -> None:
        self._panel(x, y, x + width, y + 334)
        self.canvas.create_text(x + 18, y + 16, text=body.name.upper(), fill=self.TEXT, font=self.fonts["title"], anchor="nw")
        self.canvas.create_text(x + 18, y + 43, text=f"{body.cn_name} / {body.kind}", fill=self.MUTED, font=self.fonts["small"], anchor="nw")
        self.canvas.create_oval(x + width - 46, y + 20, x + width - 22, y + 44, fill=body.color, outline=self.BORDER)

        rows = [
            ("RADIUS", f"{body.radius_km:,.0f} km"),
            ("MASS", body.mass),
            ("GRAVITY", body.gravity),
            ("ROTATION", body.rotation),
            ("TEMP", body.temperature),
        ]
        if body.elements:
            rows.extend(
                [
                    ("SEMI-MAJOR", f"{body.elements.semi_major_axis_au:.4f} AU"),
                    ("ECCENTRICITY", f"{body.elements.eccentricity:.4f}"),
                    ("INCLINATION", f"{body.elements.inclination_deg:.3f} deg"),
                    ("PERIOD", f"{body.elements.period_days:,.1f} days"),
                ]
            )

        row_y = y + 82
        for label, value in rows:
            self.canvas.create_text(x + 18, row_y, text=label, fill=self.FAINT, font=self.fonts["small"], anchor="nw")
            self.canvas.create_text(x + 145, row_y, text=value, fill=self.TEXT, font=self.fonts["small"], anchor="nw")
            row_y += 23

        self.canvas.create_line(x + 18, y + 282, x + width - 18, y + 282, fill=self.BORDER)
        self.canvas.create_text(x + 18, y + 298, text=body.summary, fill=self.MUTED, font=self.fonts["small"], width=width - 36, anchor="nw")

    def _draw_object_table(self, x: float, y: float, width: float, bodies: list[CelestialBody], state: SimulationState) -> None:
        self.canvas.create_text(x, y - 24, text="OBJECT CATALOG", fill=self.TEXT, font=self.fonts["subtitle"], anchor="nw")
        row_h = 28
        headers = [("ID", 12), ("NAME", 54), ("TYPE", 166), ("a(AU)", 270)]
        self._rect(x, y, x + width, y + row_h, self.PANEL_2, self.BORDER)
        for text, offset in headers:
            self.canvas.create_text(x + offset, y + 8, text=text, fill=self.FAINT, font=self.fonts["small"], anchor="nw")

        for idx, body in enumerate(bodies):
            by = y + row_h * (idx + 1)
            selected = body.name == state.selected
            fill = "#172033" if selected else self.PANEL
            self._rect(x, by, x + width, by + row_h, fill, "#172233")
            self.canvas.create_text(x + 12, by + 8, text=f"{idx:02d}", fill=self.FAINT, font=self.fonts["small"], anchor="nw")
            self.canvas.create_oval(x + 38, by + 10, x + 48, by + 20, fill=body.color, outline="")
            self.canvas.create_text(x + 54, by + 8, text=body.name, fill=self.TEXT if selected else self.MUTED, font=self.fonts["small"], anchor="nw")
            self.canvas.create_text(x + 166, by + 8, text=body.kind, fill=self.MUTED, font=self.fonts["small"], anchor="nw")
            semi_major = "-" if body.elements is None else f"{body.elements.semi_major_axis_au:.2f}"
            self.canvas.create_text(x + 270, by + 8, text=semi_major, fill=self.MUTED, font=self.fonts["small"], anchor="nw")
            self.ui_hitboxes.append(("select", body.name, (x, by, x + width, by + row_h)))

    def _draw_shortcuts(self, x: float, y: float, width: float) -> None:
        self._panel(x, y, x + width, y + 118)
        self.canvas.create_text(x + 16, y + 14, text="CONTROLS", fill=self.TEXT, font=self.fonts["subtitle"], anchor="nw")
        lines = [
            "Drag rotate    Wheel zoom    Click select",
            "Space pause    +/- time rate    F follow",
            "L labels       T trails       R reset",
            "Arrow keys select object       1-8 planets",
        ]
        for index, line in enumerate(lines):
            self.canvas.create_text(x + 16, y + 42 + index * 17, text=line, fill=self.MUTED, font=self.fonts["small"], anchor="nw")

    def _draw_bottom_bar(self, width: int, height: int, state: SimulationState) -> None:
        bar_y = height - self.BOTTOM_BAR_HEIGHT
        right = width - self.SIDEBAR_WIDTH
        self.canvas.create_rectangle(0, bar_y, right, height, fill="#06090E", outline="")
        self.canvas.create_line(0, bar_y, right, bar_y, fill=self.BORDER)

        buttons = [
            ("pause", "PAUSE" if not state.paused else "RUN"),
            ("slower", "RATE -"),
            ("faster", "RATE +"),
            ("follow", "FOLLOW ON" if state.follow_focus else "FOLLOW OFF"),
            ("labels", "LABELS ON" if state.show_labels else "LABELS OFF"),
            ("trails", "TRAILS ON" if state.show_trails else "TRAILS OFF"),
            ("scale", "COMPACT" if state.compact_orbits else "LINEAR"),
            ("reset", "RESET VIEW"),
        ]
        x = 24
        for action, label in buttons:
            button_width = max(76, len(label) * 8 + 24)
            if x + button_width > right - 22:
                break
            self._button(action, label, x, bar_y + 24, button_width)
            x += button_width + 10

    def _button(self, action: str, label: str, x: float, y: float, width: float) -> None:
        self._rect(x, y, x + width, y + 34, self.PANEL_2, self.BORDER)
        self.canvas.create_text(x + width / 2, y + 10, text=label, fill=self.TEXT, font=self.fonts["button"], anchor="n")
        self.ui_hitboxes.append((action, "", (x, y, x + width, y + 34)))

    def _draw_hover(self, mouse: tuple[int, int], hover: str | None, state: SimulationState) -> None:
        if not hover or hover == state.selected:
            return
        item = self.render_cache.get(hover)
        if not item:
            return
        x, y = mouse
        text = f"{item.body.name}  {item.body.cn_name}"
        width = max(130, len(text) * 7)
        self._rect(x + 14, y + 16, x + 14 + width, y + 44, self.PANEL_2, self.BORDER)
        self.canvas.create_text(x + 24, y + 24, text=text, fill=self.TEXT, font=self.fonts["small"], anchor="nw")

    def _panel(self, x1: float, y1: float, x2: float, y2: float) -> None:
        self._rect(x1, y1, x2, y2, self.PANEL, self.BORDER)

    def _rect(self, x1: float, y1: float, x2: float, y2: float, fill: str, outline: str) -> None:
        self.canvas.create_rectangle(x1, y1, x2, y2, fill=fill, outline=outline, width=1)

    def _mix(self, color_a: str, color_b: str, amount_b: float) -> str:
        a = self._hex_to_rgb(color_a)
        b = self._hex_to_rgb(color_b)
        rgb = [int(a[i] * (1 - amount_b) + b[i] * amount_b) for i in range(3)]
        return f"#{rgb[0]:02x}{rgb[1]:02x}{rgb[2]:02x}"

    def _hex_to_rgb(self, color: str) -> tuple[int, int, int]:
        value = color.lstrip("#")
        return int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16)
