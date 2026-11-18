"""Project front matter (`docs/projects/<slug>.md`). Pure, no I/O."""

import re
from enum import StrEnum
from typing import Annotated, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from portfolio.model import no_placeholder

Text = Annotated[str, AfterValidator(no_placeholder)]


class Stage(StrEnum):
    ACTIVE = "active"
    DONE = "done"
    ARCHIVED = "archived"


class Kind(StrEnum):
    LAB = "lab"
    WORK_PUBLIC = "work-public"
    OSS = "oss"


KIND_LABEL = {Kind.LAB: "Personal lab", Kind.WORK_PUBLIC: "Work (public)", Kind.OSS: "Open source"}


def _asset(value: str) -> str:
    if not value.startswith("assets/") or ".." in value:
        raise ValueError(f"expected a path under docs/assets/, got {value!r}")
    return value


class ProjectMeta(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    title: Annotated[Text, Field(min_length=1, max_length=60)]
    summary: Annotated[Text, Field(min_length=1, max_length=160)]
    stage: Stage
    kind: Kind
    repo: Annotated[str, Field(pattern=r"^https://github\.com/[\w.-]+/[\w.-]+$")]
    # False until the repository is public: the site then never links to it (tested).
    repo_public: bool = False
    image: Annotated[str | None, AfterValidator(lambda v: v and _asset(v))] = None
    image_alt: Text | None = None
    tags: Annotated[list[str], Field(min_length=1, max_length=8)]
    featured: bool = False
    order: int = 100
    hide: list[str] = []  # Material's own front-matter key (e.g. [toc])

    @model_validator(mode="after")
    def _image_needs_alt(self) -> Self:
        if self.image and not self.image_alt:
            raise ValueError("image_alt is required when image is set")
        return self


class Project(BaseModel):
    model_config = ConfigDict(frozen=True)

    src: str  # relative to docs/, e.g. "projects/tenantlab.md"
    meta: ProjectMeta


# Synced projects (Phase 006): data/projects.yml lists public repos whose `docs/portfolio-card.md`
# becomes the project page, pinned to a commit.

SHA = r"^[0-9a-f]{40}$"
REPO = r"^[\w.-]+/[\w.-]+$"


def _repo_path(value: str) -> str:
    """A file inside the repo: relative, no `..`, plain characters."""
    if not re.fullmatch(r"[\w./-]+", value) or value.startswith("/") or ".." in value:
        raise ValueError(f"expected a file path inside the repository, got {value!r}")
    return value


RepoPath = Annotated[str, AfterValidator(_repo_path)]


class SourceMeta(BaseModel):
    """Site-only fields that the card does not carry (the card holds title and text)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    summary: Annotated[Text, Field(min_length=1, max_length=160)]
    stage: Stage
    kind: Kind
    image: Annotated[str | None, AfterValidator(lambda v: v and _asset(v))] = None
    image_alt: Text | None = None
    tags: Annotated[list[str], Field(min_length=1, max_length=8)]
    featured: bool = False
    order: int = 100


class ProjectSource(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    slug: Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9-]*$")]
    repo: Annotated[str, Field(pattern=REPO)]  # owner/name, public
    ref: Annotated[str, Field(pattern=SHA)]  # a full commit SHA: reproducible and reviewed
    card: RepoPath = "docs/portfolio-card.md"
    media: list[RepoPath] = []
    meta: SourceMeta

    @model_validator(mode="after")
    def _media_names_are_unique(self) -> Self:
        names = [m.rsplit("/", 1)[-1] for m in self.media]
        if len(set(names)) != len(names):
            raise ValueError(f"two media files share a file name: {self.media}")
        return self

    @property
    def page(self) -> str:
        """The generated page, relative to docs/."""
        return f"projects/{self.slug}.md"

    def asset(self, repo_path: str) -> str:
        """Where a media file is copied, relative to docs/."""
        return f"assets/projects/{self.slug}/{repo_path.rsplit('/', 1)[-1]}"
