from bisect import bisect_right
from dataclasses import dataclass

from peat_mos.pmtiles import _spec, _varint
from peat_mos.pmtiles._datatypes import Err, Error, Ok, Result


@dataclass(frozen=True)
class MalformedDirectoryError(Error): ...


@dataclass(frozen=True)
class EmptyDirectoryError(Error): ...


@dataclass(frozen=True)
class ZeroLengthDirectoryEntryError(Error): ...


@dataclass(frozen=True)
class ContiguousOffsetOnFirstDirectoryEntryError(Error): ...


type DirectoryError = (
    MalformedDirectoryError
    | EmptyDirectoryError
    | ZeroLengthDirectoryEntryError
    | ContiguousOffsetOnFirstDirectoryEntryError
)


def decode_directory(buffer: memoryview) -> Result[_spec.Directory, DirectoryError]:
    match _varint.read_varint(buffer, 0):
        case Err(error=error):
            return Err(MalformedDirectoryError(cause=error))
        case Ok(_varint.VarintRead(value=entry_count, next_index=index)):
            pass

    if entry_count == 0:
        return Err(EmptyDirectoryError())

    match _varint.read_varints(buffer, index, entry_count):
        case Err(error=error):
            return Err(MalformedDirectoryError(cause=error))
        case Ok(_varint.VarintsRead(values=tile_id_deltas, next_index=index)):
            pass
    match _varint.read_varints(buffer, index, entry_count):
        case Err(error=error):
            return Err(MalformedDirectoryError(cause=error))
        case Ok(_varint.VarintsRead(values=run_lengths, next_index=index)):
            pass
    match _varint.read_varints(buffer, index, entry_count):
        case Err(error=error):
            return Err(MalformedDirectoryError(cause=error))
        case Ok(_varint.VarintsRead(values=lengths, next_index=index)):
            pass
    match _varint.read_varints(buffer, index, entry_count):
        case Err(error=error):
            return Err(MalformedDirectoryError(cause=error))
        case Ok(_varint.VarintsRead(values=encoded_offsets, next_index=index)):
            pass

    entries: list[_spec.DirectoryEntry] = []

    for tile_id_delta, run_length, length, encoded_offset in zip(
        tile_id_deltas, run_lengths, lengths, encoded_offsets, strict=True
    ):
        if length == 0:
            return Err(ZeroLengthDirectoryEntryError())

        if len(entries) == 0:
            tile_id = tile_id_delta
        else:
            tile_id = entries[-1].tile_id + tile_id_delta

        if encoded_offset == 0:
            if len(entries) == 0:
                return Err(ContiguousOffsetOnFirstDirectoryEntryError())
            else:
                offset = entries[-1].offset + entries[-1].length
        else:
            offset = encoded_offset - 1

        entries.append(
            _spec.DirectoryEntry(
                tile_id=tile_id,
                offset=offset,
                length=length,
                run_length=run_length,
            )
        )

    return Ok(tuple(entries))


def search_directory(
    directory: _spec.Directory, tile_id: int
) -> _spec.DirectoryEntry | None:
    index = bisect_right(directory, tile_id, key=lambda entry: entry.tile_id) - 1
    if index < 0:
        return None
    entry = directory[index]
    if tile_id < entry.tile_id + entry.run_length or entry.run_length == 0:
        return entry
    return None
