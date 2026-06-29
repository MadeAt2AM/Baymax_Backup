import "./index.css";
import React from "react";
import { Composition as RemotionComp } from "remotion";
import { Composition as MainComp } from "./Composition";
import Scene1_Hook from "./Scene1_Hook";
import Scene2_WrongWorkflow from "./Scene2_WrongWorkflow";
import Scene3_Day1 from "./Scene3_Day1";
import Scene4_Day2 from "./Scene4_Day2";
import Scene5_Day3 from "./Scene5_Day3";
import Scene6_Day4 from "./Scene6_Day4";
import Scene7_Outro from "./Scene7_Outro";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* ── FULL 60s VIDEO ─────────────────────────────────────────────── */}
      <RemotionComp
        id="4DayClaude"
        component={MainComp}
        durationInFrames={1800}
        fps={30}
        width={1920}
        height={1080}
      />

      {/* ── INDIVIDUAL SCENE STUBS — per-scene scrubbing in Studio ─────────── */}
      <RemotionComp
        id="Scene1-Hook"
        component={Scene1_Hook}
        durationInFrames={165}
        fps={30}
        width={1920}
        height={1080}
      />
      <RemotionComp
        id="Scene2-WrongWorkflow"
        component={Scene2_WrongWorkflow}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
      />
      <RemotionComp
        id="Scene3-Day1"
        component={Scene3_Day1}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
      />
      <RemotionComp
        id="Scene4-Day2"
        component={Scene4_Day2}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
      />
      <RemotionComp
        id="Scene5-Day3"
        component={Scene5_Day3}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
      />
      <RemotionComp
        id="Scene6-Day4"
        component={Scene6_Day4}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
      />
      <RemotionComp
        id="Scene7-Outro"
        component={Scene7_Outro}
        durationInFrames={135}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
