from __future__ import annotations

import math
import time
import tkinter as tk
from datetime import datetime, timezone
from tkinter import font

from .camera import Camera
from .catalog import load_catalog
from .models import CelestialBody, J2000, SimulationState
from .orbit import OrbitEngine
from .renderer import SolarSystemRenderer


APP_TITLE = "Solar System Simulator"


class SolarSystemApplication:
    def __init__(self) -> None:
        self.root = tk.Tk()
        self.root.title(APP_TITLE)
        self.root.geometry("1440x860")
        self.root.minsize(1120, 720)
        self.root.configure(bg="#05060A")

        self.canvas = tk.Canvas(self.root, bg="#05060A", highlightthickness=0, bd=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        self.fonts = self._create_fonts()
        self.bodies = load_catalog()
        self.body_map = {body.name: body for body in self.bodies}
        self.body_order = [body.name for body in self.bodies]

        initial_days = (datetime.now(timezone.utc) - J2000).total_seconds() / 86_400.0
        self.state = SimulationState(sim_days=initial_days)
        self.camera = Camera()
        self.orbit = OrbitEngine(compact_orbits=self.state.compact_orbits)
        self.renderer = SolarSystemRenderer(self.canvas, self.fonts)

        self.last_tick = time.perf_counter()
        self.drag_start: tuple[int, int] | None = None
        self.drag_moved = False
        self.mouse = (0, 0)
        self.hover: str | None = None

        self._bind_events()

    def run(self) -> None:
        self._tick()
        self.root.mainloop()

    def _create_fonts(self) -> dict[str, font.Font]:
        families = set(font.families())
        base = "Microsoft YaHei UI" if "Microsoft YaHei UI" in families else "Segoe UI"
        return {
            "hero": font.Font(family=base, size=25, weight="bold"),
            "title": font.Font(family=base, size=17, weight="bold"),
            "subtitle": font.Font(family=base, size=11),
            "body": font.Font(family=base, size=10),
            "small": font.Font(family=base, size=8),
            "button": font.Font(family=base, size=9, weight="bold"),
        }

    def _bind_events(self) -> None:
        self.canvas.bind("<ButtonPress-1>", self._on_mouse_down)
        self.canvas.bind("<B1-Motion>", self._on_mouse_drag)
        self.canvas.bind("<ButtonRelease-1>", self._on_mouse_up)
        self.canvas.bind("<Motion>", self._on_mouse_move)
        self.canvas.bind("<MouseWheel>", self._on_wheel)
        self.canvas.bind("<Button-4>", lambda event: self.camera.change_zoom(1.08))
        self.canvas.bind("<Button-5>", lambda event: self.camera.change_zoom(0.92))

        self.root.bind("<space>", lambda event: self._toggle_pause())
        self.root.bind("r", lambda event: self._reset_camera())
        self.root.bind("R", lambda event: self._reset_camera())
        self.root.bind("l", lambda event: self._toggle_labels())
        self.root.bind("L", lambda event: self._toggle_labels())
        self.root.bind("t", lambda event: self._toggle_trails())
        self.root.bind("T", lambda event: self._toggle_trails())
        self.root.bind("f", lambda event: self._toggle_follow())
        self.root.bind("F", lambda event: self._toggle_follow())
        self.root.bind("<plus>", lambda event: self._change_time_scale(1.35))
        self.root.bind("<minus>", lambda event: self._change_time_scale(1 / 1.35))
        self.root.bind("<Right>", lambda event: self._step_selection(1))
        self.root.bind("<Left>", lambda event: self._step_selection(-1))
        self.root.bind("0", lambda event: self._set_focus("Sun"))

        for index, name in enumerate(self.body_order[1:], start=1):
            self.root.bind(str(index), lambda event, planet=name: self._select_body(planet))

    def _tick(self) -> None:
        now = time.perf_counter()
        dt = min(0.1, now - self.last_tick)
        self.last_tick = now

        if not self.state.paused:
            self.state.sim_days += dt * self.state.time_scale

        self.orbit.set_compact_orbits(self.state.compact_orbits)
        self.renderer.draw(
            self.bodies,
            self.body_map,
            self.state,
            self.orbit,
            self.camera,
            self.mouse,
            self.hover,
        )
        self.root.after(16, self._tick)

    def _on_mouse_down(self, event: tk.Event) -> None:
        self.drag_start = (event.x, event.y)
        self.drag_moved = False

    def _on_mouse_drag(self, event: tk.Event) -> None:
        if not self.drag_start:
            return
        dx = event.x - self.drag_start[0]
        dy = event.y - self.drag_start[1]
        if abs(dx) + abs(dy) > 3:
            self.drag_moved = True
        self.camera.rotate_view(dx, dy)
        self.drag_start = (event.x, event.y)

    def _on_mouse_up(self, event: tk.Event) -> None:
        if self.drag_moved:
            return

        ui_action = self._pick_ui(event.x, event.y)
        if ui_action:
            self._handle_action(*ui_action)
            return

        body_name = self._pick_body(event.x, event.y)
        if body_name:
            self._select_body(body_name)

    def _on_mouse_move(self, event: tk.Event) -> None:
        self.mouse = (event.x, event.y)
        self.hover = self._pick_body(event.x, event.y)

    def _on_wheel(self, event: tk.Event) -> None:
        self.camera.change_zoom(1.1 if event.delta > 0 else 0.91)

    def _pick_ui(self, x: float, y: float) -> tuple[str, str] | None:
        for action, value, (x1, y1, x2, y2) in reversed(self.renderer.ui_hitboxes):
            if x1 <= x <= x2 and y1 <= y <= y2:
                return action, value
        return None

    def _pick_body(self, x: float, y: float) -> str | None:
        hits: list[tuple[float, str]] = []
        for name, item in self.renderer.render_cache.items():
            sx, sy = item.screen
            if math.hypot(x - sx, y - sy) <= max(11, item.radius + 5):
                hits.append((item.depth, name))
        if not hits:
            return None
        return sorted(hits, reverse=True)[0][1]

    def _handle_action(self, action: str, value: str) -> None:
        actions = {
            "pause": self._toggle_pause,
            "slower": lambda: self._change_time_scale(1 / 1.45),
            "faster": lambda: self._change_time_scale(1.45),
            "follow": self._toggle_follow,
            "labels": self._toggle_labels,
            "trails": self._toggle_trails,
            "scale": self._toggle_scale_mode,
            "reset": self._reset_camera,
        }

        if action == "select":
            self._select_body(value)
        elif action == "focus":
            self._set_focus(value)
        elif action in actions:
            actions[action]()

    def _select_body(self, name: str) -> None:
        if name not in self.body_map:
            return
        self.state.selected = name
        if name != "Sun":
            self.state.focus = name

    def _set_focus(self, name: str) -> None:
        if name not in self.body_map:
            return
        self.state.focus = name
        self.state.follow_focus = name != "Sun"

    def _step_selection(self, direction: int) -> None:
        index = self.body_order.index(self.state.selected)
        self._select_body(self.body_order[(index + direction) % len(self.body_order)])

    def _change_time_scale(self, factor: float) -> None:
        self.state.time_scale = max(1.0, min(900.0, self.state.time_scale * factor))

    def _toggle_pause(self) -> None:
        self.state.paused = not self.state.paused

    def _toggle_labels(self) -> None:
        self.state.show_labels = not self.state.show_labels

    def _toggle_trails(self) -> None:
        self.state.show_trails = not self.state.show_trails

    def _toggle_scale_mode(self) -> None:
        self.state.compact_orbits = not self.state.compact_orbits

    def _toggle_follow(self) -> None:
        if self.state.focus == "Sun" and self.state.selected != "Sun":
            self.state.focus = self.state.selected
        self.state.follow_focus = not self.state.follow_focus

    def _reset_camera(self) -> None:
        self.camera.reset()
        self.state.focus = "Sun"
        self.state.follow_focus = False
