"""Project front matter (`docs/projects/<slug>.md`). Pure, no I/O."""

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
