"""Field mapping and a deliberately small set of transforms.

A mapping is a list of rules: take a (possibly nested) source field, optionally
transform it, and write it to a (possibly nested) target field. There is no
expression language — each transform is one named, tested function.
"""

from app.transforms.mapping import MappingRule, TransformError, apply_mapping, preview_mapping
from app.transforms.functions import TRANSFORMS

__all__ = ["TRANSFORMS", "MappingRule", "TransformError", "apply_mapping", "preview_mapping"]
