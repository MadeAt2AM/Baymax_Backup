# Niche Guide: Cybersecurity & Ethical Hacking

## Audience Psychology

Cybersecurity/ethical hacking viewers are:
- **Intellectually curious and skeptical** — they distrust hype and respect accuracy
- **Action-oriented** — they want to DO something, not just know something
- **Community-proud** — they self-identify as "hackers" (in the positive sense), CTF players, red teamers, or bug bounty hunters
- **Alert to BS** — they will fact-check you; incorrect technical details destroy credibility fast
- **Motivated by two things**: career advancement (certs, jobs, bug bounties) OR pure curiosity/the thrill

**Two audience segments** to write for differently:
1. **Beginners/career switchers** — want clear explanations, real career impact, practical first steps
2. **Intermediate/advanced practitioners** — want depth, real lab demos, novel angles, respect for their time

Decide which segment you're writing for BEFORE the hook. Don't try to serve both equally — it dilutes the message.

---

## Channel Tone Reference

Study these channels for tone calibration:

| Channel | Tone | What Works |
|---|---|---|
| **NetworkChuck** | High energy, motivational, beginner-friendly | Makes dry topics feel fun; strong "why should I care" framing |
| **John Hammond** | Calm but sharp, real-time problem-solving, CTF-focused | Authenticity + thinking out loud; viewers learn his process |
| **The Cyber Mentor** | Structured, direct, career-focused | No fluff; respects viewer's time; strong practical application |
| **LiveOverflow** | Deep, technical, conceptual | Explains the "why" behind vulnerabilities, not just the "how" |
| **STÖK** | Fun, vlog-style, bug bounty energy | Mixes lifestyle with hacking; high-energy personality |
| **David Bombal** | Interview-heavy, networking + hacking blend | Credibility-building through guests; practical labs |

---

## Hook Examples — Cybersecurity Niche

**Direct Hook:**
- "If you're a developer who thinks HTTPS makes your app secure — sit down, we need to talk."
- "You passed your CompTIA Security+. Congrats. Now let me show you what it didn't teach you."
- "If you're trying to break into cybersecurity with zero experience, most roadmaps are lying to you."

**Controversy Hook:**
- "The best hackers I know don't use Kali Linux."
- "Most bug bounty programs are designed to pay you as little as possible. Here's how they do it."
- "Your company's firewall isn't protecting you from the attack I'm about to demonstrate."
- "The most dangerous vulnerability in your network probably isn't technical."

**Negative Hook:**
- "Stop trying to learn hacking from YouTube tutorials. Do this instead."
- "Never use these tools on a bug bounty program if you actually want to get paid."
- "Don't set up your home lab like this. I spent six months doing it the wrong way."

---

## Intro Example — Cybersecurity

**Topic: "How SQL Injection Actually Works"**

> In 2024, SQL injection was still in the OWASP Top 10. It's been on that list for over 20 years. That's not because developers are stupid — it's because nobody actually explains how it works from the attacker's perspective. Most tutorials show you the fix without showing you the attack. So in this video, we're doing it differently. I'm going to show you exactly how an attacker finds a vulnerable endpoint, what they inject, what happens inside the database, and then — yeah, we'll fix it. By the end of this, you'll be able to spot SQLi in a codebase in under a minute.

---

## Body Section Examples — Cybersecurity

### Example 1: Breaking down a concept (for beginner audience)

**Topic: "What is a Buffer Overflow?"**

> Think of memory like a row of parking spaces. Each one holds exactly one car. Now imagine someone tries to park a monster truck in a space meant for a sedan. It doesn't fit. It spills into the next space. And the one after that.
>
> That's a buffer overflow.
>
> A buffer is just a fixed-size chunk of memory. When a program stores more data than the buffer can hold, that data spills into adjacent memory — memory that belongs to something else. Maybe another variable. Maybe — and this is the scary part — the part of memory that tells the program what to do next.
>
> And when attackers control that part? They can make the program do whatever they want.

### Example 2: Real-world stakes (for intermediate audience)

**Topic: "Privilege Escalation on Linux"**

> Here's the thing about privilege escalation that nobody explains well: it's rarely about finding some exotic zero-day. Most of the time it's SUID binaries, misconfigured sudo rules, or world-writable cron jobs. Stuff that's just... sitting there. Forgotten.
>
> On a real pentest, I've gotten root in under three minutes using nothing but `find / -perm -4000 2>/dev/null` and GTFOBins. Three minutes. On a production server that had been running for four years.
>
> So let me walk you through the systematic approach — how I check for quick wins first, and when to go deeper.

---

## Full Skeleton Example — Cybersecurity

**Video Title: "I Tried Every Beginner Hacking Course — Here's the Truth"**

### Hook
What to include: Controversial claim about popular courses
What viewer expects: Someone who's actually done the research, not just an opinion
How to present: Start with the most unexpected finding
Reference: Name specific well-known courses (TCM Security, TryHackMe, HTB, SANS)
Example: "I spent three months taking every beginner cybersecurity course I could find. Some are worth every dollar. Some are a total waste of your time. And one — one I'm going to name specifically — might actually be setting you back."

### The Problem with Most Courses
What to include: What courses get wrong (theory-heavy, no lab time, no real-world context)
What viewer expects: Specific, credible criticism — not vague complaints
How to present: "Here's what they teach vs. what you actually need"
Reference: Mention the gap between CompTIA/cert content and real pentesting skills
Example: "Most beginner courses will teach you what a buffer overflow is. Zero of them will make you actually exploit one. And there's a massive difference between knowing and doing."

### The Ranking + Breakdown
What to include: 4–5 courses reviewed with honest pros/cons
What viewer expects: Specific details — price, time commitment, what you actually learn
How to present: Mini-reviews per course, not a feature list — tell a story about using each one
Reference: TryHackMe, HackTheBox Academy, TCM Security courses, SANS (briefly — cost context)
Example: "TryHackMe is where I'd send literally every single beginner. Not because it's the most advanced — it's not. But because it teaches you how to think, not just what to memorize."

### The Verdict + Roadmap
What to include: Specific recommended path for different goals (career vs. curiosity)
What viewer expects: A clear answer — what should I do next?
How to present: Split by goal: "If you want a job in 12 months, do this. If you want to start doing bug bounties, do this."
Example: "If your goal is to get hired, stop watching videos and start doing labs. Certifications open doors. Labs are what actually close them."

### CTA
Example: "I made a full video breaking down the exact 6-month roadmap I'd follow if I were starting from zero today — it's right here."

---

## Full Script Example — Cybersecurity (Short Form ~800 words)

**Title: "Stop Learning Cybersecurity Like This"**

---

If you're learning cybersecurity by watching tutorials, you're probably going to be stuck for a very long time.

And I don't mean "tutorials are bad." I mean most people use them wrong — and there's a specific way they use them that keeps them spinning their wheels for months without actually getting better.

Here's what's happening.

When you watch a tutorial, your brain feels productive. You're learning. You're taking notes. You understand what the instructor is doing. And then you close the video, open a terminal, and you can't replicate a single step without looking it up again.

This is called the illusion of competence. You recognized the information — but you never encoded it. And in cybersecurity, there's only one way to actually encode it: doing it yourself, breaking it, and figuring out why.

The fix is embarrassingly simple. After every tutorial you watch, close the tab. Don't look at the video again. Try to recreate exactly what you just saw from memory. You'll fail. That's fine. The failure is literally the learning. Every time you get stuck and have to figure out why, your brain builds a connection it wasn't going to build from watching alone.

But here's the bigger problem.

Most beginners spend 80% of their time consuming content and 20% of their time doing labs. The ratio needs to be completely flipped.

The people I know who broke into cybersecurity fast — not in five years, in 12 to 18 months — all had one thing in common. They were doing something actively every single day. TryHackMe rooms, HackTheBox challenges, building their own vulnerable VMs, writing tools in Python. The tutorials were supplements, not the main course.

Now, which platforms should you actually be on?

For absolute beginners: TryHackMe. It holds your hand just enough to not make you want to quit, but it throws you into actual labs immediately. Don't just do the free rooms — get the subscription for at least one month and work through the learning paths.

Once you've got the basics: HackTheBox. This is where the learning gets real. The difficulty spike is significant. That's the point.

For people who want a job: TCM Security's courses — especially the Practical Ethical Hacking course — are the closest thing I've seen to actual job training at a non-insane price. Heath Adams built those courses to mirror what pentesting work actually looks like, not just what the certification exam tests you on.

And speaking of certifications — the OSCP is still the gold standard if you want to work in offensive security. But don't go near it until you've done at least 50 HackTheBox machines and you understand what you're getting into. It's a 24-hour hands-on exam. There's no multiple choice. You either pop the boxes or you don't.

Here's my honest take on the path:

TryHackMe learning paths → HackTheBox easy/medium machines → TCM PEH course → OSCP or eJPT depending on your goal.

That's not the only path. But it's the one I've seen work most consistently.

The thing nobody tells you is that the first three months feel terrible. You're going to hit walls constantly. You're going to feel like everyone else gets it except you. That's normal. That's what learning a genuinely hard skill feels like. The people who push through that phase are the ones who make it.

One more thing before I let you go.

Stop hoarding resources. Stop building a massive Notion database of courses you're going to take someday. Pick one platform, one path, and do it until it's done. Then pick the next thing.

The best cybersecurity professionals I know aren't the ones who read the most. They're the ones who broke the most things.

Go break something.

I put together a full 6-month roadmap — specific resources, in order, with timelines — and it's in the video right here.

---

## Cybersecurity-Specific Language Tips

- Use technical terms correctly — your audience will notice errors
- Don't over-explain terms to an advanced audience (it's condescending)
- But DO explain acronyms on first use even for intermediate audiences (not everyone knows every cert)
- Real examples > hypotheticals — "I found this on a pentest" beats "imagine a scenario where"
- Mention real tools by name: Burp Suite, Metasploit, Nmap, Wireshark, Gobuster, Bloodhound, etc.
- CTF culture is real — reference it, respect it, but don't assume everyone does CTFs
- Bug bounty mindset is different from pentest mindset — don't conflate them
