from __future__ import annotations

from math import dist


def eye_aspect_ratio(points: list[tuple[float, float]]) -> float:
    """Return EAR for six ordered eye landmarks."""
    if len(points) != 6:
        raise ValueError("EAR needs six eye landmarks")
    vertical = dist(points[1], points[5]) + dist(points[2], points[4])
    horizontal = 2 * dist(points[0], points[3])
    return vertical / horizontal if horizontal else 0.0
