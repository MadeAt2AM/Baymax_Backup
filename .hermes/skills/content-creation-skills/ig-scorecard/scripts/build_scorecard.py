#!/usr/bin/env python3
"""
Instagram Scorecard Builder
Takes a JSON file of post data and produces a professionally formatted .xlsx
with 5 tabs: Full Scorecard, Winners Analysis, Losers Analysis, Key Takeaways,
and Content Strategy (actionable recommendations based on content context).

Usage:
    python build_scorecard.py <input.json> <output.xlsx>

Input JSON format:
{
  "username": "someuser",
  "posts": [
    {
      "post_num": 1,
      "date": "Feb 21, 2026",
      "type": "Reel",
      "topic": "AI Content Strategy",
      "caption_preview": "Most people overthink content strategy...",
      "full_caption": "Full caption text here...",
      "visual_description": "Talking head with text overlay showing '5 Steps'",
      "likes": 272,
      "comments": 149,
      "saves": 231,
      "shares": 91,
      "views": 6306,
      "reach": 3684
    }
  ]
}
"""

import json
import sys
import os
import textwrap
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter


def load_data(path):
    with open(path, "r") as f:
        return json.load(f)


def calc_metrics(posts):
    """Calculate engagement totals and rates, then rank."""
    for p in posts:
        likes = p.get("likes", 0) or 0
        comments = p.get("comments", 0) or 0
        saves = p.get("saves", 0) or 0
        shares = p.get("shares", 0) or 0
        views = p.get("views", 0) or 0
        reach = p.get("reach", 0) or 0

        p["total_eng"] = likes + comments + saves + shares
        p["eng_rate_reach"] = (p["total_eng"] / reach * 100) if reach > 0 else 0
        p["eng_rate_views"] = (p["total_eng"] / views * 100) if views > 0 else 0

    # Sort by engagement rate (reach-based primary, views-based fallback)
    sorted_posts = sorted(
        posts,
        key=lambda x: (x["eng_rate_reach"] if x["eng_rate_reach"] > 0 else x["eng_rate_views"]),
        reverse=True,
    )

    # Assign ranks and status labels
    n = len(sorted_posts)
    if n >= 10:
        win_cutoff, lose_cutoff = 3, n - 3
    elif n >= 6:
        win_cutoff, lose_cutoff = 2, n - 2
    else:
        win_cutoff, lose_cutoff = 1, max(n - 1, 1)

    for i, p in enumerate(sorted_posts):
        p["rank"] = i + 1
        if i < win_cutoff:
            p["status"] = "\U0001f3c6 WINNER"
        elif i >= lose_cutoff:
            p["status"] = "\U0001f53b LOSER"
        else:
            p["status"] = "\u2796 AVERAGE"

    return sorted_posts


# ── Styles ──────────────────────────────────────────────────────────────
HEADER_FONT = Font(bold=True, color="FFFFFF", size=11, name="Arial")
HEADER_FILL = PatternFill("solid", fgColor="2C3E50")
WINNER_FILL = PatternFill("solid", fgColor="27AE60")
LOSER_FILL = PatternFill("solid", fgColor="E74C3C")
AVG_FILL = PatternFill("solid", fgColor="95A5A6")
WHITE_BOLD = Font(bold=True, color="FFFFFF", name="Arial")
DATA_FONT = Font(name="Arial", size=10)
BOLD_FONT = Font(bold=True, name="Arial", size=10)
TITLE_FONT = Font(bold=True, name="Arial", size=14, color="2C3E50")
SUBTITLE_FONT = Font(bold=True, name="Arial", size=12, color="2C3E50")
THIN_BORDER = Border(
    left=Side(style="thin", color="D5D8DC"),
    right=Side(style="thin", color="D5D8DC"),
    top=Side(style="thin", color="D5D8DC"),
    bottom=Side(style="thin", color="D5D8DC"),
)
GREEN_BG = PatternFill("solid", fgColor="E8F8F5")
RED_BG = PatternFill("solid", fgColor="FDEDEC")
YELLOW_BG = PatternFill("solid", fgColor="FEF9E7")
BLUE_BG = PatternFill("solid", fgColor="EBF5FB")
STRATEGY_HEADER_FILL = PatternFill("solid", fgColor="1A5276")
STRATEGY_HEADER_FONT = Font(bold=True, color="FFFFFF", size=12, name="Arial")


def style_header(ws, row, cols):
    for col in range(1, cols + 1):
        c = ws.cell(row=row, column=col)
        c.font = HEADER_FONT
        c.fill = HEADER_FILL
        c.alignment = Alignment(horizontal="center", wrap_text=True)
        c.border = THIN_BORDER


def style_data(cell, center=False):
    cell.font = DATA_FONT
    cell.border = THIN_BORDER
    if center:
        cell.alignment = Alignment(horizontal="center")


def apply_status(cell, status):
    if "WINNER" in status:
        cell.fill = WINNER_FILL
    elif "LOSER" in status:
        cell.fill = LOSER_FILL
    else:
        cell.fill = AVG_FILL
    cell.font = WHITE_BOLD
    cell.alignment = Alignment(horizontal="center")
    cell.border = THIN_BORDER


# ── Tab builders ────────────────────────────────────────────────────────
def build_full_scorecard(wb, sorted_posts):
    ws = wb.active
    ws.title = "Full Scorecard"

    headers = [
        "Rank", "Status", "Date", "Type", "Topic", "Caption Preview",
        "Likes", "Comments", "Shares", "Saves", "Views", "Reach",
        "Total Engagements", "Eng. Rate (Reach) %", "Eng. Rate (Views) %",
    ]
    for col, h in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=h)
    style_header(ws, 1, len(headers))

    center_cols = {1, 4, 7, 8, 9, 10, 11, 12, 13, 14, 15}
    for i, p in enumerate(sorted_posts):
        r = i + 2
        # Use caption_preview if available, fall back to full_caption truncated, then caption
        caption_preview = p.get("caption_preview", "")
        if not caption_preview:
            full_cap = p.get("full_caption", p.get("caption", ""))
            caption_preview = full_cap[:80] + "..." if len(full_cap) > 80 else full_cap

        vals = [
            p["rank"], p["status"], p["date"], p["type"], p["topic"],
            caption_preview,
            p.get("likes", 0), p.get("comments", 0),
            p.get("shares", 0), p.get("saves", 0),
            p.get("views", 0), p.get("reach", 0),
            p["total_eng"],
            round(p["eng_rate_reach"], 2),
            round(p["eng_rate_views"], 2),
        ]
        for col, v in enumerate(vals, 1):
            cell = ws.cell(row=r, column=col, value=v)
            style_data(cell, center=(col in center_cols))
        apply_status(ws.cell(row=r, column=2), p["status"])

    widths = [7, 16, 15, 8, 22, 55, 10, 12, 10, 10, 10, 10, 18, 20, 20]
    for idx, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(idx)].width = w

    ws.freeze_panes = "A2"
    return ws


def _write_analysis_section(ws, row, post, idx, label_font_color, analysis_text, bg_fill):
    ws.cell(row=row, column=1, value=f"#{idx+1} — Rank #{post['rank']}").font = SUBTITLE_FONT
    row += 1

    # Include content context in the analysis sections
    full_caption = post.get("full_caption", post.get("caption", "N/A"))
    visual_desc = post.get("visual_description", "N/A")

    details = [
        ("Date", post["date"]),
        ("Type", post["type"]),
        ("Topic", post["topic"]),
        ("Visual", visual_desc),
        ("Full Caption", full_caption),
        ("Likes", post.get("likes", 0)),
        ("Comments", post.get("comments", 0)),
        ("Saves", post.get("saves", 0)),
        ("Shares", post.get("shares", 0)),
        ("Views", post.get("views", 0)),
        ("Reach", post.get("reach", 0)),
        ("Total Engagements", post["total_eng"]),
        ("Eng. Rate (Reach)", f"{post['eng_rate_reach']:.2f}%"),
        ("Eng. Rate (Views)", f"{post['eng_rate_views']:.2f}%"),
    ]
    for lbl, val in details:
        ws.cell(row=row, column=1, value=lbl).font = BOLD_FONT
        cell = ws.cell(row=row, column=2, value=val)
        cell.font = DATA_FONT
        cell.alignment = Alignment(wrap_text=True)
        for c in range(1, 3):
            ws.cell(row=row, column=c).border = THIN_BORDER
        row += 1

    # Analysis row
    analysis_label = "Why It Worked" if "27AE60" in label_font_color else "Why It Underperformed"
    ws.cell(row=row, column=1, value=analysis_label).font = Font(
        bold=True, color=label_font_color, name="Arial", size=10
    )
    ws.cell(row=row, column=2, value=analysis_text).font = DATA_FONT
    ws.cell(row=row, column=2).alignment = Alignment(wrap_text=True)
    for c in range(1, 3):
        ws.cell(row=row, column=c).border = THIN_BORDER
        ws.cell(row=row, column=c).fill = bg_fill
    return row + 2


def build_analysis_tab(wb, title, emoji, posts, analyses, label_color, bg_fill):
    ws = wb.create_sheet(title)
    ws.cell(row=1, column=1, value=f"{emoji} {title.upper()}").font = TITLE_FONT
    row = 3
    for idx, p in enumerate(posts):
        analysis = analyses[idx] if idx < len(analyses) else "Analysis pending."
        row = _write_analysis_section(ws, row, p, idx, label_color, analysis, bg_fill)
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 80
    return ws


def generate_winner_analyses(winners):
    """Generate analysis text for each winner based on their metrics and content."""
    analyses = []
    for p in winners:
        parts = []

        # Metric-based insights
        if p.get("comments", 0) > 100:
            parts.append(f"High comment count ({p['comments']}) suggests strong CTA or discussion-provoking topic.")
        if p.get("saves", 0) > 100:
            parts.append(f"High saves ({p['saves']}) indicate bookmark-worthy, educational content.")
        if p.get("shares", 0) > 50:
            parts.append(f"Strong shares ({p['shares']}) show viral/word-of-mouth potential.")
        if p.get("reach", 0) > 5000:
            parts.append(f"Strong reach ({p['reach']:,}) suggests algorithmic distribution beyond followers.")
        if p["eng_rate_reach"] > 15:
            parts.append(f"Exceptional engagement rate ({p['eng_rate_reach']:.1f}%) well above average.")

        # Content-based insights
        visual = p.get("visual_description", "")
        full_caption = p.get("full_caption", "")
        if visual:
            parts.append(f"Visual format: {visual}")
        if full_caption and len(full_caption) > 200:
            parts.append("Long-form caption with detailed value — this depth drives saves.")
        elif full_caption and len(full_caption) < 50:
            parts.append("Short, punchy caption — brevity can work when the visual carries the message.")

        topic = p.get("topic", "")
        parts.append(f"Topic '{topic}' resonated with audience.")
        analyses.append(" ".join(parts))
    return analyses


def generate_loser_analyses(losers):
    """Generate analysis text for each loser based on their metrics and content."""
    analyses = []
    for p in losers:
        parts = []

        # Metric-based insights
        if p.get("comments", 0) < 20:
            parts.append(f"Low comments ({p.get('comments', 0)}) suggest weak CTA or low discussion value.")
        if p.get("saves", 0) < 15:
            parts.append(f"Low saves ({p.get('saves', 0)}) indicate content wasn't bookmark-worthy.")
        if p.get("shares", 0) < 10:
            parts.append(f"Minimal shares ({p.get('shares', 0)}) show limited viral potential.")
        if p["eng_rate_reach"] < 5:
            parts.append(f"Below-average engagement rate ({p['eng_rate_reach']:.1f}%).")

        # Content-based insights
        visual = p.get("visual_description", "")
        full_caption = p.get("full_caption", "")
        if visual:
            parts.append(f"Visual format: {visual}")
        if full_caption and len(full_caption) < 50:
            parts.append("Very short caption — may not have provided enough value or context.")

        topic = p.get("topic", "")
        parts.append(f"Topic '{topic}' may not align with audience interests or lacked a compelling hook.")
        analyses.append(" ".join(parts))
    return analyses


def build_key_takeaways(wb, sorted_posts, username):
    ws = wb.create_sheet("Key Takeaways")

    all_posts = sorted_posts
    n = len(all_posts)
    avg_reach_rate = sum(p["eng_rate_reach"] for p in all_posts) / n if n else 0
    avg_views_rate = sum(p["eng_rate_views"] for p in all_posts) / n if n else 0

    # Content type stats
    type_eng = {}
    type_count = {}
    for p in all_posts:
        t = p["type"]
        type_eng[t] = type_eng.get(t, 0) + p["eng_rate_reach"]
        type_count[t] = type_count.get(t, 0) + 1
    type_avg = {t: type_eng[t] / type_count[t] for t in type_eng}
    best_type = max(type_avg, key=type_avg.get) if type_avg else "N/A"
    worst_type = min(type_avg, key=type_avg.get) if len(type_avg) > 1 else "N/A (only one type)"

    # Topic stats
    topic_eng = {}
    topic_count = {}
    for p in all_posts:
        t = p["topic"]
        topic_eng[t] = topic_eng.get(t, 0) + p["eng_rate_reach"]
        topic_count[t] = topic_count.get(t, 0) + 1
    topic_avg = {t: topic_eng[t] / topic_count[t] for t in topic_eng}
    best_topic = max(topic_avg, key=topic_avg.get) if topic_avg else "N/A"
    worst_topic = min(topic_avg, key=topic_avg.get) if topic_avg else "N/A"

    row = 1
    ws.cell(row=row, column=1, value=f"KEY TAKEAWAYS — @{username}").font = TITLE_FONT
    row = 3

    summary = [
        ("Posts Analyzed", str(n)),
        ("Average Engagement Rate (Reach)", f"{avg_reach_rate:.2f}%"),
        ("Average Engagement Rate (Views)", f"{avg_views_rate:.2f}%"),
        ("Best Performing Content Type", f"{best_type}" + (f" ({type_avg.get(best_type, 0):.2f}% avg)" if best_type != "N/A" else "")),
        ("Worst Performing Content Type", f"{worst_type}" + (f" ({type_avg.get(worst_type, 0):.2f}% avg)" if worst_type not in ("N/A", "N/A (only one type)") else "")),
        ("Best Performing Topic", f"{best_topic} ({topic_avg.get(best_topic, 0):.2f}% avg)"),
        ("Worst Performing Topic", f"{worst_topic} ({topic_avg.get(worst_topic, 0):.2f}% avg)"),
        ("Total Views (all posts)", f"{sum(p.get('views', 0) or 0 for p in all_posts):,}"),
        ("Total Reach (all posts)", f"{sum(p.get('reach', 0) or 0 for p in all_posts):,}"),
        ("Total Engagements (all posts)", f"{sum(p['total_eng'] for p in all_posts):,}"),
    ]

    for lbl, val in summary:
        ws.cell(row=row, column=1, value=lbl).font = BOLD_FONT
        ws.cell(row=row, column=2, value=val).font = DATA_FONT
        for c in range(1, 3):
            ws.cell(row=row, column=c).border = THIN_BORDER
        row += 1

    # Recommendations — generated from the data
    winners = [p for p in all_posts if "WINNER" in p.get("status", "")]
    losers = [p for p in all_posts if "LOSER" in p.get("status", "")]

    row += 1
    ws.cell(row=row, column=1, value="DO MORE OF:").font = Font(bold=True, color="27AE60", name="Arial", size=12)
    row += 1

    more_recs = _generate_more_recs(winners, all_posts)
    for item in more_recs:
        ws.cell(row=row, column=1, value=item).font = DATA_FONT
        ws.cell(row=row, column=1).alignment = Alignment(wrap_text=True)
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
        ws.cell(row=row, column=1).fill = GREEN_BG
        ws.cell(row=row, column=1).border = THIN_BORDER
        ws.row_dimensions[row].height = 45
        row += 1

    row += 1
    ws.cell(row=row, column=1, value="DO LESS OF:").font = Font(bold=True, color="E74C3C", name="Arial", size=12)
    row += 1

    less_recs = _generate_less_recs(losers, all_posts)
    for item in less_recs:
        ws.cell(row=row, column=1, value=item).font = DATA_FONT
        ws.cell(row=row, column=1).alignment = Alignment(wrap_text=True)
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
        ws.cell(row=row, column=1).fill = RED_BG
        ws.cell(row=row, column=1).border = THIN_BORDER
        ws.row_dimensions[row].height = 45
        row += 1

    ws.column_dimensions["A"].width = 45
    ws.column_dimensions["B"].width = 55
    return ws


def _generate_more_recs(winners, all_posts):
    """Generate 3 data-driven 'do more of' recommendations."""
    recs = []

    high_comment_posts = [p for p in winners if p.get("comments", 0) > 100]
    if high_comment_posts:
        avg_eng = sum(p["eng_rate_reach"] for p in high_comment_posts) / len(high_comment_posts)
        recs.append(
            f"1. Posts with strong CTAs that drove comments (your top performers averaged "
            f"{avg_eng:.1f}% engagement rate). Comment-driving CTAs with lead magnets consistently "
            f"outperform passive posts."
        )
    else:
        winner_topics = ", ".join(p["topic"] for p in winners[:2])
        recs.append(f"1. Content about {winner_topics} — these topics drove your highest engagement rates.")

    high_save_posts = sorted(all_posts, key=lambda x: x.get("saves", 0), reverse=True)[:3]
    avg_saves = sum(p.get("saves", 0) for p in high_save_posts) / 3
    save_topics = ", ".join(set(p["topic"] for p in high_save_posts))
    recs.append(
        f"2. Educational, bookmark-worthy content (topics like {save_topics} drove highest saves, "
        f"averaging {avg_saves:.0f} saves per post). High saves signal long-term value."
    )

    high_share_posts = sorted(all_posts, key=lambda x: x.get("shares", 0), reverse=True)[:3]
    share_topics = ", ".join(set(p["topic"] for p in high_share_posts))
    recs.append(
        f"3. Shareable content about {share_topics} — these topics had the highest share counts, "
        f"indicating strong word-of-mouth potential and algorithmic distribution."
    )

    return recs


def _generate_less_recs(losers, all_posts):
    """Generate 3 data-driven 'do less of' recommendations."""
    recs = []

    loser_topics = [p["topic"] for p in losers]
    recs.append(
        f"1. Content about {', '.join(loser_topics[:2])} — these topics had the lowest engagement "
        f"rates and may not align with your audience's expectations."
    )

    low_comment = [p for p in losers if p.get("comments", 0) < 20]
    if low_comment:
        recs.append(
            f"2. Posts without clear CTAs — {len(low_comment)} of your bottom performers had fewer "
            f"than 20 comments. Adding a specific call-to-action can significantly boost engagement."
        )
    else:
        recs.append(
            f"2. Generic or oversaturated topics without a unique angle — differentiate your content "
            f"with fresh perspectives or data to stand out."
        )

    low_save = [p for p in losers if p.get("saves", 0) < 15]
    if low_save:
        recs.append(
            f"3. Content that isn't bookmark-worthy — {len(low_save)} bottom performers had fewer "
            f"than 15 saves. Focus on providing actionable value that people want to reference later."
        )
    else:
        recs.append(
            f"3. Content with low share potential — focus on creating more 'tag a friend' or 'send this to' "
            f"moments that encourage organic distribution."
        )

    return recs


# ── Content Strategy Tab ────────────────────────────────────────────────
def build_content_strategy(wb, sorted_posts, username):
    """
    Build the Content Strategy tab with specific action items grounded in
    actual post content (captions + visuals), not just metrics.

    Three sections:
    1. DOUBLE DOWN — What's working and why (from winners)
    2. ITERATE & IMPROVE — What has potential but needs tweaking (from middle)
    3. CUT OR RETHINK — What's not landing (from losers)

    Each action item references the specific post content that informed it.
    """
    ws = wb.create_sheet("Content Strategy")

    winners = [p for p in sorted_posts if "WINNER" in p.get("status", "")]
    middle = [p for p in sorted_posts if "AVERAGE" in p.get("status", "")]
    losers = [p for p in sorted_posts if "LOSER" in p.get("status", "")]

    row = 1
    ws.cell(row=row, column=1, value=f"CONTENT STRATEGY — @{username}").font = TITLE_FONT
    row += 1
    ws.cell(row=row, column=1,
            value="Action items based on what your last 10 posts are actually about — not just the numbers.").font = Font(
        italic=True, name="Arial", size=10, color="7F8C8D")
    row += 2

    # ── Section 1: DOUBLE DOWN ──
    row = _write_strategy_section(
        ws, row,
        section_title="\U0001f525 DOUBLE DOWN — Keep doing this, do more of it",
        posts=winners,
        bg_fill=GREEN_BG,
        header_fill=PatternFill("solid", fgColor="1E8449"),
        analysis_fn=_double_down_analysis,
    )

    row += 1

    # ── Section 2: ITERATE & IMPROVE ──
    row = _write_strategy_section(
        ws, row,
        section_title="\U0001f527 ITERATE & IMPROVE — Has potential, needs work",
        posts=middle,
        bg_fill=YELLOW_BG,
        header_fill=PatternFill("solid", fgColor="B7950B"),
        analysis_fn=_iterate_analysis,
    )

    row += 1

    # ── Section 3: CUT OR RETHINK ──
    row = _write_strategy_section(
        ws, row,
        section_title="\u2702\ufe0f CUT OR RETHINK — Not landing, reconsider the approach",
        posts=losers,
        bg_fill=RED_BG,
        header_fill=PatternFill("solid", fgColor="922B21"),
        analysis_fn=_cut_analysis,
    )

    row += 1

    # ── Summary: Quick-Reference Action List ──
    ws.cell(row=row, column=1, value="\U0001f4cb QUICK-REFERENCE ACTION LIST").font = TITLE_FONT
    row += 1

    actions = _build_action_list(winners, middle, losers, sorted_posts)
    for i, action in enumerate(actions, 1):
        cell = ws.cell(row=row, column=1, value=f"{i}. {action}")
        cell.font = DATA_FONT
        cell.alignment = Alignment(wrap_text=True)
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
        cell.border = THIN_BORDER
        cell.fill = BLUE_BG
        ws.row_dimensions[row].height = 40
        row += 1

    ws.column_dimensions["A"].width = 25
    ws.column_dimensions["B"].width = 50
    ws.column_dimensions["C"].width = 50
    return ws


def _write_strategy_section(ws, row, section_title, posts, bg_fill, header_fill, analysis_fn):
    """Write a strategy section (Double Down / Iterate / Cut) with post-level details."""
    # Section header
    cell = ws.cell(row=row, column=1, value=section_title)
    cell.font = Font(bold=True, color="FFFFFF", size=12, name="Arial")
    cell.fill = header_fill
    cell.alignment = Alignment(horizontal="left")
    for c in range(1, 4):
        ws.cell(row=row, column=c).fill = header_fill
        ws.cell(row=row, column=c).border = THIN_BORDER
    ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
    row += 1

    if not posts:
        ws.cell(row=row, column=1, value="(No posts in this category)").font = Font(
            italic=True, name="Arial", size=10, color="7F8C8D")
        return row + 1

    # Column sub-headers
    sub_headers = ["Post", "Content Context", "Action Item"]
    for col, h in enumerate(sub_headers, 1):
        cell = ws.cell(row=row, column=col, value=h)
        cell.font = Font(bold=True, name="Arial", size=10, color="2C3E50")
        cell.fill = PatternFill("solid", fgColor="D5D8DC")
        cell.border = THIN_BORDER
        cell.alignment = Alignment(horizontal="center")
    row += 1

    for p in posts:
        analysis = analysis_fn(p)

        # Post identifier
        post_label = f"Rank #{p['rank']} — {p['date']}\n{p['type']} | {p['topic']}\nEng Rate: {p['eng_rate_reach']:.1f}%"
        cell = ws.cell(row=row, column=1, value=post_label)
        cell.font = BOLD_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        cell.border = THIN_BORDER
        cell.fill = bg_fill

        # Content context (what the post is actually about)
        visual = p.get("visual_description", "")
        full_caption = p.get("full_caption", p.get("caption", ""))
        # Truncate caption for display but keep it meaningful
        if len(full_caption) > 300:
            caption_display = full_caption[:300] + "..."
        else:
            caption_display = full_caption

        context = f"VISUAL: {visual}\n\nCAPTION: {caption_display}" if visual else f"CAPTION: {caption_display}"
        cell = ws.cell(row=row, column=2, value=context)
        cell.font = DATA_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        cell.border = THIN_BORDER
        cell.fill = bg_fill

        # Action item
        cell = ws.cell(row=row, column=3, value=analysis)
        cell.font = DATA_FONT
        cell.alignment = Alignment(wrap_text=True, vertical="top")
        cell.border = THIN_BORDER
        cell.fill = bg_fill

        ws.row_dimensions[row].height = 100
        row += 1

    return row


def _double_down_analysis(post):
    """Generate a 'double down' action item for a winning post."""
    parts = []
    topic = post.get("topic", "this topic")
    visual = post.get("visual_description", "")
    full_caption = post.get("full_caption", "")
    saves = post.get("saves", 0) or 0
    shares = post.get("shares", 0) or 0
    comments = post.get("comments", 0) or 0

    # What specifically worked
    if saves > 100:
        parts.append(f"This post got {saves} saves — people wanted to come back to it. The educational angle is clearly hitting.")
    if shares > 50:
        parts.append(f"{shares} shares means people are sending this to friends. This is the kind of content that grows your reach organically.")
    if comments > 100:
        parts.append(f"{comments} comments shows strong audience interaction. Whatever CTA or discussion prompt you used here, replicate it.")

    # Visual format insight
    if visual:
        parts.append(f"The visual format ({visual}) clearly resonates — make this a recurring format.")

    # Caption structure insight
    if full_caption:
        if "?" in full_caption:
            parts.append("The question in your caption drove engagement. Keep asking your audience direct questions.")
        if any(word in full_caption.lower() for word in ["save", "bookmark", "come back"]):
            parts.append("Your save CTA is working. Keep prompting saves — it signals value to the algorithm.")
        if len(full_caption) > 200:
            parts.append("Long-form caption with real depth. Your audience clearly reads and values detailed posts on this topic.")

    parts.append(f"ACTION: Create a series around '{topic}' using this same format. Aim for 2-3 more posts with this exact angle.")

    return " ".join(parts)


def _iterate_analysis(post):
    """Generate an 'iterate & improve' action item for a middle-performing post."""
    parts = []
    topic = post.get("topic", "this topic")
    visual = post.get("visual_description", "")
    full_caption = post.get("full_caption", "")
    saves = post.get("saves", 0) or 0
    shares = post.get("shares", 0) or 0
    comments = post.get("comments", 0) or 0
    reach = post.get("reach", 0) or 0
    eng_rate = post.get("eng_rate_reach", 0)

    # Identify what's underperforming relative to potential
    if saves < 30 and comments > 30:
        parts.append("Getting comments but not saves — the topic sparks discussion but isn't 'save-worthy.' Try adding a framework, checklist, or step-by-step that makes it reference material.")
    elif saves > 30 and comments < 20:
        parts.append("Getting saves but low comments — people value it but aren't engaging publicly. Add a stronger CTA question at the end.")
    elif shares < 15:
        parts.append("Low shares — the content provides value but isn't 'send this to someone' material. Try making the hook more relatable or universal.")

    if reach > 0 and eng_rate < 8:
        parts.append(f"Reach was decent ({reach:,}) but only {eng_rate:.1f}% engaged. The hook might be getting impressions but not stopping the scroll.")

    if visual:
        parts.append(f"Visual was: {visual}. Consider testing a different visual treatment — same topic, new presentation.")

    if full_caption and len(full_caption) < 100:
        parts.append("Short caption. Try a longer, more detailed version with a clear value proposition and CTA.")

    parts.append(f"ACTION: Revisit '{topic}' with a stronger hook and clearer CTA. The topic has potential — the packaging needs work.")

    return " ".join(parts)


def _cut_analysis(post):
    """Generate a 'cut or rethink' action item for a losing post."""
    parts = []
    topic = post.get("topic", "this topic")
    visual = post.get("visual_description", "")
    full_caption = post.get("full_caption", "")
    saves = post.get("saves", 0) or 0
    shares = post.get("shares", 0) or 0
    comments = post.get("comments", 0) or 0
    reach = post.get("reach", 0) or 0

    if reach > 0 and reach < 2000:
        parts.append(f"Only {reach:,} reach — the algorithm didn't push this. The initial engagement signals (first 30 min) likely weren't strong enough.")
    elif reach > 3000:
        parts.append(f"Reached {reach:,} people but very few engaged. The content was shown to people but didn't resonate — likely a hook or relevance issue, not a distribution issue.")

    if saves < 10:
        parts.append("Almost no saves. This didn't provide enough tangible value for people to want to reference later.")
    if shares < 5:
        parts.append("Virtually no shares — nothing about this made people think 'someone I know needs to see this.'")
    if comments < 10:
        parts.append("Very few comments — no conversation starter, no CTA, or the audience just didn't care about this angle.")

    if visual:
        parts.append(f"Visual was: {visual}.")

    if full_caption:
        if len(full_caption) < 50:
            parts.append("Caption was extremely short — not enough substance to drive engagement.")
        if "?" not in full_caption:
            parts.append("No question in caption — missed opportunity to prompt comments.")

    parts.append(f"ACTION: Either drop '{topic}' entirely or completely reimagine the angle. If you believe in the topic, the problem is likely the hook and format, not the subject matter itself.")

    return " ".join(parts)


def _build_action_list(winners, middle, losers, all_posts):
    """Build a numbered quick-reference action list from all the analysis."""
    actions = []

    # From winners — what to replicate
    if winners:
        winner_topics = ", ".join(set(p["topic"] for p in winners))
        winner_formats = ", ".join(set(p.get("visual_description", "")[:40] for p in winners if p.get("visual_description")))
        actions.append(f"DOUBLE DOWN on these topics: {winner_topics}. Create 2-3 more posts per topic using similar angles.")
        if winner_formats:
            actions.append(f"REPLICATE these visual formats that worked: {winner_formats}")

    # High save content
    high_save = sorted(all_posts, key=lambda x: x.get("saves", 0) or 0, reverse=True)[:2]
    if high_save and (high_save[0].get("saves", 0) or 0) > 50:
        save_topics = ", ".join(set(p["topic"] for p in high_save))
        actions.append(f"Your audience SAVES content about {save_topics} — lean into educational, reference-worthy content on these topics.")

    # CTA pattern
    high_comment = [p for p in all_posts if (p.get("comments", 0) or 0) > 80]
    low_comment = [p for p in all_posts if (p.get("comments", 0) or 0) < 15]
    if high_comment and low_comment:
        actions.append(
            f"Your top posts for comments averaged {sum(p.get('comments', 0) for p in high_comment) // len(high_comment)} comments. "
            f"Your worst averaged {sum(p.get('comments', 0) for p in low_comment) // len(low_comment)}. "
            f"Study what CTAs your winners used and apply them to underperformers."
        )

    # From middle — iteration opportunities
    if middle:
        middle_topics = ", ".join(set(p["topic"] for p in middle[:2]))
        actions.append(f"ITERATE on these middle-performers: {middle_topics}. Same topics, stronger hooks and CTAs.")

    # From losers — what to cut
    if losers:
        loser_topics = ", ".join(set(p["topic"] for p in losers))
        actions.append(f"RECONSIDER or CUT these topics: {loser_topics}. If you want to keep them, completely change the format and hook.")

    # Caption length pattern
    avg_caption_winners = sum(len(p.get("full_caption", "")) for p in winners) / len(winners) if winners else 0
    avg_caption_losers = sum(len(p.get("full_caption", "")) for p in losers) / len(losers) if losers else 0
    if avg_caption_winners > 0 and avg_caption_losers > 0:
        if avg_caption_winners > avg_caption_losers * 1.5:
            actions.append(
                f"Your winners averaged {int(avg_caption_winners)} chars in captions vs {int(avg_caption_losers)} for losers. "
                f"Longer, more detailed captions are working for you — stop being brief."
            )
        elif avg_caption_losers > avg_caption_winners * 1.5:
            actions.append(
                f"Your winners averaged {int(avg_caption_winners)} chars vs {int(avg_caption_losers)} for losers. "
                f"Shorter, punchier captions perform better for your audience."
            )

    return actions


# ── Main ────────────────────────────────────────────────────────────────
def main():
    if len(sys.argv) < 3:
        print("Usage: python build_scorecard.py <input.json> <output.xlsx>")
        sys.exit(1)

    input_path = sys.argv[1]
    output_path = sys.argv[2]

    data = load_data(input_path)
    username = data.get("username", "unknown")
    posts = data.get("posts", [])

    if not posts:
        print("Error: No posts found in input JSON.")
        sys.exit(1)

    sorted_posts = calc_metrics(posts)

    wb = Workbook()

    # Tab 1
    build_full_scorecard(wb, sorted_posts)

    # Tab 2
    winners = [p for p in sorted_posts if "WINNER" in p["status"]]
    winner_analyses = generate_winner_analyses(winners)
    build_analysis_tab(wb, "Winners Analysis", "\U0001f3c6", winners, winner_analyses, "27AE60", GREEN_BG)

    # Tab 3
    losers = [p for p in sorted_posts if "LOSER" in p["status"]]
    loser_analyses = generate_loser_analyses(losers)
    build_analysis_tab(wb, "Losers Analysis", "\U0001f53b", losers, loser_analyses, "E74C3C", RED_BG)

    # Tab 4
    build_key_takeaways(wb, sorted_posts, username)

    # Tab 5 — NEW: Content Strategy
    build_content_strategy(wb, sorted_posts, username)

    # Ensure output directory exists
    os.makedirs(os.path.dirname(output_path) or ".", exist_ok=True)
    wb.save(output_path)
    print(f"IG Scorecard saved to: {output_path}")


if __name__ == "__main__":
    main()
