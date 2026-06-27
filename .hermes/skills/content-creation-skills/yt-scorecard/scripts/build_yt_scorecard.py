#!/usr/bin/env python3
"""
YouTube Scorecard Builder
Adapted from IG Scorecard — produces a 5-tab .xlsx analyzing the last 10 YouTube videos.
Tabs: Full Scorecard, Winners Analysis, Losers Analysis, Key Takeaways, Content Strategy.

Usage: python build_yt_scorecard.py <input.json> <output.xlsx>
"""

import json, sys, os
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def load_data(path):
    with open(path) as f:
        return json.load(f)

def calc_metrics(videos):
    for v in videos:
        views = v.get("views", 0) or 0
        likes = v.get("likes", 0) or 0
        comments = v.get("comments", 0) or 0
        impressions = v.get("impressions", 0) or 0
        ctr = v.get("ctr", 0) or 0
        wt = v.get("watch_time_hours", 0) or 0
        subs = v.get("subscribers", 0) or 0

        v["total_eng"] = likes + comments
        v["eng_rate_views"] = (v["total_eng"] / views * 100) if views > 0 else 0
        v["avg_view_min"] = (wt * 60 / views) if views > 0 else 0
        v["subs_per_1k"] = (subs / views * 1000) if views > 0 else 0

    sorted_vids = sorted(videos, key=lambda x: x["views"], reverse=True)
    # Score: weighted combo of views (40%), CTR (25%), eng rate (20%), subs/1k (15%)
    if sorted_vids:
        max_views = max(v["views"] for v in sorted_vids) or 1
        max_ctr = max(v.get("ctr", 0) for v in sorted_vids) or 1
        max_eng = max(v["eng_rate_views"] for v in sorted_vids) or 1
        max_subs = max(v["subs_per_1k"] for v in sorted_vids) or 1
        for v in sorted_vids:
            v["score"] = (
                0.40 * (v["views"] / max_views) +
                0.25 * (v.get("ctr", 0) / max_ctr) +
                0.20 * (v["eng_rate_views"] / max_eng) +
                0.15 * (v["subs_per_1k"] / max_subs)
            )

    sorted_vids = sorted(sorted_vids, key=lambda x: x["score"], reverse=True)

    n = len(sorted_vids)
    if n >= 10:
        win_cutoff, lose_cutoff = 3, n - 3
    elif n >= 6:
        win_cutoff, lose_cutoff = 2, n - 2
    else:
        win_cutoff, lose_cutoff = 1, max(n - 1, 1)

    for i, v in enumerate(sorted_vids):
        v["rank"] = i + 1
        if i < win_cutoff:
            v["status"] = "\U0001f3c6 WINNER"
        elif i >= lose_cutoff:
            v["status"] = "\U0001f53b LOSER"
        else:
            v["status"] = "\u2796 AVERAGE"
    return sorted_vids

# Styles
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

# Tab 1: Full Scorecard
def build_full_scorecard(wb, sorted_vids):
    ws = wb.active
    ws.title = "Full Scorecard"
    headers = [
        "Rank", "Status", "Date", "Title", "Topic", "Duration",
        "Views", "Impressions", "CTR %", "Watch Time (hrs)",
        "Avg View (min)", "Likes", "Comments", "Subs Gained",
        "Eng. Rate (Views) %", "Subs/1K Views", "Score",
    ]
    for col, h in enumerate(headers, 1):
        ws.cell(row=1, column=col, value=h)
    style_header(ws, 1, len(headers))

    center_cols = {1, 3, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15, 16, 17}
    for i, v in enumerate(sorted_vids):
        r = i + 2
        title_preview = v["title"][:60] + "..." if len(v["title"]) > 60 else v["title"]
        vals = [
            v["rank"], v["status"], v["date"], title_preview, v["topic"], v["duration"],
            v["views"], v.get("impressions", 0), round(v.get("ctr", 0), 1),
            round(v.get("watch_time_hours", 0), 1),
            round(v["avg_view_min"], 1),
            v.get("likes", 0), v.get("comments", 0), v.get("subscribers", 0),
            round(v["eng_rate_views"], 2),
            round(v["subs_per_1k"], 1),
            round(v["score"], 3),
        ]
        for col, val in enumerate(vals, 1):
            cell = ws.cell(row=r, column=col, value=val)
            style_data(cell, center=(col in center_cols))
        apply_status(ws.cell(row=r, column=2), v["status"])

    widths = [7, 16, 14, 50, 24, 10, 10, 12, 8, 14, 12, 8, 10, 10, 18, 14, 8]
    for idx, w in enumerate(widths, 1):
        ws.column_dimensions[get_column_letter(idx)].width = w
    ws.freeze_panes = "A2"

# Tab 2 & 3: Analysis tabs
def _write_analysis(ws, row, v, idx, label_color, analysis, bg):
    ws.cell(row=row, column=1, value=f"#{idx+1} — Rank #{v['rank']}").font = SUBTITLE_FONT
    row += 1
    details = [
        ("Title", v["title"]),
        ("Date", v["date"]),
        ("Topic", v["topic"]),
        ("Duration", v["duration"]),
        ("Views", v["views"]),
        ("Impressions", v.get("impressions", 0)),
        ("CTR", f"{v.get('ctr', 0)}%"),
        ("Watch Time (hrs)", v.get("watch_time_hours", 0)),
        ("Avg View (min)", f"{v['avg_view_min']:.1f}"),
        ("Likes", v.get("likes", 0)),
        ("Comments", v.get("comments", 0)),
        ("Subscribers Gained", v.get("subscribers", 0)),
        ("Eng Rate (Views)", f"{v['eng_rate_views']:.2f}%"),
        ("Subs per 1K Views", f"{v['subs_per_1k']:.1f}"),
    ]
    for lbl, val in details:
        ws.cell(row=row, column=1, value=lbl).font = BOLD_FONT
        c = ws.cell(row=row, column=2, value=val)
        c.font = DATA_FONT
        c.alignment = Alignment(wrap_text=True)
        for cc in range(1, 3):
            ws.cell(row=row, column=cc).border = THIN_BORDER
        row += 1

    label = "Why It Worked" if "27AE60" in label_color else "Why It Underperformed"
    ws.cell(row=row, column=1, value=label).font = Font(bold=True, color=label_color, name="Arial", size=10)
    ws.cell(row=row, column=2, value=analysis).font = DATA_FONT
    ws.cell(row=row, column=2).alignment = Alignment(wrap_text=True)
    for c in range(1, 3):
        ws.cell(row=row, column=c).border = THIN_BORDER
        ws.cell(row=row, column=c).fill = bg
    return row + 2

def build_analysis_tab(wb, title, emoji, vids, analyses, color, bg):
    ws = wb.create_sheet(title)
    ws.cell(row=1, column=1, value=f"{emoji} {title.upper()}").font = TITLE_FONT
    row = 3
    for i, v in enumerate(vids):
        a = analyses[i] if i < len(analyses) else "Analysis pending."
        row = _write_analysis(ws, row, v, i, color, a, bg)
    ws.column_dimensions["A"].width = 22
    ws.column_dimensions["B"].width = 80

def gen_winner_analyses(winners):
    analyses = []
    for v in winners:
        parts = []
        if v.get("ctr", 0) > 6:
            parts.append(f"Strong CTR ({v['ctr']}%) — the title and thumbnail are clearly compelling. People click when they see this.")
        if v["views"] > 1000:
            parts.append(f"{v['views']:,} views shows strong algorithmic distribution beyond your subscriber base.")
        if v.get("subscribers", 0) > 20:
            parts.append(f"+{v['subscribers']} subscribers from one video — this topic converts viewers into followers.")
        if v["avg_view_min"] > 3:
            parts.append(f"Average view duration of {v['avg_view_min']:.1f} min signals high retention — viewers are staying.")
        if v.get("watch_time_hours", 0) > 50:
            parts.append(f"{v['watch_time_hours']} hours of watch time is massive fuel for the algorithm.")
        if v.get("likes", 0) > 30:
            parts.append(f"{v['likes']} likes shows strong positive sentiment.")
        parts.append(f"Topic '{v['topic']}' clearly resonates. ACTION: Create a series around this topic with similar packaging.")
        analyses.append(" ".join(parts))
    return analyses

def gen_loser_analyses(losers):
    analyses = []
    for v in losers:
        parts = []
        if v.get("ctr", 0) < 4:
            parts.append(f"Low CTR ({v['ctr']}%) — the title/thumbnail isn't grabbing attention in the feed.")
        if v["views"] < 400:
            parts.append(f"Only {v['views']} views — YouTube didn't push this. The initial engagement signals were likely too weak.")
        if v.get("subscribers", 0) < 5:
            parts.append(f"Only +{v['subscribers']} subscribers — this content didn't convince viewers to follow.")
        if v["avg_view_min"] < 2:
            parts.append(f"Avg view duration of just {v['avg_view_min']:.1f} min — viewers are bouncing early. The hook or intro may not be strong enough.")
        if v.get("comments", 0) < 3:
            parts.append(f"Only {v['comments']} comments — no CTA or the topic didn't spark conversation.")
        parts.append(f"Topic '{v['topic']}' may not align with what your audience wants. ACTION: Either drop this topic or completely reimagine the packaging.")
        analyses.append(" ".join(parts))
    return analyses

# Tab 4: Key Takeaways
def build_key_takeaways(wb, sorted_vids, channel):
    ws = wb.create_sheet("Key Takeaways")
    n = len(sorted_vids)
    avg_ctr = sum(v.get("ctr", 0) for v in sorted_vids) / n
    avg_eng = sum(v["eng_rate_views"] for v in sorted_vids) / n
    avg_views = sum(v["views"] for v in sorted_vids) / n
    avg_subs = sum(v.get("subscribers", 0) for v in sorted_vids) / n

    topic_views = {}
    topic_count = {}
    for v in sorted_vids:
        t = v["topic"]
        topic_views[t] = topic_views.get(t, 0) + v["views"]
        topic_count[t] = topic_count.get(t, 0) + 1
    topic_avg = {t: topic_views[t] / topic_count[t] for t in topic_views}
    best_topic = max(topic_avg, key=topic_avg.get) if topic_avg else "N/A"
    worst_topic = min(topic_avg, key=topic_avg.get) if topic_avg else "N/A"

    row = 1
    ws.cell(row=row, column=1, value=f"KEY TAKEAWAYS — {channel}").font = TITLE_FONT
    row = 3

    winners = [v for v in sorted_vids if "WINNER" in v.get("status", "")]
    losers = [v for v in sorted_vids if "LOSER" in v.get("status", "")]

    summary = [
        ("Videos Analyzed", str(n)),
        ("Total Views (all videos)", f"{sum(v['views'] for v in sorted_vids):,}"),
        ("Total Watch Time (hours)", f"{sum(v.get('watch_time_hours', 0) for v in sorted_vids):,.1f}"),
        ("Total Subscribers Gained", f"+{sum(v.get('subscribers', 0) for v in sorted_vids):,}"),
        ("Average Views per Video", f"{avg_views:,.0f}"),
        ("Average CTR", f"{avg_ctr:.1f}%"),
        ("Average Engagement Rate (Views)", f"{avg_eng:.2f}%"),
        ("Average Subs Gained per Video", f"+{avg_subs:.1f}"),
        ("Best Performing Topic", f"{best_topic} ({topic_avg.get(best_topic, 0):,.0f} avg views)"),
        ("Worst Performing Topic", f"{worst_topic} ({topic_avg.get(worst_topic, 0):,.0f} avg views)"),
    ]
    for lbl, val in summary:
        ws.cell(row=row, column=1, value=lbl).font = BOLD_FONT
        ws.cell(row=row, column=2, value=val).font = DATA_FONT
        for c in range(1, 3):
            ws.cell(row=row, column=c).border = THIN_BORDER
        row += 1

    row += 1
    ws.cell(row=row, column=1, value="DO MORE OF:").font = Font(bold=True, color="27AE60", name="Arial", size=12)
    row += 1
    more_recs = []
    if winners:
        w_topics = ", ".join(set(v["topic"] for v in winners))
        avg_w_ctr = sum(v.get("ctr", 0) for v in winners) / len(winners)
        more_recs.append(f"1. Topics like {w_topics} — your winners averaged {avg_w_ctr:.1f}% CTR and {sum(v['views'] for v in winners)/len(winners):,.0f} views per video.")
    high_sub = sorted(sorted_vids, key=lambda x: x.get("subscribers", 0), reverse=True)[:3]
    sub_topics = ", ".join(set(v["topic"] for v in high_sub))
    more_recs.append(f"2. Subscriber-converting content about {sub_topics} — these topics drove the most new subscribers per video.")
    high_wt = sorted(sorted_vids, key=lambda x: x.get("watch_time_hours", 0), reverse=True)[:3]
    wt_topics = ", ".join(set(v["topic"] for v in high_wt))
    more_recs.append(f"3. Long-form deep dives on {wt_topics} — these drove the most watch time, which is YouTube's #1 ranking signal.")

    for item in more_recs:
        cell = ws.cell(row=row, column=1, value=item)
        cell.font = DATA_FONT
        cell.alignment = Alignment(wrap_text=True)
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
        cell.fill = GREEN_BG
        cell.border = THIN_BORDER
        ws.row_dimensions[row].height = 45
        row += 1

    row += 1
    ws.cell(row=row, column=1, value="DO LESS OF:").font = Font(bold=True, color="E74C3C", name="Arial", size=12)
    row += 1
    less_recs = []
    if losers:
        l_topics = ", ".join(set(v["topic"] for v in losers))
        less_recs.append(f"1. Content about {l_topics} — these had the lowest views and weakest CTR. Your audience isn't clicking on these.")
    low_ctr = [v for v in losers if v.get("ctr", 0) < 4]
    if low_ctr:
        less_recs.append(f"2. Vague or unclear titles — {len(low_ctr)} of your bottom performers had CTR below 4%. The title/thumbnail must promise specific value.")
    else:
        less_recs.append("2. Topics that don't clearly communicate a specific outcome or benefit in the title/thumbnail.")
    low_comm = [v for v in losers if v.get("comments", 0) < 5]
    if low_comm:
        less_recs.append(f"3. Videos without discussion hooks — {len(low_comm)} bottom performers had fewer than 5 comments. Add CTAs asking specific questions.")
    else:
        less_recs.append("3. Videos without clear community engagement hooks or CTAs.")

    for item in less_recs:
        cell = ws.cell(row=row, column=1, value=item)
        cell.font = DATA_FONT
        cell.alignment = Alignment(wrap_text=True)
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=2)
        cell.fill = RED_BG
        cell.border = THIN_BORDER
        ws.row_dimensions[row].height = 45
        row += 1

    ws.column_dimensions["A"].width = 45
    ws.column_dimensions["B"].width = 55

# Tab 5: Content Strategy
def build_content_strategy(wb, sorted_vids, channel):
    ws = wb.create_sheet("Content Strategy")
    winners = [v for v in sorted_vids if "WINNER" in v.get("status", "")]
    middle = [v for v in sorted_vids if "AVERAGE" in v.get("status", "")]
    losers = [v for v in sorted_vids if "LOSER" in v.get("status", "")]

    row = 1
    ws.cell(row=row, column=1, value=f"CONTENT STRATEGY — {channel}").font = TITLE_FONT
    row += 1
    ws.cell(row=row, column=1, value="Action items based on what your last 10 videos actually performed like — not just vibes.").font = Font(italic=True, name="Arial", size=10, color="7F8C8D")
    row += 2

    def write_section(ws, row, title, vids, bg, header_fill, fn):
        cell = ws.cell(row=row, column=1, value=title)
        cell.font = Font(bold=True, color="FFFFFF", size=12, name="Arial")
        cell.fill = header_fill
        for c in range(1, 4):
            ws.cell(row=row, column=c).fill = header_fill
            ws.cell(row=row, column=c).border = THIN_BORDER
        ws.merge_cells(start_row=row, start_column=1, end_row=row, end_column=3)
        row += 1
        if not vids:
            ws.cell(row=row, column=1, value="(No videos in this category)").font = Font(italic=True, name="Arial", size=10, color="7F8C8D")
            return row + 1
        for h_col, h_text in enumerate(["Video", "Key Metrics", "Action Item"], 1):
            c = ws.cell(row=row, column=h_col, value=h_text)
            c.font = Font(bold=True, name="Arial", size=10, color="2C3E50")
            c.fill = PatternFill("solid", fgColor="D5D8DC")
            c.border = THIN_BORDER
            c.alignment = Alignment(horizontal="center")
        row += 1
        for v in vids:
            label = f"Rank #{v['rank']} — {v['date']}\n{v['topic']}\nScore: {v['score']:.3f}"
            ws.cell(row=row, column=1, value=label).font = BOLD_FONT
            ws.cell(row=row, column=1).alignment = Alignment(wrap_text=True, vertical="top")
            ws.cell(row=row, column=1).border = THIN_BORDER
            ws.cell(row=row, column=1).fill = bg

            metrics = f"Views: {v['views']:,} | CTR: {v.get('ctr',0)}%\nWatch Time: {v.get('watch_time_hours',0)} hrs\nLikes: {v.get('likes',0)} | Comments: {v.get('comments',0)}\nSubs: +{v.get('subscribers',0)}"
            ws.cell(row=row, column=2, value=metrics).font = DATA_FONT
            ws.cell(row=row, column=2).alignment = Alignment(wrap_text=True, vertical="top")
            ws.cell(row=row, column=2).border = THIN_BORDER
            ws.cell(row=row, column=2).fill = bg

            ws.cell(row=row, column=3, value=fn(v)).font = DATA_FONT
            ws.cell(row=row, column=3).alignment = Alignment(wrap_text=True, vertical="top")
            ws.cell(row=row, column=3).border = THIN_BORDER
            ws.cell(row=row, column=3).fill = bg
            ws.row_dimensions[row].height = 90
            row += 1
        return row

    def double_down(v):
        parts = []
        if v.get("ctr", 0) > 6:
            parts.append(f"CTR of {v['ctr']}% is excellent — this title/thumbnail formula works. Study it and replicate the pattern.")
        if v.get("subscribers", 0) > 20:
            parts.append(f"+{v['subscribers']} subs means this content is a subscriber magnet. This is your growth engine.")
        if v.get("watch_time_hours", 0) > 100:
            parts.append(f"{v['watch_time_hours']} hrs of watch time is massive. Long watch time = YouTube pushes your video to more people.")
        if v.get("likes", 0) > 50:
            parts.append(f"{v['likes']} likes. Strong positive signal. Viewers are voting with their thumbs.")
        parts.append(f"ACTION: Create 2-3 more videos around '{v['topic']}' with similar title structure and thumbnail style.")
        return " ".join(parts)

    def iterate(v):
        parts = []
        if v.get("ctr", 0) < 5:
            parts.append(f"CTR of {v['ctr']}% could be higher. Test a more curiosity-driven title or a bolder thumbnail.")
        elif v.get("ctr", 0) >= 5 and v["views"] < 500:
            parts.append("Decent CTR but low views — YouTube may not be recommending it. Check if the watch time is holding it back.")
        if v.get("comments", 0) < 5:
            parts.append("Low comments. Add a specific question in the first 30 seconds and at the end to drive discussion.")
        if v["avg_view_min"] < 3:
            parts.append(f"Avg view of {v['avg_view_min']:.1f} min — viewers are leaving early. Tighten the intro and deliver value faster.")
        parts.append(f"ACTION: Revisit '{v['topic']}' with stronger packaging — same core topic, better hook and title.")
        return " ".join(parts)

    def cut(v):
        parts = []
        if v.get("ctr", 0) < 4:
            parts.append(f"CTR of {v['ctr']}% is below average. People see this in their feed and keep scrolling.")
        if v["views"] < 300:
            parts.append(f"Only {v['views']} views — YouTube barely distributed this. The topic/packaging combo didn't get traction.")
        if v.get("subscribers", 0) < 3:
            parts.append(f"Only +{v['subscribers']} subscribers — viewers who watched didn't care enough to follow.")
        if v.get("comments", 0) < 3:
            parts.append(f"Only {v['comments']} comments — zero conversation. This didn't connect.")
        parts.append(f"ACTION: Either drop '{v['topic']}' entirely or do a COMPLETELY different take — new angle, new title format, new hook.")
        return " ".join(parts)

    row = write_section(ws, row, "\U0001f525 DOUBLE DOWN — Keep doing this, do more of it", winners, GREEN_BG, PatternFill("solid", fgColor="1E8449"), double_down)
    row += 1
    row = write_section(ws, row, "\U0001f527 ITERATE & IMPROVE — Has potential, needs work", middle, YELLOW_BG, PatternFill("solid", fgColor="B7950B"), iterate)
    row += 1
    row = write_section(ws, row, "\u2702\ufe0f CUT OR RETHINK — Not landing, reconsider", losers, RED_BG, PatternFill("solid", fgColor="922B21"), cut)
    row += 1

    # Quick reference action list
    ws.cell(row=row, column=1, value="\U0001f4cb QUICK-REFERENCE ACTION LIST").font = TITLE_FONT
    row += 1
    actions = []
    if winners:
        w_topics = ", ".join(set(v["topic"] for v in winners))
        actions.append(f"DOUBLE DOWN on: {w_topics}. Create 2-3 more videos per topic with similar packaging.")
    high_ctr = sorted(sorted_vids, key=lambda x: x.get("ctr", 0), reverse=True)[:3]
    actions.append(f"STUDY your best CTR titles: {' | '.join(v['title'][:50] for v in high_ctr)}. Replicate these title structures.")
    high_sub = sorted(sorted_vids, key=lambda x: x.get("subscribers", 0), reverse=True)[:3]
    sub_topics = ", ".join(set(v["topic"] for v in high_sub))
    actions.append(f"Your SUBSCRIBER MAGNETS are about: {sub_topics}. These convert viewers into followers — lean in hard.")
    if middle:
        m_topics = ", ".join(set(v["topic"] for v in middle[:2]))
        actions.append(f"ITERATE on: {m_topics}. Same topics, stronger titles and hooks.")
    if losers:
        l_topics = ", ".join(set(v["topic"] for v in losers))
        actions.append(f"RECONSIDER or CUT: {l_topics}. If you revisit these, completely change the angle and packaging.")

    avg_winner_dur = sum(len(v["duration"]) for v in winners) if winners else 0
    avg_loser_dur = sum(len(v["duration"]) for v in losers) if losers else 0
    # Check if longer videos are performing better
    avg_w_wt = sum(v.get("watch_time_hours", 0) for v in winners) / len(winners) if winners else 0
    avg_l_wt = sum(v.get("watch_time_hours", 0) for v in losers) / len(losers) if losers else 0
    if avg_w_wt > avg_l_wt * 2:
        actions.append(f"Your winners averaged {avg_w_wt:.0f} hrs of watch time vs {avg_l_wt:.0f} hrs for losers. Longer, deeper content is winning — keep going deep.")

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
    ws.column_dimensions["B"].width = 40
    ws.column_dimensions["C"].width = 55

def main():
    if len(sys.argv) < 3:
        print("Usage: python build_yt_scorecard.py <input.json> <output.xlsx>")
        sys.exit(1)

    data = load_data(sys.argv[1])
    channel = data.get("channel_name", "Unknown")
    videos = data.get("videos", [])
    if not videos:
        print("Error: No videos found.")
        sys.exit(1)

    sorted_vids = calc_metrics(videos)
    wb = Workbook()

    build_full_scorecard(wb, sorted_vids)

    winners = [v for v in sorted_vids if "WINNER" in v["status"]]
    losers = [v for v in sorted_vids if "LOSER" in v["status"]]

    build_analysis_tab(wb, "Winners Analysis", "\U0001f3c6", winners, gen_winner_analyses(winners), "27AE60", GREEN_BG)
    build_analysis_tab(wb, "Losers Analysis", "\U0001f53b", losers, gen_loser_analyses(losers), "E74C3C", RED_BG)
    build_key_takeaways(wb, sorted_vids, channel)
    build_content_strategy(wb, sorted_vids, channel)

    os.makedirs(os.path.dirname(sys.argv[2]) or ".", exist_ok=True)
    wb.save(sys.argv[2])
    print(f"YouTube Scorecard saved to: {sys.argv[2]}")

if __name__ == "__main__":
    main()
