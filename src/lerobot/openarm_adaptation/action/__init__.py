"""Action contract preprocessing — D-34 P2."""

from .relstats_transform import (
    RelstatsTransformResult,
    transform_dataset_to_relative_chunk,
)

__all__ = ["transform_dataset_to_relative_chunk", "RelstatsTransformResult"]
