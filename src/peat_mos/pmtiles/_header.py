import struct
from dataclasses import dataclass

from peat_mos.pmtiles import _spec
from peat_mos.pmtiles._datatypes import Err, Error, Ok, Result

# little-endian, no padding: magic, version, 11 x u64, 6 x u8, 4 x i32, u8, 2 x i32
_HEADER_STRUCT = struct.Struct("<7sB11Q6B4iB2i")


@dataclass(frozen=True, slots=True)
class HeaderTooShortError(Error):
    length: int


@dataclass(frozen=True, slots=True)
class InvalidMagicNumberError(Error):
    found: bytes


@dataclass(frozen=True, slots=True)
class UnsupportedVersionError(Error):
    version: int


@dataclass(frozen=True, slots=True)
class InvalidClusteredValueError(Error):
    clustered: int


@dataclass(frozen=True, slots=True)
class InvalidInternalCompressionError(Error):
    compression: int


@dataclass(frozen=True, slots=True)
class InvalidTileCompressionError(Error):
    compression: int


@dataclass(frozen=True, slots=True)
class InvalidTileTypeError(Error):
    tile_type: int


@dataclass(frozen=True, slots=True)
class MaxZoomBelowMinZoomError(Error):
    min_zoom: int
    max_zoom: int


@dataclass(frozen=True, slots=True)
class RootDirectoryOutsideInitialBytesError(Error):
    root_directory_end: int


type HeaderError = (
    HeaderTooShortError
    | InvalidMagicNumberError
    | UnsupportedVersionError
    | InvalidClusteredValueError
    | InvalidInternalCompressionError
    | InvalidTileCompressionError
    | InvalidTileTypeError
    | MaxZoomBelowMinZoomError
    | RootDirectoryOutsideInitialBytesError
)


def decode_header(buffer: memoryview) -> Result[_spec.Header, HeaderError]:
    if len(buffer) < _spec.HEADER_LENGTH:
        return Err(HeaderTooShortError(len(buffer)))

    (
        magic_number,
        version,
        root_directory_offset,
        root_directory_length,
        metadata_offset,
        metadata_length,
        leaf_directories_offset,
        leaf_directories_length,
        tile_data_offset,
        tile_data_length,
        number_of_addressed_tiles,
        number_of_tile_entries,
        number_of_tile_contents,
        clustered,
        internal_compression,
        tile_compression,
        tile_type,
        min_zoom,
        max_zoom,
        min_longitude_e7,
        min_latitude_e7,
        max_longitude_e7,
        max_latitude_e7,
        center_zoom,
        center_longitude_e7,
        center_latitude_e7,
    ) = _HEADER_STRUCT.unpack_from(buffer)

    if magic_number != _spec.MAGIC_NUMBER:
        return Err(InvalidMagicNumberError(magic_number))
    if version != _spec.VERSION:
        return Err(UnsupportedVersionError(version))
    if clustered not in (0, 1):
        return Err(InvalidClusteredValueError(clustered))
    if internal_compression not in _spec.Compression:
        return Err(InvalidInternalCompressionError(internal_compression))
    if tile_compression not in _spec.Compression:
        return Err(InvalidTileCompressionError(tile_compression))
    if tile_type not in _spec.TileType:
        return Err(InvalidTileTypeError(tile_type))
    if max_zoom < min_zoom:
        return Err(MaxZoomBelowMinZoomError(min_zoom, max_zoom))
    root_directory_end = root_directory_offset + root_directory_length
    if root_directory_end > _spec.MAX_INITIAL_BYTES:
        return Err(RootDirectoryOutsideInitialBytesError(root_directory_end))

    return Ok(
        _spec.Header(
            version=version,
            root_directory_offset=root_directory_offset,
            root_directory_length=root_directory_length,
            metadata_offset=metadata_offset,
            metadata_length=metadata_length,
            leaf_directories_offset=leaf_directories_offset,
            leaf_directories_length=leaf_directories_length,
            tile_data_offset=tile_data_offset,
            tile_data_length=tile_data_length,
            number_of_addressed_tiles=number_of_addressed_tiles,
            number_of_tile_entries=number_of_tile_entries,
            number_of_tile_contents=number_of_tile_contents,
            clustered=clustered == 1,
            internal_compression=_spec.Compression(internal_compression),
            tile_compression=_spec.Compression(tile_compression),
            tile_type=_spec.TileType(tile_type),
            min_zoom=min_zoom,
            max_zoom=max_zoom,
            min_position=_decode_position(min_longitude_e7, min_latitude_e7),
            max_position=_decode_position(max_longitude_e7, max_latitude_e7),
            center_zoom=center_zoom,
            center_position=_decode_position(center_longitude_e7, center_latitude_e7),
        )
    )


def _decode_position(longitude_e7: int, latitude_e7: int) -> _spec.Position:
    return _spec.Position(
        longitude_e7 / _spec.POSITION_SCALE, latitude_e7 / _spec.POSITION_SCALE
    )
