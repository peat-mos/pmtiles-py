from typing import BinaryIO, assert_never

from peat_mos.pmtiles import _reader as reader
from peat_mos.pmtiles._compression import UnsupportedCompressionError
from peat_mos.pmtiles._datatypes import Err, Ok
from peat_mos.pmtiles._header import UnsupportedVersionError
from peat_mos.pmtiles._spec import Header


class PMTilesError(Exception): ...


class InvalidArchiveError(PMTilesError): ...


class UnsupportedArchiveError(PMTilesError): ...


class InvalidTileCoordinateError(PMTilesError, ValueError): ...


class ArchiveReadError(PMTilesError, OSError): ...


class PMTiles:
    def __init__(
        self,
        file: BinaryIO,
        max_directory_depth: int = reader.DEFAULT_MAX_DIRECTORY_DEPTH,
    ) -> None:
        self._file = file
        match reader.open_archive(file, max_directory_depth):
            case Ok(archive):
                self._archive = archive
                return
            case Err(error):
                pass
        match error:
            case reader.InvalidHeaderError():
                raise InvalidArchiveError(f"invalid header: {error}")
            case UnsupportedCompressionError():
                raise UnsupportedArchiveError(
                    f"unsupported compression: {error.compression.name.lower()}"
                )
            case UnsupportedVersionError():
                raise UnsupportedArchiveError(
                    f"unsupported PMTiles version: {error.version}"
                )
            case reader.InvalidRootDirectoryError():
                raise InvalidArchiveError(f"invalid root directory: {error}")
            case reader.FileReadError():
                raise ArchiveReadError(f"could not read the file: {error}")
            case _:
                assert_never(error)

    @property
    def closed(self) -> bool:
        return self._file.closed

    @property
    def header(self) -> Header:
        return self._archive.header

    def get_tile(self, z: int, x: int, y: int) -> bytes | None:
        if self.closed:
            raise ValueError("I/O operation on closed archive")
        match reader.read_tile(self._file, self._archive, z, x, y):
            case Ok(tile):
                return None if tile is None else bytes(tile)
            case Err(error):
                pass
        tile_name = f"{z}/{x}/{y}"
        match error:
            case reader.InvalidTileCoordinateError():
                raise InvalidTileCoordinateError(f"tile {tile_name} does not exist")
            case reader.InvalidChildDirectoryError():
                raise InvalidArchiveError(
                    f"invalid directory for tile {tile_name}: {error}"
                )
            case reader.DirectoryDepthExceededError():
                raise InvalidArchiveError(
                    f"directories for tile {tile_name} are nested deeper than "
                    f"{error.max_directory_depth} levels"
                )
            case reader.TileDataReadError():
                raise InvalidArchiveError(f"could not read tile {tile_name}: {error}")
            case UnsupportedCompressionError():
                raise UnsupportedArchiveError(
                    f"unsupported compression: {error.compression.name.lower()}"
                )
            case reader.FileReadError():
                raise ArchiveReadError(
                    f"could not read the file for tile {tile_name}: {error}"
                )
            case _:
                assert_never(error)
