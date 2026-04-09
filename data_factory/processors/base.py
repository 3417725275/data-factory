"""Processor abstract base class and registry."""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from data_factory.core.config import AppConfig
from data_factory.core.schema import FetchResult

PROCESSOR_REGISTRY: dict[str, type["Processor"]] = {}


class Processor(ABC):
    def __init_subclass__(cls, *, processor_name: str | None = None, **kwargs: Any):
        super().__init_subclass__(**kwargs)
        if processor_name is not None:
            PROCESSOR_REGISTRY[processor_name] = cls
            cls.processor_name = processor_name

    @abstractmethod
    def should_run(self, result: FetchResult, output_dir: Path) -> bool:
        """Check whether this processor needs to run."""

    @abstractmethod
    def process(self, result: FetchResult, output_dir: Path, config: AppConfig) -> None:
        """Execute processing, update files and meta.json."""
