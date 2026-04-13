from __future__ import annotations

from typing import Callable, TypeVar

from i2v.core.base import BasePipeline

T = TypeVar("T", bound=BasePipeline)


class _Registry:
    def __init__(self) -> None:
        self._models: dict[str, type[BasePipeline]] = {}

    def register(self, name: str) -> Callable[[type[T]], type[T]]:
        def deco(cls: type[T]) -> type[T]:
            if name in self._models:
                raise ValueError(f"pipeline '{name}' already registered")
            cls.name = name
            self._models[name] = cls
            return cls

        return deco

    def get(self, name: str) -> type[BasePipeline]:
        if name not in self._models:
            raise KeyError(f"unknown pipeline '{name}'. registered: {list(self._models)}")
        return self._models[name]

    def list(self) -> list[str]:
        return sorted(self._models)


registry = _Registry()
