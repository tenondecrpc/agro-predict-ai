"""Mapping of Paraguayan departments to centroid coordinates.

Used by the weather risk fetcher. Coordinates are approximate centroids
suitable for representative forecasts at department scale; they are not
fit for parcel-level agronomy. Source: standard public references.
"""

from __future__ import annotations

from decimal import Decimal


class DepartmentCoords:
    __slots__ = ("name", "lat", "lng")

    def __init__(self, name: str, lat: Decimal | float, lng: Decimal | float) -> None:
        self.name = name
        self.lat = Decimal(str(lat))
        self.lng = Decimal(str(lng))


# Keys are lowercased and ASCII-folded for tolerant lookup.
DEPARTMENT_COORDS: dict[str, DepartmentCoords] = {
    "asuncion": DepartmentCoords("Asuncion", -25.2637, -57.5759),
    "concepcion": DepartmentCoords("Concepcion", -23.4064, -57.4344),
    "san pedro": DepartmentCoords("San Pedro", -24.0666, -57.0833),
    "cordillera": DepartmentCoords("Cordillera", -25.3275, -57.0833),
    "guaira": DepartmentCoords("Guaira", -25.7833, -56.4500),
    "caaguazu": DepartmentCoords("Caaguazu", -25.4666, -56.0166),
    "caazapa": DepartmentCoords("Caazapa", -26.1833, -56.3666),
    "itapua": DepartmentCoords("Itapua", -27.3333, -55.8666),
    "misiones": DepartmentCoords("Misiones", -26.8833, -57.0833),
    "paraguari": DepartmentCoords("Paraguari", -25.6333, -57.1500),
    "alto parana": DepartmentCoords("Alto Parana", -25.5166, -54.7833),
    "central": DepartmentCoords("Central", -25.3333, -57.5500),
    "neembucu": DepartmentCoords("Neembucu", -27.0166, -58.2833),
    "amambay": DepartmentCoords("Amambay", -22.5666, -56.0333),
    "canindeyu": DepartmentCoords("Canindeyu", -24.1333, -55.5333),
    "presidente hayes": DepartmentCoords("Presidente Hayes", -23.3500, -59.0500),
    "boqueron": DepartmentCoords("Boqueron", -22.0833, -60.4833),
    "alto paraguay": DepartmentCoords("Alto Paraguay", -20.9166, -59.5833),
}


def normalize(name: str) -> str:
    """Lowercase and remove common Spanish accents for lookup."""
    table = str.maketrans("aeiouAEIOU", "aeiouaeiou", "")
    folded = (
        name.lower()
        .replace("á", "a")
        .replace("é", "e")
        .replace("í", "i")
        .replace("ó", "o")
        .replace("ú", "u")
        .replace("ñ", "n")
    )
    return folded.translate(table).strip()


def get_coords(department: str) -> DepartmentCoords | None:
    return DEPARTMENT_COORDS.get(normalize(department))
