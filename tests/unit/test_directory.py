import pytest

from peat_mos.pmtiles import _directory, _spec, _varint
from peat_mos.pmtiles._datatypes import Err, Ok


def _encode_varint(value: int) -> bytes:
    out = bytearray()
    while True:
        byte = value & 0x7F
        value >>= 7
        if value:
            out.append(byte | 0x80)
        else:
            out.append(byte)
            return bytes(out)


@pytest.mark.parametrize(
    ("entries", "expected"),
    [
        pytest.param(
            (_spec.DirectoryEntry(tile_id=5, offset=50, length=100, run_length=1),),
            Ok((_spec.DirectoryEntry(tile_id=5, offset=50, length=100, run_length=1),)),
            id="single_entry",
        ),
        pytest.param(
            (
                _spec.DirectoryEntry(tile_id=5, offset=50, length=100, run_length=1),
                _spec.DirectoryEntry(tile_id=8, offset=150, length=50, run_length=2),
            ),
            Ok(
                (
                    _spec.DirectoryEntry(
                        tile_id=5, offset=50, length=100, run_length=1
                    ),
                    _spec.DirectoryEntry(
                        tile_id=8, offset=150, length=50, run_length=2
                    ),
                )
            ),
            id="contiguous_offset_follows_prior_entry",
        ),
        pytest.param((), Err(_directory.EmptyDirectoryError()), id="empty_directory"),
        pytest.param(
            (_spec.DirectoryEntry(tile_id=5, offset=50, length=0, run_length=1),),
            Err(_directory.ZeroLengthDirectoryEntryError()),
            id="zero_length_entry",
        ),
    ],
)
def test_decode_directory(
    entries: tuple[_spec.DirectoryEntry, ...], expected: object
) -> None:
    tile_id_deltas: list[int] = []
    run_lengths: list[int] = []
    lengths: list[int] = []
    encoded_offsets: list[int] = []

    for index, entry in enumerate(entries):
        if index == 0:
            tile_id_deltas.append(entry.tile_id)
            encoded_offsets.append(entry.offset + 1)
        else:
            prior = entries[index - 1]
            tile_id_deltas.append(entry.tile_id - prior.tile_id)
            is_contiguous = entry.offset == prior.offset + prior.length
            encoded_offsets.append(0 if is_contiguous else entry.offset + 1)
        run_lengths.append(entry.run_length)
        lengths.append(entry.length)

    columns = (tile_id_deltas, run_lengths, lengths, encoded_offsets)
    buffer = b"".join(
        _encode_varint(v) for v in (len(entries), *(v for col in columns for v in col))
    )
    assert _directory.decode_directory(memoryview(buffer)) == expected


def test_decode_directory_contiguous_offset_on_first_entry() -> None:
    # entry_count=1, tile_id_delta=5, run_length=1, length=100, encoded_offset=0:
    # the contiguous-offset sentinel is invalid with no prior entry to chain from.
    buffer = b"".join(_encode_varint(v) for v in (1, 5, 1, 100, 0))
    assert _directory.decode_directory(memoryview(buffer)) == Err(
        _directory.ContiguousOffsetOnFirstDirectoryEntryError()
    )


def test_decode_directory_malformed_varint_is_wrapped() -> None:
    # declares 1 entry but has no varints describing it
    buffer = memoryview(_encode_varint(1))
    match _directory.decode_directory(buffer):
        case Err(error):
            assert isinstance(error, _directory.MalformedDirectoryError)
            assert isinstance(error.cause, _varint.UnterminatedVarintError)
        case other:
            pytest.fail(f"expected Err, got {other!r}")


@pytest.mark.parametrize(
    ("directory", "tile_id", "expected"),
    [
        pytest.param(
            (_spec.DirectoryEntry(tile_id=5, offset=0, length=10, run_length=3),),
            5,
            _spec.DirectoryEntry(tile_id=5, offset=0, length=10, run_length=3),
            id="single_entry_matches_start_of_run",
        ),
        pytest.param(
            (_spec.DirectoryEntry(tile_id=5, offset=0, length=10, run_length=3),),
            7,
            _spec.DirectoryEntry(tile_id=5, offset=0, length=10, run_length=3),
            id="single_entry_matches_end_of_run",
        ),
        pytest.param(
            (_spec.DirectoryEntry(tile_id=5, offset=0, length=10, run_length=3),),
            8,
            None,
            id="single_entry_tile_id_past_end_of_run_returns_none",
        ),
        pytest.param(
            (_spec.DirectoryEntry(tile_id=5, offset=0, length=10, run_length=3),),
            4,
            None,
            id="single_entry_tile_id_before_start_returns_none",
        ),
        pytest.param(
            (_spec.DirectoryEntry(tile_id=5, offset=0, length=10, run_length=0),),
            5,
            _spec.DirectoryEntry(tile_id=5, offset=0, length=10, run_length=0),
            id="leaf_entry_matches_at_its_own_tile_id",
        ),
        pytest.param(
            (_spec.DirectoryEntry(tile_id=5, offset=0, length=10, run_length=0),),
            9999,
            _spec.DirectoryEntry(tile_id=5, offset=0, length=10, run_length=0),
            id="leaf_entry_matches_far_past_its_tile_id",
        ),
        pytest.param(
            (
                _spec.DirectoryEntry(tile_id=0, offset=0, length=10, run_length=3),
                _spec.DirectoryEntry(tile_id=10, offset=30, length=5, run_length=2),
            ),
            10,
            _spec.DirectoryEntry(tile_id=10, offset=30, length=5, run_length=2),
            id="tile_id_at_start_of_second_entry_selects_second_entry",
        ),
        pytest.param(
            (
                _spec.DirectoryEntry(tile_id=0, offset=0, length=10, run_length=3),
                _spec.DirectoryEntry(tile_id=10, offset=30, length=5, run_length=2),
            ),
            9,
            None,
            id="tile_id_in_gap_between_two_entries_returns_none",
        ),
        pytest.param(
            (_spec.DirectoryEntry(tile_id=5, offset=0, length=10, run_length=3),),
            0,
            None,
            id="tile_id_before_first_entry_returns_none",
        ),
        pytest.param((), 0, None, id="empty_directory_returns_none"),
    ],
)
def test_search_directory(
    directory: _spec.Directory,
    tile_id: int,
    expected: _spec.DirectoryEntry | None,
) -> None:
    assert _directory.search_directory(directory, tile_id) == expected
