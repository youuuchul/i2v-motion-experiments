from __future__ import annotations

from abc import ABC, abstractmethod

from i2v.core.types import GenerationRequest, GenerationResult


class BasePipeline(ABC):
    """Common interface every i2v model adapter implements.

    Keep this surface small — it's the contract across teammates' model PRs.
    """

    name: str

    @abstractmethod
    def load(self) -> None: ...

    @abstractmethod
    def generate(self, request: GenerationRequest) -> GenerationResult: ...

    def unload(self) -> None:
        """Optional: free GPU memory."""
