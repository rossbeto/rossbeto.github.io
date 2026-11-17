from pathlib import Path

import pytest
from check_links import anchors, main, problems, slug


@pytest.mark.parametrize(
    ("heading", "anchor"),
    [
        ("Quick start (Docker)", "quick-start-docker"),
        ("3.7 Local deploy: `tlbuilder`", "37-local-deploy-tlbuilder"),
        ("What this demonstrates", "what-this-demonstrates"),
        ("snake_case_name", "snake_case_name"),
    ],
)
def test_slug_matches_github(heading: str, anchor: str) -> None:
    assert slug(heading) == anchor


def test_duplicate_headings_get_numbered_anchors() -> None:
    assert anchors("# A\n## A\n```\n# not a heading\n```\n") == {"a", "a-1"}


def test_problems(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir()
    (tmp_path / "docs" / "arch.md").write_text("# Arch\n## Request lifecycle\n")
    readme = tmp_path / "README.md"
    readme.write_text(
        "[ok](docs/arch.md) [ok](docs/arch.md#request-lifecycle) [web](https://x.test/nope)\n"
        "[gone](docs/gone.md) [bad anchor](docs/arch.md#nope) [self](#top)\n"
        "![gif](docs/media/demo.gif)\n"
        "```\n[in code](not/checked.md)\n```\n# Top\n"
    )
    assert problems(readme) == [
        f"{readme}:2: missing docs/gone.md",
        f"{readme}:2: no heading #nope in arch.md",
        f"{readme}:3: missing docs/media/demo.gif",
    ]
    assert main([str(tmp_path / "docs")]) == 0
    assert main([str(readme)]) == 1
