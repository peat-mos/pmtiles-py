import gzip
import zlib
from dataclasses import dataclass

from peat_mos.pmtiles import _spec
from peat_mos.pmtiles._datatypes import Err, Error, Ok, Result


@dataclass(frozen=True, slots=True)
class UnsupportedCompressionError(Error):
    compression: _spec.Compression


@dataclass(frozen=True, slots=True)
class DecompressionFailedError(Error):
    compression: _spec.Compression
    detail: str


def _decompress_gzip(data: memoryview) -> Result[memoryview, DecompressionFailedError]:
    try:
        return Ok(memoryview(gzip.decompress(data)))
    except (gzip.BadGzipFile, zlib.error, EOFError) as e:
        return Err(DecompressionFailedError(_spec.Compression.GZIP, str(e)))


def decompress(
    data: memoryview, compression: _spec.Compression
) -> Result[memoryview, DecompressionFailedError | UnsupportedCompressionError]:
    match compression:
        case _spec.Compression.NONE:
            return Ok(data)
        case _spec.Compression.GZIP:
            return _decompress_gzip(data)
        case (
            _spec.Compression.UNKNOWN
            | _spec.Compression.BROTLI
            | _spec.Compression.ZSTD
        ):
            return Err(UnsupportedCompressionError(compression))
