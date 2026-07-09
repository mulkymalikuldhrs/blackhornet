"""Pydantic v1/v2 compatibility helpers."""

import pydantic

_PYDANTIC_V1 = pydantic.__version__.startswith("1")


def model_dump(obj) -> dict:
    """Serialize a Pydantic model to a dict (JSON-safe in v2)."""
    if _PYDANTIC_V1:
        return obj.dict()
    return obj.model_dump(mode="json")


def model_validate(cls, data: dict):
    """Deserialize a dict into a Pydantic model."""
    if _PYDANTIC_V1:
        return cls.parse_obj(data)
    return cls.model_validate(data)
