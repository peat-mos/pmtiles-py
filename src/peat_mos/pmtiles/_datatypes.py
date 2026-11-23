from __future__ import annotations

from dataclasses import dataclass, field
from typing import Generic, TypeVar

T_co = TypeVar("T_co", covariant=True)


@dataclass(frozen=True, slots=True)
class Ok(Generic[T_co]):
    value: T_co


E_co = TypeVar("E_co", covariant=True)


@dataclass(frozen=True, slots=True)
class Err(Generic[E_co]):
    error: E_co


type Result[T, E] = Ok[T] | Err[E]


@dataclass(frozen=True)
class Error:
    cause: Error | None = field(default=None, kw_only=True)
