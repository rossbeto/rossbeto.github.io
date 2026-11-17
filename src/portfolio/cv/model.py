"""The CV model: JSON Resume shape plus `x_` extensions (data/cv.yml). Pure, no I/O."""

import datetime as dt
import re
from typing import Annotated, Any, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

from portfolio.model import find_placeholders

YEAR_MONTH = re.compile(r"^(\d{4})-(0[1-9]|1[0-2])$")


def _year_month(value: str) -> str:
    if not YEAR_MONTH.match(value):
        raise ValueError(f"expected YYYY-MM, got {value!r}")
    return value


YearMonth = Annotated[str, AfterValidator(_year_month)]
NonEmpty = Annotated[str, Field(min_length=1)]


def month_label(value: str | None) -> str:
    """`2019-09` → `Sep 2019`; no end date → `Present`."""
    if value is None:
        return "Present"
    year, month = value.split("-")
    return f"{dt.date(int(year), int(month), 1):%b} {year}"


class Entry(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True, populate_by_name=True)


class Location(Entry):
    city: NonEmpty
    region: NonEmpty


class Profile(Entry):
    network: NonEmpty
    url: NonEmpty
    username: str | None = None
    icon: Annotated[str, Field(alias="x_icon")]


class Basics(Entry):
    name: NonEmpty
    label: NonEmpty
    tagline: Annotated[str | None, Field(alias="x_tagline")] = None
    image: NonEmpty
    image_alt: Annotated[str, Field(alias="x_image_alt", min_length=1)]
    location: Location
    summary: Annotated[list[NonEmpty], Field(min_length=1)]
    profiles: list[Profile]


def _docs_page(value: str) -> str:
    if value.startswith(("/", ".")) or not value.endswith(".md"):
        raise ValueError(f"expected a page path under docs/ like projects/x.md, got {value!r}")
    return value


class Capability(Entry):
    title: NonEmpty
    text: NonEmpty
    # A page under docs/, e.g. projects/tenantlab.md: the capability is shown in a personal lab
    # and gets a "lab" badge linking there (lab work is always labelled as lab work).
    proof: Annotated[str | None, AfterValidator(lambda v: v and _docs_page(v))] = None
    hidden: Annotated[bool, Field(alias="x_hidden")] = False


class Note(Entry):
    title: NonEmpty
    text: NonEmpty


class SkillGroup(Entry):
    name: NonEmpty
    keywords: Annotated[list[NonEmpty], Field(min_length=1)]
    earlier: Annotated[list[NonEmpty], Field(alias="x_earlier")] = []


class Work(Entry):
    name: NonEmpty
    position: NonEmpty
    location: NonEmpty
    start: Annotated[YearMonth, Field(alias="startDate")]
    end: Annotated[YearMonth | None, Field(alias="endDate")] = None
    summary: str | None = None
    highlights: Annotated[list[NonEmpty], Field(min_length=1)]
    hidden: Annotated[bool, Field(alias="x_hidden")] = False

    @model_validator(mode="after")
    def _ends_after_start(self) -> Self:
        if self.end is not None and self.end < self.start:
            raise ValueError(f"endDate {self.end} is before startDate {self.start}")
        return self

    @property
    def period(self) -> str:
        return f"{month_label(self.start)} – {month_label(self.end)}"


class Education(Entry):
    institution: NonEmpty
    area: str | None = None
    studyType: str | None = None  # JSON Resume key


class CV(Entry):
    basics: Basics
    capabilities: Annotated[list[Capability], Field(alias="x_capabilities")] = []
    recent: Annotated[list[Note], Field(alias="x_recent")] = []
    skills: list[SkillGroup] = []
    work_intro: Annotated[str | None, Field(alias="x_work_intro")] = None
    work: Annotated[list[Work], Field(min_length=1)]
    education: list[Education] = []

    @model_validator(mode="before")
    @classmethod
    def _no_placeholders(cls, data: Any) -> Any:
        # Checked on the raw data so the error names the YAML path (work[0].highlights[1]).
        gaps = list(find_placeholders(data))
        if gaps:
            raise ValueError("; ".join(gaps))
        return data
