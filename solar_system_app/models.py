from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


J2000 = datetime(2000, 1, 1, 12, tzinfo=timezone.utc)


Vector3 = tuple[float, float, float]
Point2 = tuple[float, float]


@dataclass(frozen=True)
class OrbitalElements:
    semi_major_axis_au: float
    eccentricity: float
    inclination_deg: float
    longitude_node_deg: float
    argument_periapsis_deg: float
    mean_anomaly_epoch_deg: float
    period_days: float


@dataclass(frozen=True)
class CelestialBody:
    name: str
    cn_name: str
    kind: str
    color: str
    radius_km: float
    mass: str
    gravity: str
    rotation: str
    temperature: str
    summary: str
    elements: OrbitalElements | None
    axial_tilt_deg: float = 0.0
    visual_radius: float = 8.0


@dataclass
class RenderBody:
    body: CelestialBody
    world: Vector3
    screen: Point2
    depth: float
    radius: float
    perspective: float


@dataclass
class SimulationState:
    sim_days: float
    time_scale: float = 18.0
    paused: bool = False
    selected: str = "Earth"
    focus: str = "Sun"
    follow_focus: bool = False
    show_trails: bool = True
    show_labels: bool = True
    compact_orbits: bool = True
