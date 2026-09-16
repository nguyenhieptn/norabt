from __future__ import annotations

from typing import Optional

import numpy as np


class BootstrapSampler:
    """Deterministic-capable IID and moving-block bootstrap sampler."""

    @staticmethod
    def iid_resample(
        returns: np.ndarray,
        n_samples: int,
        seed: Optional[int] = None,
        rng: Optional[np.random.Generator] = None,
    ) -> np.ndarray:
        if n_samples < 0:
            raise ValueError("n_samples must be non-negative")
        if len(returns) == 0:
            return np.zeros(n_samples, dtype=np.float64)
        generator = rng or np.random.default_rng(seed)
        indices = generator.integers(0, len(returns), size=n_samples)
        return returns[indices]

    @staticmethod
    def block_resample(
        returns: np.ndarray,
        n_samples: int,
        block_size: int = 4,
        seed: Optional[int] = None,
        rng: Optional[np.random.Generator] = None,
    ) -> np.ndarray:
        if n_samples < 0:
            raise ValueError("n_samples must be non-negative")
        if block_size <= 0:
            raise ValueError("block_size must be positive")
        generator = rng or np.random.default_rng(seed)
        count = len(returns)
        if count <= block_size:
            return BootstrapSampler.iid_resample(returns, n_samples, rng=generator)
        block_count = int(np.ceil(n_samples / block_size))
        starts = generator.integers(0, count - block_size + 1, size=block_count)
        indices = (starts[:, None] + np.arange(block_size)).reshape(-1)[:n_samples]
        return returns[indices]
