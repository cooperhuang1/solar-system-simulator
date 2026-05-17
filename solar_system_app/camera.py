from __future__ import annotations

import math

from .models import Vector3


class Camera:
    def __init__(self) -> None:
        self.yaw = math.radians(-34)
        self.pitch = math.radians(58)
        self.zoom = 1.0

    def reset(self) -> None:
        self.yaw = math.radians(-34)
        self.pitch = math.radians(58)
        self.zoom = 1.0

    def rotate_view(self, dx: float, dy: float) -> None:
        self.yaw += dx * 0.006
        self.pitch = max(math.radians(12), min(math.radians(86), self.pitch + dy * 0.004))

    def change_zoom(self, factor: float) -> None:
        self.zoom = max(0.38, min(3.2, self.zoom * factor))

    def project(
        self,
        point: Vector3,
        center: tuple[float, float],
        focus_offset: Vector3 = (0.0, 0.0, 0.0),
    ) -> tuple[float, float, float, float]:
        x = point[0] - focus_offset[0]
        y = point[1] - focus_offset[1]
        z = point[2] - focus_offset[2]

        cy, sy = math.cos(self.yaw), math.sin(self.yaw)
        x, z = x * cy - z * sy, x * sy + z * cy

        cp, sp = math.cos(self.pitch), math.sin(self.pitch)
        y, z = y * cp - z * sp, y * sp + z * cp

        camera_distance = 920.0
        perspective = camera_distance / (camera_distance + z)
        return (
            center[0] + x * self.zoom * perspective,
            center[1] + y * self.zoom * perspective,
            z,
            perspective,
        )
