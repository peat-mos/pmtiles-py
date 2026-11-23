from dataclasses import dataclass

from peat_mos.pmtiles._datatypes import Err, Error, Ok, Result

_MAX_U64_VARINT_LENGTH = 10


@dataclass(frozen=True, slots=True)
class VarintRead:
    value: int
    next_index: int


@dataclass(frozen=True, slots=True)
class VarintsRead:
    values: tuple[int, ...]
    next_index: int


@dataclass(frozen=True, slots=True)
class UnterminatedVarintError(Error):
    at_index: int


@dataclass(frozen=True, slots=True)
class VarintOverflowError(Error):
    at_index: int


@dataclass(frozen=True, slots=True)
class VarintCountExceedsBufferError(Error):
    requested: int
    read: int
    at_index: int


type VarintError = UnterminatedVarintError | VarintOverflowError

type VarintsError = VarintError | VarintCountExceedsBufferError


def _find_varint_len(
    buffer: memoryview, start_index: int
) -> Result[int, UnterminatedVarintError]:
    for index in range(start_index, len(buffer)):
        if buffer[index] < 0x80:
            return Ok(index - start_index + 1)
    return Err(UnterminatedVarintError(at_index=len(buffer)))


def _varint_is_u64(buffer: memoryview) -> bool:
    return len(buffer) < _MAX_U64_VARINT_LENGTH or (
        len(buffer) == _MAX_U64_VARINT_LENGTH and buffer[-1] <= 0x01
    )


def _decode_varint(buffer: memoryview) -> int:
    value = 0
    for index, byte in enumerate(buffer):
        value |= (byte & 0x7F) << (7 * index)
    return value


def read_varint(
    buffer: memoryview, start_index: int
) -> Result[VarintRead, VarintError]:
    match _find_varint_len(buffer, start_index):
        case Err() as e:
            return e
        case Ok(varint_len):
            end_index = start_index + varint_len
            varint_bytes = buffer[start_index:end_index]
            if not _varint_is_u64(varint_bytes):
                return Err(VarintOverflowError(at_index=start_index))
            return Ok(
                VarintRead(value=_decode_varint(varint_bytes), next_index=end_index)
            )


def read_varints(
    buffer: memoryview, start_index: int, count: int
) -> Result[VarintsRead, VarintsError]:
    values: list[int] = []
    index = start_index
    for _ in range(count):
        match read_varint(buffer, index):
            case Err() as e:
                return e
            case Ok(VarintRead(value=value, next_index=next_index)):
                values.append(value)
                index = next_index
    return Ok(VarintsRead(values=tuple(values), next_index=index))
