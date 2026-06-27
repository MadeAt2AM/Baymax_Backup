---
name: ig-scorecard
description: >
  Build an Instagram Scorecard analyzing any account's last 10 posts. Navigates to Instagram
  in the browser, collects post metrics (likes, comments, saves, shares, views, reach) via
  View Insights, captures full captions and visual context, ranks posts by engagement rate,
  and outputs a .xlsx with Full Scorecard, Winners Analysis, Losers Analysis, Key Takeaways,
  and Content Strategy tabs with action items on what to double down on, improve, and cut.
  Use this skill whenever the user mentions: content scorecard, Instagram audit, post performance,
  analyze my Instagram, IG analytics, which posts performed best, Instagram report, rank my posts,
  score my content, content review, social media audit, how are my posts doing, analyze my reels,
  top performing posts, worst performing posts, IG report, content strategy, what should I post
  more of, what content is working. Even casual requests like "check how my Instagram is doing"
  or "which of my posts hit" should trigger this skill.
---

# Instagram Scorecard

This skill automates the full process of collecting Instagram post metrics via the browser and producing a professional Scorecard spreadsheet with actionable content strategy. It works on whatever Instagram account is currently signed in.

## Overview

The scorecard analyzes the **10 most recent posts** (by date) and produces a 5-tab .xlsx file:
1. **Full Scorecard** — all 10 posts ranked by engagement rate with color-coded status
2. **Winners Analysis** — deep dive on the top 3 posts with "Why It Worked" analysis
3. **Losers Analysis** — deep dive on the bottom 3 posts with "Why It Underperformed" analysis
4. **Key Takeaways** — averages, best/worst content types, and high-level recommendations
5. **Content Strategy** — specific action items: what to double down on, what to iterate/improve, and what to cut, grounded in the actual content context of each post

The Content Strategy tab is what makes this more than just a numbers report. By capturing what each post is actually about (full captions + what the visual shows), the strategy recommendations reference specific content angles, hooks, formats, and topics — not just generic "post more of X type."

## Workflow

There are two phases: **data collection** (browser) and **spreadsheet generation** (Python script). The browser phase is the bottleneck, so the instructions below are optimized to minimize clicks and page loads.

---

### Phase 1: Data Collection (Browser)

#### Step 1 — Navigate to Profile

1. Get browser tab context (`tabs_context_mcp`, create if empty)
2. Navigate to `https://www.instagram.com`
3. Take a screenshot to confirm login
4. If not logged in: **stop and tell the user** to log in, then continue once they confirm
5. Use `find` to locate the "Profile" link in the sidebar, then click it
6. Confirm you're on the profile page (you'll see the username, follower count, post grid)
7. Note the **username** from the page URL or header — you'll need it for the spreadsheet

#### Step 2 — Extract All Post URLs from the Grid

Instead of clicking posts one by one from the grid and navigating back each time, extract all the post URLs at once using JavaScript, then visit each directly.

First, scroll the profile page enough to load at least 15+ posts (to have a comfortable buffer). You may need to scroll multiple times if posts are lazy-loaded. Use `window.scrollTo(0, Y)` with increasing Y values, waiting a second between scrolls.

Then run this JavaScript to get all post URLs from the grid:

```javascript
const allLinks = document.querySelectorAll('a[href*="/p/"], a[href*="/reel/"]');
const results = [];
for (const a of allLinks) {
  const href = a.getAttribute('href');
  if (!results.some(r => r.href === href)) {
    results.push({ href });
  }
}
JSON.stringify(results);
```

This gives you all unique post/reel URLs visible on the profile. The grid shows posts in a mix of pinned-first then reverse-chronological order, but you should **not** try to figure out which are pinned from the grid. Instead, you'll determine recency by checking dates when you visit each post.

#### Step 2b — Visit Posts and Select the 10 Most Recent by Date

The profile grid puts pinned posts first, then non-pinned posts in reverse chronological order. Since pinned posts can be old or recent, the grid order alone doesn't tell you which 10 are most recent — you need to check dates.

**Strategy:** Visit posts from the extracted URL list one by one, starting from the top. For each post, note the date. Collect posts until you have 10, then check if any remaining unvisited posts could be newer (they won't be, because after the pinned section, the grid is strictly reverse-chronological — so once you've seen 10 posts and the dates are decreasing, you're done).

In practice, this means:
1. Visit each URL in grid order
2. Record the date shown on each post (e.g., "1 day ago", "February 12", "3w")
3. After visiting ~13 posts (a safe buffer), you'll have enough to pick the 10 most recent by date
4. Sort your collected posts by date and take the top 10

**Why 13?** Instagram allows a maximum of 3 pinned posts. So the worst case is 3 pinned posts from months ago sitting at the top of the grid, followed by the actual recent posts. Visiting 13 guarantees you've seen at least 10 non-pinned recent posts even in that worst case. If a pinned post happens to be recent enough to land in the top 10 by date, that's fine — include it.

**Optimization:** As you visit posts, you can stop early if you've already collected 10 posts and the dates are clearly getting older. For example, if your 10th newest post is from Feb 4 and the post you just visited is from Jan 15, you don't need to keep going.

#### Step 3 — Collect Metrics AND Content Context for Each Post

This is where the updated skill differs from a basic scorecard. For each post, you're collecting two things: the **numbers** (metrics) and the **context** (what the post is actually about). Both happen in the same visit — no extra navigation needed.

For each of the 10 most recent post URLs (by date), do this sequence:

1. **Navigate directly** to the post URL (e.g., `https://www.instagram.com/p/ABC123/`)
2. **Take a screenshot** to capture the post visual
3. **Extract content context** from the page:
   - **Full caption text**: Grab the complete caption, not just a preview. If the caption is truncated with a "more" button, click it to expand first. Use JavaScript to extract: `document.querySelector('h1')?.textContent` or look for the caption element. Capture the entire thing — this is critical for the Content Strategy tab.
   - **Visual description**: Based on the screenshot you just took, write a 1-2 sentence description of what the visual shows. For Reels, describe the thumbnail/cover frame. Examples: "Talking head with text overlay showing '5 AI Tools'", "Screen recording of ChatGPT workflow", "Lifestyle shot at coffee shop with motivational quote overlay", "Before/after comparison of Instagram analytics". This doesn't need to be fancy — just enough context to know what the viewer sees.
   - **Date posted**
   - **Content type**: check for "Boost reel" button (= Reel), carousel dots (= Carousel), or neither (= Single Image)
   - **Like count** (visible on the post)
4. **Click "View insights"** — use `find` to locate the button, then click it
5. **Take a screenshot** of the insights panel
6. **Record all metrics** from the insights panel:
   - Views (for Reels)
   - Accounts reached
   - Likes
   - Comments
   - Saves
   - Shares
   - (These are clearly labeled in the insights panel)
7. **Close insights** by clicking the X button (top-left), which returns you to the profile
8. Move to the next post URL

**Combine Steps 2b and 3:** To avoid visiting each post twice (once to check the date, once to collect metrics), do both in a single pass. Visit each post, note the date AND collect its full metrics + content context via View Insights right away. After ~13 posts, stop, sort by date, and keep the 10 most recent for the spreadsheet.

**If "View insights" is not available** (e.g., viewing someone else's profile or a non-business account), collect whatever metrics are publicly visible: likes and comments from the post page. Mark shares, saves, views, and reach as "N/A".

#### Efficiency Tips

- Navigate directly to post URLs instead of clicking thumbnails in the grid. This avoids the scroll-back-and-find-the-right-post problem entirely.
- After closing insights, Instagram returns to the profile page. You can navigate to the next post URL immediately.
- If the insights page loads at a URL like `/insights/media/...`, closing it (clicking X) takes you back to the profile. Alternatively, just navigate directly to the next post URL — no need to go back to the profile at all.
- Use `find` for "View insights" buttons rather than coordinate-based clicks — it's more reliable across different screen sizes.
- Expanding the caption ("more" button) and taking the screenshot are things you're already doing — the visual description is just you writing down what you saw. Zero extra clicks.

#### Step 4 — Determine Post Topics

For each post, assign a 2-3 word topic/theme based on the full caption content and visual description. Common categories:
- AI tools, AI automation, content strategy, financial breakdown, lifestyle/vlog, lifestyle/fashion, product review, tutorial, motivational, behind-the-scenes, collaboration, giveaway, etc.

---

### Phase 2: Spreadsheet Generation

Once all 10 posts' data is collected, run the bundled Python script to generate the spreadsheet.

#### Prepare the Data

Create a JSON file at `/sessions/sharp-inspiring-mayer/post_data.json` with this structure:

```json
{
  "username": "jasoncooperson",
  "posts": [
    {
      "post_num": 1,
      "date": "Feb 21, 2026",
      "type": "Reel",
      "topic": "AI Content Strategy",
      "caption_preview": "Most people overthink content strategy...",
      "full_caption": "Most people overthink content strategy. Here's what actually works: 1. Pick ONE platform 2. Post daily for 30 days 3. Track what gets saves (not likes) 4. Double down on your top 3 formats. That's it. Stop consuming content about content strategy and start making content. The algorithm rewards consistency over perfection every single time. Save this for later. What platform are you going all-in on? Drop it below.",
      "visual_description": "Talking head to camera with text overlay '5 Steps to Fix Your Content Strategy'. Clean background, direct eye contact, animated text appearing with each point.",
      "likes": 272,
      "comments": 149,
      "saves": 231,
      "shares": 91,
      "views": 6306,
      "reach": 3684
    }
  ]
}
```

- `post_num`: 1 = most recent, 10 = oldest (sorted by date, not grid position)
- For metrics that weren't available, use `0` or `null`
- `views` should be 0 for non-Reel posts where views aren't shown
- `reach` should be 0 if insights weren't accessible
- `full_caption`: The complete caption text. This is what powers the Content Strategy tab — don't truncate it.
- `visual_description`: Your 1-2 sentence description of what the post visual shows. The Content Strategy tab uses this to understand format and presentation style, not just topic.

#### Run the Script

```bash
python3 <skill-path>/scripts/build_scorecard.py \
  /sessions/sharp-inspiring-mayer/post_data.json \
  "/sessions/sharp-inspiring-mayer/mnt/outputs/IG Scorecard.xlsx"
```

The script handles all calculations, ranking, color-coding, formatting, and content strategy generation automatically.

#### Present the Result

Share the file with the user using a computer:// link and include a brief summary:
- The top 3 winners with their engagement rates
- The bottom 3 losers
- 2-3 of the most impactful action items from the Content Strategy tab

---

## Edge Cases

- **Not logged in**: Stop at Step 1 and ask the user to log in. Resume when they confirm.
- **Private account / no insights**: Collect publicly visible metrics only (likes, comments). Note the limitation in the spreadsheet. The Content Strategy tab can still work with caption + visual context alone.
- **Fewer than 10 posts**: Use however many are available. Adjust the Winners/Losers thresholds proportionally (e.g., for 6 posts: top 2 winners, bottom 2 losers, middle 2 average).
- **Sponsored/ad posts**: Skip these — they don't count toward the 10. Look for "Paid partnership" or "Sponsored" labels.
- **Carousel posts**: These won't have "Views" — use Reach for engagement rate instead, or just rank by Total Engagements.
- **All Reels**: If all 10 posts are Reels (common for many creators), note this in Key Takeaways and focus the content type analysis on topics/themes instead.
- **Very short captions**: Some posts may have minimal captions (just emojis or a single line). That's fine — the visual description fills in the context gap for the Content Strategy analysis.
