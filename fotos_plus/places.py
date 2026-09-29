from __future__ import annotations

import json
from array import array
from functools import lru_cache
from importlib import resources
from typing import Iterable, Optional, Sequence

COORDINATE_SCALE = 10000
COORDINATE_LIMIT_LON = 180 * COORDINATE_SCALE
COORDINATE_LIMIT_LAT = 90 * COORDINATE_SCALE

GRID_COLUMNS = 180
GRID_ROWS = 90

CELL_LONGITUDE = (2 * COORDINATE_LIMIT_LON) // GRID_COLUMNS
CELL_LATITUDE = (2 * COORDINATE_LIMIT_LAT) // GRID_ROWS

DATA_PACKAGE = "fotos_plus.data"
DATA_RESOURCE = "countries.geojson"


class CountryDataError(Exception):
    pass


class Country:
    __slots__ = ("code", "name")

    def __init__(self, code: str, name: str) -> None:
        self.code = code
        self.name = name

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Country):
            return NotImplemented
        return self.code == other.code and self.name == other.name

    def __hash__(self) -> int:
        return hash((self.code, self.name))

    def __repr__(self) -> str:
        return f"Country({self.code!r}, {self.name!r})"


def _band_of(lat: int) -> int:
    band = (lat + COORDINATE_LIMIT_LAT) // CELL_LATITUDE
    if band < 0:
        return 0
    if band >= GRID_ROWS:
        return GRID_ROWS - 1
    return band


def _build_bands(points: array) -> tuple[array, array]:
    """Reparte las aristas del anillo por la franja de latitud que atraviesan.

    Devuelve un array plano con las posiciones de las aristas y otro con los offsets de
    cada franja, de forma que un rango contiguo del array son las aristas de esa franja.
    """
    count = len(points)
    per_band: list[list[int]] = [[] for _ in range(GRID_ROWS + 1)]
    for position in range(0, count, 2):
        following = (position + 2) % count
        y1 = points[position + 1]
        y2 = points[following + 1]
        low = _band_of(y1 if y1 < y2 else y2)
        high = _band_of(y1 if y1 > y2 else y2)
        for band in range(low, high + 1):
            per_band[band].append(position)
    edges = array("i")
    bands = array("i", bytes(4 * (GRID_ROWS + 1)))
    cursor = 0
    bands[0] = 0
    for band in range(GRID_ROWS):
        bucket = per_band[band]
        if bucket:
            edges.extend(bucket)
            cursor += len(bucket)
        bands[band + 1] = cursor
    return edges, bands


class _Ring:
    """Un anillo con indice de franjas de latitud.

    El algoritmo de cruce de rayo solo necesita las aristas cuya latitud abarca la
    consulta. Guardar esas aristas por franja evita recorrer anillos de miles de puntos
    (Argentina tiene 4248) en cada consulta.
    """

    __slots__ = (
        "points",
        "min_lon",
        "min_lat",
        "max_lon",
        "max_lat",
        "edges",
        "bands",
    )

    def __init__(self, coordinates: Sequence[Sequence[float]]) -> None:
        points = array("i")
        min_lon = COORDINATE_LIMIT_LON
        min_lat = COORDINATE_LIMIT_LAT
        max_lon = -COORDINATE_LIMIT_LON
        max_lat = -COORDINATE_LIMIT_LAT
        for coordinate in coordinates:
            lon = int(round(coordinate[0] * COORDINATE_SCALE))
            lat = int(round(coordinate[1] * COORDINATE_SCALE))
            if not (-COORDINATE_LIMIT_LON <= lon <= COORDINATE_LIMIT_LON):
                lon = min(max(lon, -COORDINATE_LIMIT_LON), COORDINATE_LIMIT_LON)
            if not (-COORDINATE_LIMIT_LAT <= lat <= COORDINATE_LIMIT_LAT):
                lat = min(max(lat, -COORDINATE_LIMIT_LAT), COORDINATE_LIMIT_LAT)
            points.append(lon)
            points.append(lat)
            if lon < min_lon:
                min_lon = lon
            if lon > max_lon:
                max_lon = lon
            if lat < min_lat:
                min_lat = lat
            if lat > max_lat:
                max_lat = lat
        self.points = points
        self.min_lon = min_lon
        self.min_lat = min_lat
        self.max_lon = max_lon
        self.max_lat = max_lat
        self.edges, self.bands = _build_bands(points)

    @property
    def point_count(self) -> int:
        return len(self.points) // 2

    def contains(self, lon: int, lat: int) -> bool:
        if not (self.min_lon <= lon <= self.max_lon):
            return False
        if not (self.min_lat <= lat <= self.max_lat):
            return False
        points = self.points
        count = len(points)
        edges = self.edges
        band = (lat + COORDINATE_LIMIT_LAT) // CELL_LATITUDE
        if band < 0:
            band = 0
        elif band >= GRID_ROWS:
            band = GRID_ROWS - 1
        start = self.bands[band]
        end = self.bands[band + 1]
        inside = False
        for slot in range(start, end):
            position = edges[slot]
            following = (position + 2) % count
            y1 = points[position + 1]
            y2 = points[following + 1]
            if (y1 > lat) != (y2 > lat):
                x1 = points[position]
                x2 = points[following]
                if lon < x1 + (lat - y1) * (x2 - x1) / (y2 - y1):
                    inside = not inside
        return inside


class _Polygon:
    __slots__ = ("outer", "holes", "country", "min_lon", "min_lat", "max_lon", "max_lat")

    def __init__(self, outer: _Ring, holes: list[_Ring], country: Country) -> None:
        self.outer = outer
        self.holes = holes
        self.country = country
        self.min_lon = outer.min_lon
        self.min_lat = outer.min_lat
        self.max_lon = outer.max_lon
        self.max_lat = outer.max_lat

    def contains(self, lon: int, lat: int) -> bool:
        if not self.outer.contains(lon, lat):
            return False
        for hole in self.holes:
            if hole.contains(lon, lat):
                return False
        return True


class CountryIndex:
    def __init__(self, version: int, polygons: list[_Polygon]) -> None:
        self.version = version
        self._polygons = polygons
        self._grid: dict[tuple[int, int], list[int]] = {}
        for position, polygon in enumerate(polygons):
            for cell in self._cells_for(polygon):
                self._grid.setdefault(cell, []).append(position)

    @staticmethod
    def _cell_of(lon: int, lat: int) -> tuple[int, int]:
        column = (lon + COORDINATE_LIMIT_LON) // CELL_LONGITUDE
        row = (lat + COORDINATE_LIMIT_LAT) // CELL_LATITUDE
        if column < 0:
            column = 0
        elif column >= GRID_COLUMNS:
            column = GRID_COLUMNS - 1
        if row < 0:
            row = 0
        elif row >= GRID_ROWS:
            row = GRID_ROWS - 1
        return column, row

    @staticmethod
    def _cells_for(polygon: _Polygon) -> Iterable[tuple[int, int]]:
        first = CountryIndex._cell_of(polygon.min_lon, polygon.min_lat)
        last = CountryIndex._cell_of(polygon.max_lon, polygon.max_lat)
        for column in range(min(first[0], last[0]), max(first[0], last[0]) + 1):
            for row in range(min(first[1], last[1]), max(first[1], last[1]) + 1):
                yield column, row

    @property
    def polygon_count(self) -> int:
        return len(self._polygons)

    def country_of(self, latitude: float, longitude: float) -> Optional[Country]:
        if latitude is None or longitude is None:
            return None
        if not (-90.0 <= latitude <= 90.0) or not (-180.0 <= longitude <= 180.0):
            return None
        lon = int(round(longitude * COORDINATE_SCALE))
        lat = int(round(latitude * COORDINATE_SCALE))
        column, row = self._cell_of(lon, lat)
        for position in self._grid.get((column, row), ()):
            polygon = self._polygons[position]
            if not (
                polygon.min_lon <= lon <= polygon.max_lon
                and polygon.min_lat <= lat <= polygon.max_lat
            ):
                continue
            if polygon.contains(lon, lat):
                return polygon.country
        return None


def _build_index(payload: dict) -> CountryIndex:
    version = payload.get("version")
    if not isinstance(version, int):
        raise CountryDataError("el conjunto de paises no declara una version entera")
    features = payload.get("features")
    if not isinstance(features, list) or not features:
        raise CountryDataError("el conjunto de paises no trae features")

    polygons: list[_Polygon] = []
    for feature in features:
        properties = feature.get("properties") or {}
        name = properties.get("name")
        code = properties.get("code")
        if not name or not code:
            raise CountryDataError("una feature del conjunto de paises no declara name/code")
        geometry = feature.get("geometry")
        if not geometry:
            continue
        geometry_type = geometry.get("type")
        coordinates = geometry.get("coordinates")
        if geometry_type == "Polygon":
            parts = [coordinates]
        elif geometry_type == "MultiPolygon":
            parts = coordinates
        else:
            continue
        country = Country(code, name)
        for part in parts:
            if not part or len(part[0]) < 4:
                continue
            outer = _Ring(part[0])
            if outer.point_count < 4:
                continue
            holes = [_Ring(ring) for ring in part[1:] if len(ring) >= 4]
            polygons.append(_Polygon(outer, holes, country))
    if not polygons:
        raise CountryDataError("el conjunto de paises no tiene poligonos usables")
    return CountryIndex(version, polygons)


@lru_cache(maxsize=1)
def _load_index() -> CountryIndex:
    text = (
        resources.files(DATA_PACKAGE)
        .joinpath(DATA_RESOURCE)
        .read_text(encoding="utf-8")
    )
    try:
        payload = json.loads(text)
    except ValueError as error:
        raise CountryDataError(f"el conjunto de paises no es JSON valido: {error}") from error
    return _build_index(payload)


def country_index() -> CountryIndex:
    return _load_index()


def countries_version() -> int:
    return _load_index().version


def country_of(latitude: Optional[float], longitude: Optional[float]) -> Optional[Country]:
    return _load_index().country_of(latitude, longitude)
