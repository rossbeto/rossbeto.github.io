"""Validators shared by every content model. No I/O."""

PLACEHOLDER = "[X]"


def no_placeholder(value: str) -> str:
    """Refuse text that still holds a `[X]` gap: it must never reach the public site."""
    if PLACEHOLDER in value:
        raise ValueError(f"unresolved placeholder {PLACEHOLDER!r} in {value!r}")
    return value
