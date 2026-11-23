import struct

import factories
import pytest

from peat_mos.pmtiles import _header, _spec
from peat_mos.pmtiles._datatypes import Err, Ok

# Independent of pmtiles._header's own struct definition, so a mistake in that
# definition can't silently agree with this test's encoding of the same bytes.
# Layout per spec v3 section 3: magic, version, 11 x u64, 6 x u8, 4 x i32, u8, 2 x i32.
_HEADER_STRUCT = struct.Struct("<7sB11Q6B4iB2i")


@pytest.mark.parametrize(
    (
        "header",
        "magic_number",
        "clustered",
        "internal_compression",
        "tile_compression",
        "tile_type",
        "expected",
    ),
    [
        pytest.param(
            factories.header(),
            _spec.MAGIC_NUMBER,
            None,
            None,
            None,
            None,
            Ok(factories.header()),
            id="round_trip",
        ),
        pytest.param(
            factories.header(version=99),
            _spec.MAGIC_NUMBER,
            None,
            None,
            None,
            None,
            Err(_header.UnsupportedVersionError(99)),
            id="unsupported_version",
        ),
        pytest.param(
            factories.header(min_zoom=5, max_zoom=3),
            _spec.MAGIC_NUMBER,
            None,
            None,
            None,
            None,
            Err(_header.MaxZoomBelowMinZoomError(min_zoom=5, max_zoom=3)),
            id="max_zoom_below_min_zoom",
        ),
        pytest.param(
            factories.header(root_directory_offset=16380, root_directory_length=10),
            _spec.MAGIC_NUMBER,
            None,
            None,
            None,
            None,
            Err(
                _header.RootDirectoryOutsideInitialBytesError(root_directory_end=16390)
            ),
            id="root_directory_outside_initial_bytes",
        ),
        pytest.param(
            factories.header(),
            b"WRONG!!",
            None,
            None,
            None,
            None,
            Err(_header.InvalidMagicNumberError(found=b"WRONG!!")),
            id="invalid_magic_number",
        ),
        pytest.param(
            factories.header(),
            _spec.MAGIC_NUMBER,
            2,
            None,
            None,
            None,
            Err(_header.InvalidClusteredValueError(2)),
            id="invalid_clustered_value",
        ),
        pytest.param(
            factories.header(),
            _spec.MAGIC_NUMBER,
            None,
            99,
            None,
            None,
            Err(_header.InvalidInternalCompressionError(99)),
            id="invalid_internal_compression",
        ),
        pytest.param(
            factories.header(),
            _spec.MAGIC_NUMBER,
            None,
            None,
            99,
            None,
            Err(_header.InvalidTileCompressionError(99)),
            id="invalid_tile_compression",
        ),
        pytest.param(
            factories.header(),
            _spec.MAGIC_NUMBER,
            None,
            None,
            None,
            99,
            Err(_header.InvalidTileTypeError(99)),
            id="invalid_tile_type",
        ),
    ],
)
def test_decode_header(
    header: _spec.Header,
    magic_number: bytes,
    clustered: int | None,
    internal_compression: int | None,
    tile_compression: int | None,
    tile_type: int | None,
    expected: object,
) -> None:
    buffer = memoryview(
        _HEADER_STRUCT.pack(
            magic_number,
            header.version,
            header.root_directory_offset,
            header.root_directory_length,
            header.metadata_offset,
            header.metadata_length,
            header.leaf_directories_offset,
            header.leaf_directories_length,
            header.tile_data_offset,
            header.tile_data_length,
            header.number_of_addressed_tiles,
            header.number_of_tile_entries,
            header.number_of_tile_contents,
            int(header.clustered) if clustered is None else clustered,
            int(header.internal_compression)
            if internal_compression is None
            else internal_compression,
            int(header.tile_compression)
            if tile_compression is None
            else tile_compression,
            int(header.tile_type) if tile_type is None else tile_type,
            header.min_zoom,
            header.max_zoom,
            round(header.min_position.longitude * _spec.POSITION_SCALE),
            round(header.min_position.latitude * _spec.POSITION_SCALE),
            round(header.max_position.longitude * _spec.POSITION_SCALE),
            round(header.max_position.latitude * _spec.POSITION_SCALE),
            header.center_zoom,
            round(header.center_position.longitude * _spec.POSITION_SCALE),
            round(header.center_position.latitude * _spec.POSITION_SCALE),
        )
    )
    assert _header.decode_header(buffer) == expected


def test_decode_header_too_short() -> None:
    assert _header.decode_header(memoryview(b"\x00" * 10)) == Err(
        _header.HeaderTooShortError(length=10)
    )
