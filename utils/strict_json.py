"""JSON readers that reject ambiguous duplicate object keys."""

from __future__ import annotations

import json
from typing import IO, Any


class DuplicateJSONKeyError(ValueError):
    """Raised when a JSON object contains the same key more than once."""


def _reject_duplicate_keys(pairs: list[tuple[str, Any]]) -> dict[str, Any]:
    result = {}
    for key, value in pairs:
        if key in result:
            raise DuplicateJSONKeyError(f"Duplicate JSON object key: {key!r}")
        result[key] = value
    return result


def load_json_strict(file: IO[str]) -> Any:
    """Deserialize a JSON text stream and reject duplicate object keys."""
    return json.load(file, object_pairs_hook=_reject_duplicate_keys)


def loads_json_strict(text: str) -> Any:
    """Deserialize JSON text and reject duplicate object keys."""
    return json.loads(text, object_pairs_hook=_reject_duplicate_keys)
