"""Deterministic Markdown note renderer for an `AnalysisBundle`.

The renderer is intentionally minimal:

- It escapes any user-provided strings — no raw HTML, no Markdown injection
  from untrusted input.
- It produces a stable order over `sections`, `research`, and `tools`.
- The output is identical for identical input (no time, no random IDs).
"""

from __future__ import annotations

import html
from typing import Iterable

from .models import AnalysisBundle, Section, ToolResearch


def _esc(value: str) -> str:
    return html.escape(value, quote=False)


def _quote_block(text: str) -> str:
    return "\n".join(f"> {line}" if line else ">" for line in text.splitlines())


def _section_block(section: Section) -> str:
    return f"**{_esc(section.label)}** — {_esc(section.note)}\n{_quote_block(_esc(section.text))}"


def _research_block(research: Iterable[ToolResearch]) -> str:
    blocks = []
    for item in research:
        blocks.append(
            "\n".join(
                [
                    f"**{_esc(item.tool)}** — {_esc(item.one_liner)}",
                    f"  - How it works: {_esc(item.how_it_works)}",
                    f"  - Hook fact: {_esc(item.hook_fact)}",
                    f"  - Source: <{_esc(item.source_url)}>",
                ]
            )
        )
    return "\n\n".join(blocks)


def render_note(bundle: AnalysisBundle) -> str:
    """Render the Markdown note for one analysis bundle."""

    src = bundle.source
    a = bundle.analysis

    frontmatter_lines = [
        f"source_account: {_esc(src.username)}",
        f"source_url: {_esc(src.url)}",
        f"source_views: {int(src.views)}",
        f"source_likes: {int(src.likes)}",
        f"source_comments: {int(src.comments)}",
        f"relevance_score: {int(a.relevance_score)}",
        f"date_scraped: {_esc(src.scraped_at.isoformat())}",
        f"topic: \"{_esc(a.topic)}\"",
        f"tools: \"{', '.join(_esc(t) for t in a.tools)}\"",
        f"hook_style: {a.hook_style.value}",
    ]
    frontmatter = "---\n" + "\n".join(frontmatter_lines) + "\n---\n"

    sections = "\n\n".join(_section_block(s) for s in a.sections)
    research = _research_block(a.research)
    angle = _esc(a.angle_suggestion)

    body = "\n\n".join(
        [
            f"# {_esc(a.topic)}",
            "## Source\n\n"
            f"- **Account**: [@{_esc(src.username)}]({_esc(src.url)})\n"
            f"- **Views**: {int(src.views)} · **Likes**: {int(src.likes)} · **Comments**: {int(src.comments)}\n"
            f"- **Caption**: {_esc(src.caption[:280])}",
            "## Transcript (by section)\n\n" + sections,
            "## Research\n\n" + research,
            "## Production notes\n\n"
            f"- Hook style: {a.hook_style.value}\n"
            f"- Relevance score: {int(a.relevance_score)}/10\n"
            f"- Model: {_esc(bundle.model.provider)}/{_esc(bundle.model.model)}",
            f"**Angle suggestion**: {angle}",
        ]
    )

    return frontmatter + "\n" + body + "\n"


__all__ = ["render_note"]
