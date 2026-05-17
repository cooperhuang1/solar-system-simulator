from __future__ import annotations

import math
from datetime import datetime, timedelta

from .models import CelestialBody, J2000, Vector3


class OrbitEngine:
    """Computes heliocentric positions from approximate Keplerian elements."""

    def __init__(self, compact_orbits: bool = True, distance_scale: float = 1.0) -> None:
        self.compact_orbits = compact_orbits
        self.distance_scale = distance_scale
        self._orbit_cache: dict[tuple[str, bool], list[Vector3]] = {}

    @staticmethod
    def days_since_j2000(value: datetime) -> float:
        return (value - J2000).total_seconds() / 86_400.0

    @staticmethod
    def date_from_days(days: float) -> datetime:
        return J2000 + timedelta(days=days)

    def set_compact_orbits(self, enabled: bool) -> None:
        if self.compact_orbits != enabled:
            self.compact_orbits = enabled
            self._orbit_cache.clear()

    def positions(self, bodies: list[CelestialBody], days: float) -> dict[str, Vector3]:
        return {body.name: self.position(body, days) for body in bodies}

    def position(self, body: CelestialBody, days: float) -> Vector3:
        elements = body.elements
        if elements is None:
            return 0.0, 0.0, 0.0

        mean_anomaly = math.radians(elements.mean_anomaly_epoch_deg) + math.tau * days / elements.period_days
        eccentric_anomaly = self._solve_kepler(mean_anomaly % math.tau, elements.eccentricity)

        x_orb = elements.semi_major_axis_au * (math.cos(eccentric_anomaly) - elements.eccentricity)
        y_orb = (
            elements.semi_major_axis_au
            * math.sqrt(1 - elements.eccentricity * elements.eccentricity)
            * math.sin(eccentric_anomaly)
        )

        omega = math.radians(elements.argument_periapsis_deg)
        node = math.radians(elements.longitude_node_deg)
        inc = math.radians(elements.inclination_deg)

        x1 = x_orb * math.cos(omega) - y_orb * math.sin(omega)
        y1 = x_orb * math.sin(omega) + y_orb * math.cos(omega)

        x = x1 * math.cos(node) - y1 * math.cos(inc) * math.sin(node)
        y = x1 * math.sin(node) + y1 * math.cos(inc) * math.cos(node)
        z = y1 * math.sin(inc)
        return self._scale_vector(x, z, y)

    def orbit_polyline(self, body: CelestialBody, samples: int = 260) -> list[Vector3]:
        if body.elements is None:
            return []

        key = (body.name, self.compact_orbits)
        cached = self._orbit_cache.get(key)
        if cached is not None:
            return cached

        period = body.elements.period_days
        points = [self.position(body, period * i / samples) for i in range(samples + 1)]
        self._orbit_cache[key] = points
        return points

    def trail_polyline(self, body: CelestialBody, days: float, samples: int = 48) -> list[Vector3]:
        if body.elements is None:
            return []
        trail_days = min(body.elements.period_days * 0.22, 900)
        return [
            self.position(body, days - trail_days * i / max(1, samples - 1))
            for i in range(samples)
        ]

    def _solve_kepler(self, mean_anomaly: float, eccentricity: float) -> float:
        eccentric_anomaly = mean_anomaly
        for _ in range(8):
            eccentric_anomaly -= (
                eccentric_anomaly
                - eccentricity * math.sin(eccentric_anomaly)
                - mean_anomaly
            ) / (1 - eccentricity * math.cos(eccentric_anomaly))
        return eccentric_anomaly

    def _scale_vector(self, x_au: float, y_au: float, z_au: float) -> Vector3:
        radius_au = math.sqrt(x_au * x_au + y_au * y_au + z_au * z_au)
        if radius_au == 0:
            return 0.0, 0.0, 0.0

        if self.compact_orbits:
            scaled_radius = (radius_au ** 0.66) * 132 * self.distance_scale
        else:
            scaled_radius = radius_au * 58 * self.distance_scale

        factor = scaled_radius / radius_au
        return x_au * factor, y_au * factor, z_au * factor
