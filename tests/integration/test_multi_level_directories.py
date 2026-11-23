import io

import pmtiles.tile
import pmtiles.writer
import pytest

import peat_mos.pmtiles

_ZOOM = 12
_TILES_PER_ROW = 4096
_TILE_COUNT_FORCING_LEAF_SPLIT = 16_000

_FIRST_TILE_COORDINATE = (_ZOOM, 0, 0)
_FIRST_TILE_CONTENT = b"tile-0"

_LAST_TILE_COORDINATE = (_ZOOM, 3711, 3)
_LAST_TILE_CONTENT = b"tile-15999"


def _build_archive_with_leaf_directories() -> io.BytesIO:
    buffer = io.BytesIO()
    reference_writer = pmtiles.writer.Writer(buffer)
    for i in range(_TILE_COUNT_FORCING_LEAF_SPLIT):
        x, y = i % _TILES_PER_ROW, (i // _TILES_PER_ROW) % _TILES_PER_ROW
        tile_id = pmtiles.tile.zxy_to_tileid(_ZOOM, x, y)
        reference_writer.write_tile(  # pyright: ignore[reportUnknownMemberType]
            tile_id, f"tile-{i}".encode()
        )
    reference_writer.finalize(  # pyright: ignore[reportUnknownMemberType]
        {
            "tile_type": pmtiles.tile.TileType.UNKNOWN,
            "tile_compression": pmtiles.tile.Compression.NONE,
        },
        {},
    )
    return buffer


def test_reads_tiles_through_multi_level_directories() -> None:
    archive = peat_mos.pmtiles.PMTiles(_build_archive_with_leaf_directories())
    assert archive.header.leaf_directories_length > 0
    assert archive.get_tile(*_FIRST_TILE_COORDINATE) == _FIRST_TILE_CONTENT
    assert archive.get_tile(*_LAST_TILE_COORDINATE) == _LAST_TILE_CONTENT


def test_get_tile_raises_when_max_directory_depth_is_too_shallow() -> None:
    archive = peat_mos.pmtiles.PMTiles(
        _build_archive_with_leaf_directories(), max_directory_depth=1
    )
    with pytest.raises(peat_mos.pmtiles.InvalidArchiveError):
        archive.get_tile(*_FIRST_TILE_COORDINATE)
