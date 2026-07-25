"""Tests for the deterministic Markdown note renderer."""

from __future__ import annotations

from pipeline.models import (
    AnalysisBundle,
    AnalysisSection,
    HookStyle,
    ModelMetadata,
    ReelInput,
    Section,
    ToolResearch,
)
from pipeline.notes import render_note


def _bundle(**analysis_overrides) -> AnalysisBundle:
    analysis = AnalysisSection(
        relevance_score=8,
        verdict=True,
        topic="On-niche topic",
        tools=["tool1"],
        hook_style=HookStyle.problem_promise,
        reasoning="Direct match.",
        sections=[
            Section(label="Hook", text="the opening line", note="opens with context"),
            Section(label="Beat 1", text="step one happens", note="step 1 — setup"),
            Section(label="CTA", text="follow for more", note="FOMO close"),
        ],
        research=[
            ToolResearch(
                tool="tool1",
                one_liner="a tool",
                how_it_works="does x",
                hook_fact="fast fact",
                source_url="https://example.com/tool1",
            )
        ],
        angle_suggestion="A different angle.",
        **analysis_overrides,
    )
    source = ReelInput(
        shortcode="abc123def",
        username="test_account",
        url="https://www.instagram.com/reel/abc123def/",
        views=1000,
        likes=50,
        comments=5,
        caption="caption",
        transcript="the opening line step one happens follow for more",
        scraped_at="2026-07-24T10:00:00+08:00",
    )
    model = ModelMetadata(
        provider="minimax",
        model="MiniMax-M3",
        analyzed_at="2026-07-24T10:30:00+08:00",
    )
    return AnalysisBundle(
        niche="strength training for busy professionals over 30",
        source=source,
        analysis=analysis,
        model=model,
    )


def test_render_note_includes_frontmatter() -> None:
    md = render_note(_bundle())
    assert "source_account: test_account" in md
    assert "source_url: https://www.instagram.com/reel/abc123def/" in md
    assert "relevance_score: 8" in md
    assert "hook_style: problem-promise" in md
    assert "topic: \"On-niche topic\"" in md


def test_render_note_includes_section_quote_blocks() -> None:
    md = render_note(_bundle())
    assert "**Hook** — opens with context" in md
    assert "> the opening line" in md
    assert "**Beat 1** — step 1 — setup" in md
    assert "**CTA** — FOMO close" in md
    assert "> follow for more" in md


def test_render_note_escapes_user_provided_strings() -> None:
    """No raw HTML should be emitted and special characters should be escaped."""

    base = _bundle()
    bundle = base.model_copy(
        deep=True,
        update={
            "analysis": base.analysis.model_copy(
                update={
                    "topic": "<script>alert(1)</script>",
                    "angle_suggestion": "A & B > C",
                    "reasoning": "contains *stars* and _underscores_",
                }
            )
        },
    )
    md = render_note(bundle)
    assert "<script>" not in md
    assert "&lt;script&gt;" in md
    assert "A &amp; B" in md


def test_render_note_is_deterministic() -> None:
    bundle = _bundle()
    a = render_note(bundle)
    b = render_note(bundle)
    assert a == b


def test_render_note_includes_research_block() -> None:
    md = render_note(_bundle())
    assert "**tool1** — a tool" in md
    assert "https://example.com/tool1" in md
