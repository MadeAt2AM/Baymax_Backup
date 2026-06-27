---
name: yt-scorecard
description: >
  Build a YouTube Scorecard analyzing any channel's last 10 videos. Navigates to YouTube Studio,
  collects video analytics (views, watch time, impressions, CTR, subscribers, likes, comments)
  from Overview and Reach tabs, ranks by weighted composite score, and outputs a .xlsx with
  Full Scorecard, Winners Analysis, Losers Analysis, Key Takeaways, and Content Strategy tabs.
  Use this skill whenever the user mentions: YouTube scorecard, YouTube audit, video performance,
  analyze my YouTube, YT analytics, which videos performed best, YouTube report, rank my videos,
  score my content, how are my videos doing, top performing videos, worst performing videos,
  YouTube content strategy, what videos should I make more of, YouTube channel audit.
  Even casual requests like "check how my YouTube is doing" or "which of my videos hit" should
  trigger this skill.
---

# YouTube Scorecard

This skill automates the full process of collecting YouTube video analytics via the browser and producing a professional Scorecard spreadsheet with actionable content strategy. It works on whatever YouTube account is currently signed in to YouTube Studio.

## Overview

The scorecard analyzes the **10 most recent videos** and produces a 5-tab .xlsx file:
1. **Full Scorecard** — all 10 videos ranked by weighted composite score with color-coded status
2. **Winners Analysis** — deep dive on the top 3 videos with "Why It Worked" analysis
3. **Losers Analysis** — deep dive on the bottom 3 videos with "Why It Underperformed" analysis
4. **Key Takeaways** — averages, best/worst topics, and high-level recommendations
5. **Content Strategy** — specific action items: what to double down on, what to iterate/improve, and what to cut

The composite score weights: Views (40%), CTR (25%), Engagement Rate (20%), Subs per 1K Views (15%). This balances raw reach with clickability, audience engagement, and subscriber conversion power.

## Workflow

There are two phases: **data collection** (browser) and **spreadsheet generation** (Python script). The browser phase is the bottleneck, so the instructions below are optimized to minimize clicks and page loads.

---

### Phase 1: Data Collection (Browser)

The data collection has two stages. First, scrape the Content tab table to get video IDs, titles, dates, durations, views, comments, and likes for all 10 videos in one shot. Then visit each video's analytics page to collect the metrics that only live there (watch time, subscribers, impressions, CTR). This order matters — the Content tab gives you the bulk of the data upfront and avoids having to hunt for likes/comments on individual pages.

#### Step 1 — Navigate to YouTube Studio

1. Get browser tab context (`tabs_context_mcp`, create if empty)
2. Navigate to `https://studio.youtube.com`
3. Take a screenshot to confirm you're logged in and can see the Studio dashboard
4. If not logged in: **stop and tell the user** to log in, then continue once they confirm
5. Note the **channel name** from the dashboard header — you'll need it for the spreadsheet

#### Step 2 — Scrape the Content Tab (video IDs, titles, dates, views, comments, likes)

The Content tab in YouTube Studio shows a table with columns for Video, Visibility, Monetization, Restrictions, Date, Views, Comments, and Likes (vs. dislikes). This is the most efficient place to collect the majority of the data.

1. Click the **Content** tab in the left sidebar
2. Wait for the page to fully load — the table can take a few seconds to render. Wait 3 seconds, then take a screenshot.
3. **Important rendering quirk**: The Content tab sometimes loads the DOM rows but doesn't visually render the table columns. If you take a screenshot and see "Channel content" with an empty area below it, the data is likely in the DOM but not visible. In this case:
   - Try clicking the "Content" sidebar item again, or navigate directly to the videos/upload URL
   - Wait 3 seconds and screenshot again
   - The table should now show with all columns: Video, Visibility, Monetization, Restrictions, Date, Views, Comments, Likes
4. Once the table is visually rendered with all columns, take a screenshot and read the data for the first ~7 videos visible on screen.
5. Scroll down to see the remaining videos and take another screenshot.

**From the Content tab, record for each of the 10 most recent videos:**
- **Video title** (full title from the Video column)
- **Video ID** (extract from the thumbnail/row link — the `/video/{ID}` portion of the href)
- **Duration** (shown on the thumbnail overlay, e.g., "31:25", "8:14", "2:37:02")
- **Date** (from the Date column, e.g., "Feb 4, 2026")
- **Views** (from the Views column)
- **Comments** (from the Comments column)
- **Likes count** (from the Likes vs. dislikes column — shown as "100.0% / 14 likes", extract the number)
- **Like ratio** (the percentage from the Likes vs. dislikes column)

**Extracting video IDs programmatically**: If the table is rendered but you need the IDs, use JavaScript:

```javascript
const rows = document.querySelectorAll('ytcp-video-row');
const results = [];
rows.forEach(row => {
  const link = row.querySelector('a[href*="/video/"]');
  if (link) {
    const href = link.getAttribute('href');
    const match = href.match(/\/video\/([^/]+)/);
    if (match) {
      const title = row.querySelector('.video-title-wrapper a')?.textContent?.trim() ||
                    link.textContent?.trim() || '';
      results.push({ id: match[1], title });
    }
  }
});
JSON.stringify(results.slice(0, 10));
```

If fewer than 10 results, scroll down to load more rows and re-run the extraction.

**Assigning a topic:** For each video, assign a 2-3 word topic/theme based on the title. Common categories for YouTube:
- AI tools, automation, tutorial, vlog, product review, case study, how-to, breakdown, behind-the-scenes, collaboration, etc.

This single step gives you most of the data points needed per video. The remaining metrics (watch time, subscribers, impressions, CTR) require visiting each video's analytics page.

#### Step 3 — Collect Remaining Analytics (Overview + Reach tabs)

Now visit each video's analytics page to collect the metrics not available on the Content tab. Navigate directly — this is faster than clicking through the UI:

```
https://studio.youtube.com/video/{VIDEO_ID}/analytics
```

This loads the Overview tab by default.

**From the Overview tab, collect:**
- Watch time (hours)
- Subscribers gained (net new subscribers)

Take a screenshot and record these values.

**Then click the "Reach" tab** at the top of the analytics page.

**From the Reach tab, collect:**
- Impressions
- Impressions click-through rate (CTR %)
- Unique viewers (if shown — sometimes shows "--" or a warning icon)

Take a screenshot and record these values.

Repeat for all 10 videos. After collecting Overview data for a video, just click the Reach tab — don't navigate away and back.

#### Efficiency Tips

- The Content tab is the single most valuable page — it has views, comments, likes, dates, durations, and titles for every video. Always start here.
- Navigate directly to `studio.youtube.com/video/{ID}/analytics` for the per-video analytics. Much faster than clicking through the UI.
- After collecting Overview data, just click the Reach tab — don't navigate away and back.
- Batch your screenshots — take one per tab (Overview and Reach) rather than one per metric.
- If a metric isn't visible or shows as "--", record it as 0.

#### Step 4 — Compile the Data

After collecting all 10 videos' data, organize it into a JSON structure. Store it at a temporary path.

---

### Phase 2: Spreadsheet Generation

Once all 10 videos' data is collected, run the bundled Python script to generate the spreadsheet.

#### Prepare the Data

Create a JSON file with this structure:

```json
{
  "channel_name": "Channel Name Here",
  "videos": [
    {
      "post_num": 1,
      "title": "Full video title here",
      "date": "Feb 4, 2026",
      "duration": "31:25",
      "topic": "AI Marketing Tool",
      "views": 523,
      "watch_time_hours": 34.1,
      "subscribers": 5,
      "impressions": 3900,
      "ctr": 6.8,
      "unique_viewers": 379,
      "likes": 14,
      "comments": 7,
      "like_ratio": 100.0
    }
  ]
}
```

Field notes:
- `post_num`: 1 = most recent, 10 = oldest
- `duration`: Format as "MM:SS" or "H:MM:SS"
- `ctr`: The percentage value (e.g., 6.8 means 6.8%)
- For metrics that weren't available, use `0`
- `unique_viewers` and `like_ratio` are optional — set to 0 if not visible

#### Run the Script

```bash
python3 <skill-path>/scripts/build_yt_scorecard.py \
  <path-to-data.json> \
  "<output-path>/YT Scorecard.xlsx"
```

The script handles all calculations, ranking, color-coding, formatting, and content strategy generation automatically.

#### Present the Result

Share the file with the user using a computer:// link and include a brief summary:
- The top 3 winners with their key metrics and what made them work
- The bottom 3 losers and what held them back
- 2-3 of the most impactful action items from the Content Strategy tab

---

## Edge Cases

- **Not logged in**: Stop at Step 1 and ask the user to log in. Resume when they confirm.
- **Fewer than 10 videos**: Use however many are available. The script adjusts Winners/Losers thresholds proportionally (e.g., for 6 videos: top 2 winners, bottom 2 losers).
- **Metrics showing "--" or unavailable**: Record as 0. The script handles zeros gracefully.
- **Shorts vs long-form**: Both are included. The scoring system naturally differentiates since longer videos tend to accumulate more watch time and views. Note any Shorts in the topic field if relevant.
- **Analytics not yet available**: Very new videos (under 48 hours) may have incomplete analytics. Note this if encountered and consider using the next oldest video instead.
- **Multiple channels**: The skill works on whichever channel is active in YouTube Studio. If the user has multiple channels, they may need to switch channels in Studio first.
