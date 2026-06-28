import "./index.css";
import React from "react";
import { Composition } from "remotion";
import ChronixelMotionSystem from "./ChronixelMotionSystem";
import {
  FourDayClaude,
  Scene1Hook_comp,
  Scene2Day1_comp,
  Scene3Day2_comp,
  Scene4Day3_comp,
  Scene5Day4_comp,
} from "./4DayClaude";

export const RemotionRoot: React.FC = () => {
  return (
    <>
      {/* ── Chronixel Motion System Reference Still ── */}
      <Composition
        id="ChronixelMotionSystem"
        component={ChronixelMotionSystem}
        durationInFrames={150}
        fps={30}
        width={1920}
        height={1080}
      />

      {/* ── 4DayClaude — FULL 90s Timeline (all 5 scenes in one comp) ── */}
      <Composition
        id="4DayClaude"
        component={FourDayClaude}
        durationInFrames={2700}
        fps={30}
        width={1920}
        height={1080}
      />

      {/* ── Individual scene stubs — per-scene scrubbing in Studio ── */}
      <Composition
        id="4DayClaude-Day1-Scene"
        component={Scene1Hook_comp}
        durationInFrames={151}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="4DayClaude-Day1-Scene2"
        component={Scene2Day1_comp}
        durationInFrames={1050}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="4DayClaude-Day2-Scene3"
        component={Scene3Day2_comp}
        durationInFrames={450}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="4DayClaude-Day3-Scene4"
        component={Scene4Day3_comp}
        durationInFrames={600}
        fps={30}
        width={1920}
        height={1080}
      />
      <Composition
        id="4DayClaude-Day4-Scene5"
        component={Scene5Day4_comp}
        durationInFrames={450}
        fps={30}
        width={1920}
        height={1080}
      />
    </>
  );
};
