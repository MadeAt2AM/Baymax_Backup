import React from "react";
import { AbsoluteFill, Sequence } from "remotion";
import Scene1_Hook from "./Scene1_Hook";
import Scene2_WrongWorkflow from "./Scene2_WrongWorkflow";
import Scene3_Day1 from "./Scene3_Day1";
import Scene4_Day2 from "./Scene4_Day2";
import Scene5_Day3 from "./Scene5_Day3";
import Scene6_Day4 from "./Scene6_Day4";
import Scene7_Outro from "./Scene7_Outro";

// ─── FULL TIMELINE ────────────────────────────────────────────────────────────
// Total: 30fps × 60s = 1800 frames
//
// Frame mapping:
//   0 – 165  ( 0s–5.5s)  → Scene 1: Hook / Countdown
// 165 – 465  (5.5s–15.5s) → Scene 2: The Wrong Workflow
// 465 – 765  (15.5s–25.5s)→ Scene 3: Day 1 – Create Your Projects
// 765 – 1065 (25.5s–35.5s)→ Scene 4: Day 2 – Claude Cowork
// 1065 – 1365 (35.5s–45.5s)→ Scene 5: Day 3 – Connect Your Tools
// 1365 – 1665 (45.5s–55.5s)→ Scene 6: Day 4 – Claude Code
// 1665 – 1800 (55.5s–60s)  → Scene 7: Outro / CTA

export const Composition: React.FC = () => (
  <AbsoluteFill style={{ background: "#0A0B14" }}>
    <Sequence from={0} durationInFrames={209} name="1-Hook">
      <Scene1_Hook />
    </Sequence>
    <Sequence from={207} durationInFrames={300} name="2-WrongWorkflow">
      <Scene2_WrongWorkflow />
    </Sequence>
    <Sequence from={465} durationInFrames={300} name="3-Day1">
      <Scene3_Day1 />
    </Sequence>
    <Sequence from={765} durationInFrames={300} name="4-Day2">
      <Scene4_Day2 />
    </Sequence>
    <Sequence from={1065} durationInFrames={300} name="5-Day3">
      <Scene5_Day3 />
    </Sequence>
    <Sequence from={1365} durationInFrames={300} name="6-Day4">
      <Scene6_Day4 />
    </Sequence>
    <Sequence from={1665} durationInFrames={135} name="7-Outro">
      <Scene7_Outro />
    </Sequence>
  </AbsoluteFill>
);
