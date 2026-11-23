from dataclasses import dataclass
from typing import BinaryIO, assert_never

from peat_mos.pmtiles import _compression, _directory, _header, _spec, _tile_coordinate
from peat_mos.pmtiles._datatypes import Err, Error, Ok, Result

DEFAULT_MAX_DIRECTORY_DEPTH = 4


@dataclass(frozen=True, slots=True)
class InvalidHeaderError(Error): ...


@dataclass(frozen=True, slots=True)
class InvalidRootDirectoryError(Error): ...


@dataclass(frozen=True, slots=True)
class InvalidChildDirectoryError(Error):
    offset_from_leaf_directories: int
    length: int


@dataclass(frozen=True, slots=True)
class TileDataReadError(Error):
    offset_from_tile_data: int
    length: int


@dataclass(frozen=True, slots=True)
class InvalidTileCoordinateError(Error):
    z: int
    x: int
    y: int


@dataclass(frozen=True, slots=True)
class DirectoryDepthExceededError(Error):
    max_directory_depth: int


@dataclass(frozen=True, slots=True)
class FileReadError(Error):
    offset: int
    length: int


type OpenArchiveError = (
    InvalidHeaderError
    | _header.UnsupportedVersionError
    | _compression.UnsupportedCompressionError
    | InvalidRootDirectoryError
    | FileReadError
)

type ReadTileError = (
    InvalidTileCoordinateError
    | InvalidChildDirectoryError
    | _compression.UnsupportedCompressionError
    | DirectoryDepthExceededError
    | TileDataReadError
    | FileReadError
)


@dataclass(frozen=True, slots=True)
class _ShortReadError(Error):
    offset: int
    requested: int
    received: int


@dataclass(frozen=True, slots=True)
class _ReadFailedError(Error):
    offset: int
    length: int
    detail: str


type _ReadError = _ShortReadError | _ReadFailedError


@dataclass(frozen=True, slots=True)
class Archive:
    header: _spec.Header
    root_directory: _spec.Directory
    max_directory_depth: int


def _read_range_exact(
    file: BinaryIO, offset: int, length: int
) -> Result[memoryview, _ReadError]:
    try:
        file.seek(offset)
        data = file.read(length)
    except OSError as e:
        return Err(_ReadFailedError(offset, length, str(e)))
    if len(data) != length:
        return Err(_ShortReadError(offset, length, len(data)))
    return Ok(memoryview(data))


def read_tile(
    file: BinaryIO, archive: Archive, z: int, x: int, y: int
) -> Result[memoryview | None, ReadTileError]:
    if not _tile_coordinate.is_valid_tile_coordinate(z, x, y):
        return Err(InvalidTileCoordinateError(z, x, y))
    tile_id = _tile_coordinate.tile_coordinate_to_tile_id(z, x, y)

    directory = archive.root_directory
    for _ in range(archive.max_directory_depth):
        entry = _directory.search_directory(directory, tile_id)
        if entry is None:
            return Ok(None)

        if entry.run_length > 0:
            tile_offset = archive.header.tile_data_offset + entry.offset
            match _read_range_exact(file, tile_offset, entry.length):
                case Ok(tile_buffer):
                    return Ok(tile_buffer)
                case Err(error):
                    match error:
                        case _ShortReadError():
                            return Err(
                                TileDataReadError(
                                    entry.offset, entry.length, cause=error
                                )
                            )
                        case _ReadFailedError():
                            return Err(
                                FileReadError(tile_offset, entry.length, cause=error)
                            )
                        case _:
                            assert_never(error)

        child_offset = archive.header.leaf_directories_offset + entry.offset
        match _read_range_exact(file, child_offset, entry.length):
            case Ok(compressed_buffer):
                pass
            case Err(error):
                match error:
                    case _ShortReadError():
                        return Err(
                            InvalidChildDirectoryError(
                                entry.offset, entry.length, cause=error
                            )
                        )
                    case _ReadFailedError():
                        return Err(
                            FileReadError(child_offset, entry.length, cause=error)
                        )
                    case _:
                        assert_never(error)

        match _compression.decompress(
            compressed_buffer, archive.header.internal_compression
        ):
            case Ok(directory_buffer):
                pass
            case Err(error):
                match error:
                    case _compression.DecompressionFailedError():
                        return Err(
                            InvalidChildDirectoryError(
                                entry.offset, entry.length, cause=error
                            )
                        )
                    case _compression.UnsupportedCompressionError():
                        return Err(error)
                    case _:
                        assert_never(error)

        match _directory.decode_directory(directory_buffer):
            case Ok(child_directory):
                directory = child_directory
            case Err(error):
                match error:
                    case (
                        _directory.MalformedDirectoryError()
                        | _directory.EmptyDirectoryError()
                        | _directory.ZeroLengthDirectoryEntryError()
                        | _directory.ContiguousOffsetOnFirstDirectoryEntryError()
                    ):
                        return Err(
                            InvalidChildDirectoryError(
                                entry.offset, entry.length, cause=error
                            )
                        )
                    case _:
                        assert_never(error)

    return Err(DirectoryDepthExceededError(archive.max_directory_depth))


def open_archive(
    file: BinaryIO, max_directory_depth: int = DEFAULT_MAX_DIRECTORY_DEPTH
) -> Result[Archive, OpenArchiveError]:
    try:
        file.seek(0)
        header_buffer = memoryview(file.read(_spec.HEADER_LENGTH))
    except OSError as e:
        read_error = _ReadFailedError(0, _spec.HEADER_LENGTH, str(e))
        return Err(FileReadError(0, _spec.HEADER_LENGTH, cause=read_error))

    match _header.decode_header(header_buffer):
        case Ok(header):
            pass
        case Err(error):
            match error:
                case _header.UnsupportedVersionError():
                    return Err(error)
                case (
                    _header.HeaderTooShortError()
                    | _header.InvalidMagicNumberError()
                    | _header.InvalidClusteredValueError()
                    | _header.InvalidInternalCompressionError()
                    | _header.InvalidTileCompressionError()
                    | _header.InvalidTileTypeError()
                    | _header.MaxZoomBelowMinZoomError()
                    | _header.RootDirectoryOutsideInitialBytesError()
                ):
                    return Err(InvalidHeaderError(cause=error))
                case _:
                    assert_never(error)

    root_offset = header.root_directory_offset
    root_length = header.root_directory_length
    match _read_range_exact(file, root_offset, root_length):
        case Ok(root_directory_buffer):
            pass
        case Err(error):
            match error:
                case _ShortReadError():
                    return Err(InvalidRootDirectoryError(cause=error))
                case _ReadFailedError():
                    return Err(FileReadError(root_offset, root_length, cause=error))
                case _:
                    assert_never(error)

    match _compression.decompress(root_directory_buffer, header.internal_compression):
        case Ok(directory_buffer):
            pass
        case Err(error):
            match error:
                case _compression.UnsupportedCompressionError():
                    return Err(error)
                case _compression.DecompressionFailedError():
                    return Err(InvalidRootDirectoryError(cause=error))
                case _:
                    assert_never(error)

    match _directory.decode_directory(directory_buffer):
        case Ok(root_directory):
            pass
        case Err(error):
            match error:
                case (
                    _directory.MalformedDirectoryError()
                    | _directory.EmptyDirectoryError()
                    | _directory.ZeroLengthDirectoryEntryError()
                    | _directory.ContiguousOffsetOnFirstDirectoryEntryError()
                ):
                    return Err(InvalidRootDirectoryError(cause=error))
                case _:
                    assert_never(error)

    return Ok(
        Archive(
            header=header,
            root_directory=root_directory,
            max_directory_depth=max_directory_depth,
        )
    )
