import React from "react";
import { useCurrentFrame, interpolate, Easing, AbsoluteFill } from "remotion";

// ─── THEME ───────────────────────────────────────────────────────────────────
const THEME = {
  bg: "#0A0B14",
  bgMid: "#1A1B2F",
  accent: "#FF6B35",       // intense orange
  accentDim: "#FF9A5C",
  cyan: "#00F2FE",
  text: "#FFFFFF",
  dimText: "rgba(255,255,255,0.55)",
  gridLine: "rgba(255,107,53,0.05)",
};

// ─── HELPERS ─────────────────────────────────────────────────────────────────
const bezier = (x: number, y: number, z: number, w: number) =>
  Easing.bezier(x, y, z, w);
const SPRING = bezier(0.22, 1, 0.36, 1);
const EASE_OUT = bezier(0.16, 1, 0.3, 1);

const useKF = (
  frame: number,
  keyframes: { frame: number; [key: string]: any }[]
) => {
  let result: Record<string, number> = {};
  for (let i = 0; i < keyframes.length - 1; i++) {
    const kf = keyframes[i];
    const next = keyframes[i + 1];
    if (frame >= kf.frame && frame < next.frame) {
      const t = (frame - kf.frame) / (next.frame - kf.frame);
      for (const key of Object.keys(kf)) {
        if (key === "frame") continue;
        const from = kf[key] ?? 0;
        const to = next[key] ?? 0;
        result[key] = interpolate(t, [0, 1], [from, to], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: SPRING,
        });
      }
    }
  }
  return result;
};

// ─── COUNTDOWN ───────────────────────────────────────────────────────────────
const Countdown: React.FC<{ frame: number }> = ({ frame }) => {
  // 4→3→2→1 each 20 frames, then vanish
  const counts = [
    { val: "4", start: 0, end: 20 },
    { val: "3", start: 20, end: 40 },
    { val: "2", start: 40, end: 60 },
    { val: "1", start: 60, end: 80 },
    { val: "", start: 80, end: 100 },
  ];
  const active = counts.find((c) => frame >= c.start && frame < c.end);
  if (!active) return null;

  const t = (frame - active.start) / (active.end - active.start);
  const scale = interpolate(t, [0, 0.3, 0.7, 1], [0.3, 1.4, 1.1, 1], { easing: SPRING });
  const opacity = interpolate(t, [0, 0.1, 0.8, 1], [0, 1, 1, 0.9]);

  return (
    <div
      style={{
        position: "absolute",
        top: "50%",
        left: "50%",
        transform: `translate(-50%, -50%) scale(${scale})`,
        opacity,
        fontSize: "320px",
        fontWeight: 900,
        color: THEME.accent,
        fontFamily: "Poppins, sans-serif",
        letterSpacing: "-0.06em",
        textShadow: `0 0 100px ${THEME.accent}, 0 0 200px ${THEME.accentDim}66`,
        userSelect: "none",
        lineHeight: 1,
      }}
    >
      {active.val}
    </div>
  );
};

// ─── MAIN HOOK TEXT ──────────────────────────────────────────────────────────
const HookText: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = useKF(frame, [
    { frame: 80, opacity: 0, scale: 0.7, y: 60 },
    { frame: 100, opacity: 1, scale: 1, y: 0 },
  ]);
  const opacity = kf.opacity ?? 0;
  const scale = kf.scale ?? 1;
  const y = kf.y ?? 0;

  return (
    <div
      style={{
        position: "absolute",
        top: "28%",
        left: "50%",
        transform: `translate(-50%, calc(-50% + ${y}px)) scale(${scale})`,
        opacity,
        textAlign: "center",
        maxWidth: "900px",
        width: "100%",
        padding: "0 40px",
      }}
    >
      {/* "4 DAYS" — massive, tight */}
      <div
        style={{
          fontSize: "180px",
          fontWeight: 900,
          color: THEME.text,
          fontFamily: "Poppins, sans-serif",
          letterSpacing: "-0.06em",
          lineHeight: 0.85,
          textShadow: `0 0 80px ${THEME.accent}44`,
        }}
      >
        4 DAYS
      </div>
      {/* subtitle */}
      <div
        style={{
          marginTop: 16,
          fontSize: "36px",
          fontWeight: 700,
          color: THEME.accent,
          fontFamily: "Poppins, sans-serif",
          letterSpacing: "-0.02em",
          textShadow: `0 0 40px ${THEME.accent}66`,
        }}
      >
        NOOB → CLAUDE PRO
      </div>
      {/* tagline */}
      <div
        style={{
          marginTop: 24,
          fontSize: "22px",
          fontWeight: 400,
          color: THEME.dimText,
          fontFamily: "Inter, sans-serif",
          letterSpacing: "0.01em",
        }}
      >
        Use this roadmap. 4 days from now, you can go from noob to Claude Pro.
      </div>
    </div>
  );
};

// ─── TIMELINE SLIDER ─────────────────────────────────────────────────────────
const TimelineSlider: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = useKF(frame, [
    { frame: 105, opacity: 0, y: 40 },
    { frame: 115, opacity: 1, y: 0 },
  ]);
  const opacity = kf.opacity ?? 0;
  const y = kf.y ?? 0;

  const progress = interpolate(frame, [115, 145], [0, 100], {
    extrapolateRight: "clamp",
    easing: EASE_OUT,
  });

  return (
    <div
      style={{
        position: "absolute",
        bottom: "18%",
        left: "50%",
        transform: `translate(-50%, ${y}px)`,
        opacity,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 10,
      }}
    >
      {/* day labels */}
      <div
        style={{
          display: "flex",
          gap: 0,
          fontFamily: "Inter, sans-serif",
          fontSize: 13,
          fontWeight: 600,
          color: THEME.dimText,
          letterSpacing: "0.05em",
        }}
      >
        {["DAY 0", "DAY 1", "DAY 2", "DAY 3", "DAY 4"].map((d, i) => (
          <div
            key={d}
            style={{
              width: 100,
              textAlign: "center",
              color: i <= Math.floor((progress / 100) * 4) ? THEME.accent : THEME.dimText,
              textShadow: i <= Math.floor((progress / 100) * 4) ? `0 0 20px ${THEME.accent}` : "none",
              transition: "color 0.3s",
            }}
          >
            {d}
          </div>
        ))}
      </div>
      {/* track */}
      <div
        style={{
          width: 500,
          height: 8,
          background: "rgba(255,255,255,0.08)",
          borderRadius: 4,
          overflow: "hidden",
          position: "relative",
        }}
      >
        <div
          style={{
            height: "100%",
            width: `${progress}%`,
            background: `linear-gradient(90deg, ${THEME.accent}, ${THEME.accentDim})`,
            borderRadius: 4,
            boxShadow: `0 0 20px ${THEME.accent}`,
          }}
        />
      </div>
    </div>
  );
};

// ─── GRID BACKGROUND ─────────────────────────────────────────────────────────
const GridBg: React.FC = () => (
  <div
    style={{
      position: "absolute",
      inset: 0,
      backgroundImage: `
        linear-gradient(${THEME.gridLine} 1px, transparent 1px),
        linear-gradient(90deg, ${THEME.gridLine} 1px, transparent 1px)
      `,
      backgroundSize: "60px 60px",
      backgroundColor: THEME.bg,
    }}
  />
);

// ─── SCENE 1 ROOT ────────────────────────────────────────────────────────────
const Scene1_Hook: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill>
      <GridBg />
      {/* radial vignette */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `radial-gradient(ellipse at 50% 40%, transparent 30%, ${THEME.bg} 80%)`,
          pointerEvents: "none",
        }}
      />
      <Countdown frame={frame} />
      <HookText frame={frame} />
      <TimelineSlider frame={frame} />
    </AbsoluteFill>
  );
};

export default Scene1_Hook;