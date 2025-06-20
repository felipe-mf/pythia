"""
Copyright 2024 Nathan P. Bombana

This module contains functions related to the identification of individual weather stations on NASA POWER,
referred to as "grid tiles". NASA POWER has data in a resolution of up to 0.5x0.625 degrees latitude and longitude.
This means that if we request data for a location at (0, 0) followed by (0.1, 0.2), we will get the data for the
same weather station. This wastes requests and time.

To work around this problem, a grid system is defined, and an ID is assigned to each grid tile. Note that this ID
is NOT the index of the tile. Using this system, we can infer if two different sets of coordinates resolve to the
same grid tile, and thus the same weather station.

The NASA POWER data is composed of meteorology data and solar irradiation data. These two grids differ in their
resolution, thus the grid system cannot be defined as a simple 2D regular grid. Instead, two regular grids are
defined: one for meteorology data, one for solar irradiation data. Each grid has its own resolution.

When calculating the ID for a given coordinate, we seek the cell ID in both grids and do Cantor pairing to combine
both IDs into a single piece of information. The same process is reversed when retrieving the coordinates of a
given grid tile ID.

Important note: the meteorology grid tile is tilted by 0.3125x0.25 degrees in direction to the bottom-left corner
of the Mercator projection, making the alignment of meteorology and solar data even more challenging.
"""

import math
from dataclasses import dataclass
from typing import Tuple, List


@dataclass
class BBox:
    """A bounding box, as defined by the GeoJSON standard.
    From index 0 to 3, the values are: bottom-left longitude, bottom-left latitude, top-right longitude and top-right latitude.
    See https://tools.ietf.org/html/rfc7946#section-5
    """

    min_lon: float
    min_lat: float
    max_lon: float
    max_lat: float

    def __post_init__(self):
        """Validates the bounding box parameters."""
        if self.min_lon > self.max_lon or self.min_lat > self.max_lat:
            raise ValueError(
                f"bottomLeft ({self.min_lon}, {self.min_lat}) is greater than topRight ({self.max_lon}, {self.max_lat})"
            )
        if (
            self.min_lon < -180
            or self.min_lat < -90
            or self.max_lon > 180
            or self.max_lat > 90
        ):
            raise ValueError("longitude or latitude are out of bounds")

    def centroid(self) -> Tuple[float, float]:
        """Returns the centroid (center point) of the bounding box."""
        return (self.min_lon + self.max_lon) / 2, (self.min_lat + self.max_lat) / 2

    def intersects(self, other: "BBox") -> bool:
        """Returns True if this bounding box intersects with another."""
        return (
            self.max_lon >= other.min_lon
            and self.min_lon <= other.max_lon
            and self.max_lat >= other.min_lat
            and self.min_lat <= other.max_lat
        )

    def intersection(self, other: "BBox") -> "BBox":
        """Returns the intersection of this bounding box with another."""
        if not self.intersects(other):
            raise ValueError(f"bounding boxes {self} and {other} do not intersect")
        return BBox(
            max(self.min_lon, other.min_lon),
            max(self.min_lat, other.min_lat),
            min(self.max_lon, other.max_lon),
            min(self.max_lat, other.max_lat),
        )


@dataclass
class RegularGrid2D:
    """Represents a regular grid in a finite 2-dimensional plane.
    See https://en.wikipedia.org/wiki/Regular_grid
    """

    min_x: float
    min_y: float
    max_x: float
    max_y: float
    cell_width: float
    cell_height: float

    def __post_init__(self):
        """Validates the grid parameters."""
        if self.min_x > self.max_x:
            raise ValueError("min_x must be less than or equal to max_x")
        if self.min_y > self.max_y:
            raise ValueError("min_y must be less than or equal to max_y")
        if self.cell_width <= 0:
            raise ValueError("cell_width must be greater than 0")
        if self.cell_height <= 0:
            raise ValueError("cell_height must be greater than 0")

        # Check if grid dimensions are symmetric
        if math.fmod(self.max_x - self.min_x, self.cell_width) != 0:
            raise ValueError(
                "cell_width is not symmetric with respect to the grid width"
            )
        if math.fmod(self.max_y - self.min_y, self.cell_height) != 0:
            raise ValueError(
                "cell_height is not symmetric with respect to the grid height"
            )

    def count_cells_x(self) -> int:
        """Returns the number of cells in the x direction."""
        return math.ceil((self.max_x - self.min_x) / self.cell_width)

    def count_cells_y(self) -> int:
        """Returns the number of cells in the y direction."""
        return math.ceil((self.max_y - self.min_y) / self.cell_height)

    def count_cells(self) -> int:
        """Returns the total number of cells in the grid."""
        return self.count_cells_x() * self.count_cells_y()

    def cell_id(self, x: float, y: float) -> int:
        """Returns the cell ID for the given coordinates."""
        if x < self.min_x or x > self.max_x or y < self.min_y or y > self.max_y:
            raise ValueError(f"coordinates ({x}, {y}) are outside the grid boundaries")

        x_idx = int((x - self.min_x) / self.cell_width)
        y_idx = int((y - self.min_y) / self.cell_height)
        return y_idx * self.count_cells_x() + x_idx

    def corners(self, cell_id: int) -> Tuple[float, float, float, float]:
        """Returns the corners (min_x, min_y, max_x, max_y) of the cell with the given ID."""
        if cell_id < 0 or cell_id >= self.count_cells():
            raise ValueError(f"cell_id {cell_id} is out of bounds")

        idx_x = cell_id % self.count_cells_x()
        idx_y = cell_id // self.count_cells_x()

        min_x = self.min_x + idx_x * self.cell_width
        max_x = self.min_x + (idx_x + 1) * self.cell_width
        min_y = self.min_y + idx_y * self.cell_height
        max_y = self.min_y + (idx_y + 1) * self.cell_height
        return min_x, min_y, max_x, max_y


def cantor_pair(a: int, b: int) -> int:
    """Combines two non-negative integers into a single integer using the Cantor pairing function."""
    return ((a + b) * (a + b + 1)) // 2 + b


def cantor_unpair(z: int) -> Tuple[int, int]:
    """Splits a Cantor paired number back into its original components."""
    w = int((math.sqrt(8 * z + 1) - 1) / 2)
    t = (w * w + w) // 2
    b = z - t
    a = w - b
    return a, b


# Global grid definitions
GRID_METEOROLOGY = RegularGrid2D(
    min_x=-180.3125,
    min_y=-90.25,
    max_x=179.6875,
    max_y=89.75,
    cell_width=0.625,
    cell_height=0.5,
)

GRID_SOLAR = RegularGrid2D(
    min_x=-180, min_y=-90, max_x=180, max_y=90, cell_width=1, cell_height=1
)


def id_at(lon: float, lat: float) -> int:
    """Returns the grid tile ID for the given coordinates."""
    try:
        met = GRID_METEOROLOGY.cell_id(lon, lat)
        srad = GRID_SOLAR.cell_id(lon, lat)
        return cantor_pair(met, srad)
    except ValueError as e:
        raise ValueError(
            f"Failed to calculate grid tile ID for coordinates ({lon}, {lat}): {str(e)}"
        )


def center_of_id(grid_id: int) -> Tuple[float, float]:
    """Returns the latitude and longitude of the center of the NASA POWER grid tile for the given ID."""
    box = bounds_of_grid_tile(grid_id)
    return box.centroid()


def bounds_of_grid_tile(grid_id: int) -> BBox:
    """Returns the bounding box of the grid tile for the given ID."""
    met_id, srad_id = cantor_unpair(grid_id)

    try:
        # Get meteorology grid bounds
        minx_met, miny_met, maxx_met, maxy_met = GRID_METEOROLOGY.corners(met_id)
        met_box = BBox(
            max(minx_met, -180),
            max(miny_met, -90),
            min(maxx_met, 180),
            min(maxy_met, 90),
        )

        # Get solar radiation grid bounds
        minx_srad, miny_srad, maxx_srad, maxy_srad = GRID_SOLAR.corners(srad_id)
        srad_box = BBox(minx_srad, miny_srad, maxx_srad, maxy_srad)

        # Return the intersection of both boxes
        return met_box.intersection(srad_box)
    except (ValueError, IndexError) as e:
        raise ValueError(
            f"Failed to calculate bounds for grid tile {grid_id}: {str(e)}"
        )


def ids_in_square(box: BBox) -> List[int]:
    """Returns the IDs of all the grid tiles that are contained in the given square."""
    ids = []
    lon, lat = box.min_lon, box.min_lat

    while True:
        grid_id = id_at(lon, lat)
        other_box = bounds_of_grid_tile(grid_id)

        if box.intersects(other_box):
            ids.append(grid_id)
            lon, lat = other_box.max_lon, other_box.min_lat
        else:
            lon, lat = box.min_lon, other_box.max_lat
            if not bounds_of_grid_tile(id_at(lon, lat)).intersects(box):
                break

    return ids
