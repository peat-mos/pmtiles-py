"""Constants and data types defined by the PMTiles spec.

https://github.com/protomaps/PMTiles/blob/main/spec/v3/spec.md
"""

from dataclasses import dataclass
from enum import IntEnum

# Section 2
MAX_INITIAL_BYTES = 16_384  # header + root directory must fit in the first 16 KiB


# Section 3
HEADER_LENGTH = 127
MAGIC_NUMBER = b"PMTiles"
VERSION = 3
POSITION_SCALE = 10_000_000


class TileType(IntEnum):
    UNKNOWN = 0x00
    MVT = 0x01
    PNG = 0x02
    JPEG = 0x03
    WEBP = 0x04
    AVIF = 0x05
    MLT = 0x06  # MapLibre Vector Tile


class Compression(IntEnum):
    UNKNOWN = 0x00
    NONE = 0x01
    GZIP = 0x02
    BROTLI = 0x03
    ZSTD = 0x04


@dataclass(frozen=True, slots=True)
class Position:
    longitude: float
    latitude: float


@dataclass(frozen=True, slots=True)
class Header:
    version: int
    root_directory_offset: int
    root_directory_length: int
    metadata_offset: int
    metadata_length: int
    leaf_directories_offset: int
    leaf_directories_length: int
    tile_data_offset: int
    tile_data_length: int
    number_of_addressed_tiles: int  # 0 = unknown
    number_of_tile_entries: int  # 0 = unknown
    number_of_tile_contents: int  # 0 = unknown
    clustered: bool
    internal_compression: Compression
    tile_compression: Compression
    tile_type: TileType
    min_zoom: int
    max_zoom: int
    min_position: Position
    max_position: Position
    center_zoom: int
    center_position: Position


# Section 4
MAX_ROOT_DIRECTORY_LENGTH = 16_257


@dataclass(frozen=True, slots=True)
class DirectoryEntry:
    tile_id: int
    offset: int
    length: int
    run_length: int


type Directory = tuple[DirectoryEntry, ...]
