"""Post front matter, validated against the review checklist (docs/blog/README.md). No I/O."""

import datetime as dt
import re
from typing import Annotated

from pydantic import AfterValidator, BaseModel, ConfigDict, Field

from portfolio.model import no_placeholder

Text = Annotated[str, AfterValidator(no_placeholder)]
SLUG = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")


class PostMeta(BaseModel):
    """Front matter of `docs/blog/posts/*.md` (the keys Material's blog plugin reads, plus ours)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    date: dt.date
    slug: Annotated[str, Field(pattern=SLUG.pattern)]
    title: Annotated[Text, Field(min_length=1, max_length=60)]
    description: Annotated[Text, Field(min_length=1, max_length=155)]
    authors: Annotated[list[str], Field(min_length=1)]
    categories: Annotated[list[str], Field(min_length=1, max_length=2)]
    tags: Annotated[list[str], Field(min_length=2, max_length=5)]
    draft: bool = False
    readtime: int | None = None


class Post(BaseModel):
    """A post as the generator sees it: where it lives (relative to docs/) and its front matter."""

    model_config = ConfigDict(frozen=True)

    src: str  # e.g. "blog/posts/the-301-that-leaked-a-tenant.md"
    meta: PostMeta
