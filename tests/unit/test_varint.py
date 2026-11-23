import pytest

from peat_mos.pmtiles import _varint
from peat_mos.pmtiles._datatypes import Err, Ok


@pytest.mark.parametrize(
    ("encoded", "start_index", "expected"),
    [
        pytest.param(b"\x00", 0, Ok(_varint.VarintRead(0, 1)), id="zero"),
        pytest.param(
            b"\x01", 0, Ok(_varint.VarintRead(1, 1)), id="one_byte_min_continuation"
        ),
        pytest.param(b"\x7f", 0, Ok(_varint.VarintRead(127, 1)), id="one_byte_max"),
        pytest.param(b"\x80\x01", 0, Ok(_varint.VarintRead(128, 2)), id="two_byte_min"),
        pytest.param(b"\xac\x02", 0, Ok(_varint.VarintRead(300, 2)), id="two_byte_mid"),
        pytest.param(
            b"\xff\xff\xff\xff\x0f",
            0,
            Ok(_varint.VarintRead(2**32 - 1, 5)),
            id="four_byte_u32_max",
        ),
        pytest.param(
            b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\x01",
            0,
            Ok(_varint.VarintRead(2**64 - 1, 10)),
            id="ten_byte_u64_max",
        ),
        pytest.param(
            b"\x00\xac\x02",
            1,
            Ok(_varint.VarintRead(300, 3)),
            id="start_index_mid_buffer",
        ),
        pytest.param(
            b"", 0, Err(_varint.UnterminatedVarintError(at_index=0)), id="empty_buffer"
        ),
        pytest.param(
            b"\x80\x80\x80",
            0,
            Err(_varint.UnterminatedVarintError(at_index=3)),
            id="unterminated_mid_buffer",
        ),
        pytest.param(
            b"\xff\xff\xff\xff\xff\xff\xff\xff\xff\x02",
            0,
            Err(_varint.VarintOverflowError(at_index=0)),
            id="overflow_tenth_byte_just_over",
        ),
    ],
)
def test_read_varint(encoded: bytes, start_index: int, expected: object) -> None:
    assert _varint.read_varint(memoryview(encoded), start_index) == expected


@pytest.mark.parametrize(
    ("encoded", "start_index", "count", "expected"),
    [
        pytest.param(
            b"\x00\xac\x02\x7f",
            0,
            3,
            Ok(_varint.VarintsRead((0, 300, 127), 4)),
            id="reads_sequential_values",
        ),
        pytest.param(
            b"\x01",
            0,
            0,
            Ok(_varint.VarintsRead((), 0)),
            id="zero_count_returns_empty_without_advancing",
        ),
        pytest.param(
            b"\x00\x80\x80\x80",
            0,
            2,
            Err(_varint.UnterminatedVarintError(at_index=4)),
            id="propagates_error_from_underlying_read",
        ),
    ],
)
def test_read_varints(
    encoded: bytes, start_index: int, count: int, expected: object
) -> None:
    assert _varint.read_varints(memoryview(encoded), start_index, count) == expected
