"""Adapter: read and validate data/cv.yml (the only CV module touching files or YAML)."""

from pathlib import Path

import yaml
from pydantic import ValidationError

from portfolio.cv.model import CV


class CVError(ValueError):
    """data/cv.yml is unreadable or invalid; the message lists every problem with its path."""


def _location(loc: tuple[int | str, ...]) -> str:
    out = ""
    for part in loc:
        out += f"[{part}]" if isinstance(part, int) else (f".{part}" if out else str(part))
    return out or "<root>"


def load_cv(path: Path) -> CV:
    try:
        data = yaml.safe_load(path.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as exc:
        raise CVError(f"{path}: {exc}") from exc
    try:
        return CV.model_validate(data)
    except ValidationError as exc:
        problems = [f"  {_location(e['loc'])}: {e['msg']}" for e in exc.errors()]
        raise CVError(f"{path}: {len(problems)} problem(s)\n" + "\n".join(problems)) from None
