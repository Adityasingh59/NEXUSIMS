"""NEXUS IMS — Attribute validation against item_type.attribute_schema (Block 1.2)."""
from decimal import Decimal
from typing import Any

# Schema field types: text, number, date, boolean, enum
VALID_TYPES = {"text", "number", "date", "boolean", "enum"}


class AttributeValidationError(Exception):
    """Raised when attributes fail validation against schema."""

    def __init__(self, message: str, field_errors: dict[str, str] | None = None):
        self.message = message
        self.field_errors = field_errors or {}
        super().__init__(message)


def _coerce_value(val: Any, field_type: str, options: list[str] | None) -> Any:
    """Coerce input to expected type."""
    if val is None:
        return None
    if field_type == "text":
        return str(val) if not isinstance(val, str) else val
    if field_type == "number":
        if isinstance(val, (int, float, Decimal)):
            return Decimal(str(val))
        if isinstance(val, str):
            try:
                return Decimal(val)
            except Exception:
                raise AttributeValidationError(f"Invalid number: {val}")
        raise AttributeValidationError(f"Cannot convert to number: {val}")
    if field_type == "date":
        return str(val)  # Store as ISO string; caller can validate format
    if field_type == "boolean":
        if isinstance(val, bool):
            return val
        if isinstance(val, str):
            return val.lower() in ("true", "1", "yes")
        return bool(val)
    if field_type == "enum":
        s = str(val)
        if options and s not in options:
            raise AttributeValidationError(f"Value must be one of {options}")
        return s
    return val


def validate_attributes(attributes: dict, attribute_schema: list[dict]) -> dict:
    """
    Validate attributes against item_type.attribute_schema.
    Schema: [{name, type, required, options?}]
    Returns validated/coerced attributes. Raises AttributeValidationError on failure.
    """
    field_errors: dict[str, str] = {}
    result: dict[str, Any] = {}

    for field_def in attribute_schema:
        name = field_def.get("name")
        if not name:
            continue
        field_type = field_def.get("type", "text")
        required = field_def.get("required", False)
        options = field_def.get("options")

        if field_type not in VALID_TYPES:
            field_errors[name] = f"Invalid schema type: {field_type}"
            continue

        val = attributes.get(name)
        if val is None or (isinstance(val, str) and val.strip() == ""):
            if required:
                field_errors[name] = "Required field"
            continue

        try:
            result[name] = _coerce_value(val, field_type, options)
        except AttributeValidationError as e:
            field_errors[name] = e.message

    if field_errors:
        raise AttributeValidationError("Attribute validation failed", field_errors)

    return result
