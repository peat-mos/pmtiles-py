import gzip
import io

import pmtiles.tile
import pmtiles.writer

import peat_mos.pmtiles

_RAW_TILE_CONTENT = b"hello pmtiles gzip integration test"


def test_reads_tile_through_gzip_compressed_directory() -> None:
    buffer = io.BytesIO()
    reference_writer = pmtiles.writer.Writer(buffer)
    reference_writer.write_tile(  # pyright: ignore[reportUnknownMemberType]
        pmtiles.tile.zxy_to_tileid(0, 0, 0),
        gzip.compress(_RAW_TILE_CONTENT, mtime=0),
    )
    reference_writer.finalize(  # pyright: ignore[reportUnknownMemberType]
        {
            "tile_type": pmtiles.tile.TileType.UNKNOWN,
            "tile_compression": pmtiles.tile.Compression.GZIP,
        },
        {},
    )

    archive = peat_mos.pmtiles.PMTiles(buffer)
    assert archive.header.internal_compression == peat_mos.pmtiles.Compression.GZIP
    assert archive.header.tile_compression == peat_mos.pmtiles.Compression.GZIP

    tile = archive.get_tile(0, 0, 0)
    assert tile is not None
    assert gzip.decompress(tile) == _RAW_TILE_CONTENT
