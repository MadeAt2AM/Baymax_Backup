import React from "react";
import { useCurrentFrame, interpolate, Easing, AbsoluteFill } from "remotion";

const THEME = {
  bg: "#0A0B14",
  bgMid: "#1A1B2F",
  accent: "#FF6B35",
  text: "#FFFFFF",
  dimText: "rgba(255,255,255,0.55)",
  warning: "#FF4444",
};

const SPRING = Easing.bezier(0.22, 1, 0.36, 1);

// ─── CHAOTIC NEW CHAT WINDOW ─────────────────────────────────────────────────
const ChaoticWindow: React.FC<{
  frame: number;
  startFrame: number;
  x: number; y: number;
  w: number; h: number;
  rot: number;
  opacity: number;
}> = ({ frame, startFrame, x, y, w, h, rot, opacity }) => {
  const t = interpolate(frame, [startFrame, startFrame + 30], [0, 1], { extrapolateRight: "clamp", easing: SPRING });
  return (
    <div
      style={{
        position: "absolute",
        left: `${x}%`,
        top: `${y}%`,
        width: w,
        height: h,
        transform: `translate(-50%, -50%) rotate(${rot}deg) scale(${t * 0.9 + 0.1})`,
        opacity: opacity * t,
        background: "rgba(26,27,47,0.92)",
        border: "1px solid rgba(255,255,255,0.15)",
        borderRadius: 12,
        backdropFilter: "blur(8px)",
        overflow: "hidden",
        boxShadow: "0 8px 40px rgba(0,0,0,0.6)",
      }}
    >
      {/* header */}
      <div style={{ height: 32, background: "rgba(255,255,255,0.05)", borderBottom: "1px solid rgba(255,255,255,0.08)", display: "flex", alignItems: "center", paddingLeft: 12, gap: 6 }}>
        <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#FF5F57" }} />
        <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#FFBD2E" }} />
        <div style={{ width: 10, height: 10, borderRadius: "50%", background: "#28CA41" }} />
        <div style={{ marginLeft: 8, color: "rgba(255,255,255,0.4)", fontSize: 12, fontFamily: "Inter, sans-serif" }}>New Chat</div>
      </div>
      {/* messy lines */}
      <div style={{ padding: "10px 14px", display: "flex", flexDirection: "column", gap: 6 }}>
        {["upload document", "re-explain context", "repeat again", "upload again"].map((txt, i) => (
          <div key={i} style={{ height: 8, background: `rgba(255,255,255,${0.06 + i * 0.02})`, borderRadius: 4, width: `${50 + i * 12}%` }} />
        ))}
      </div>
    </div>
  );
};

// ─── DOTTED UPLOAD LINE ──────────────────────────────────────────────────────
const UploadDots: React.FC<{ frame: number }> = ({ frame }) => {
  const DOTS = 12;
  const active = frame < 120;
  if (!active) return null;

  return (
    <div style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
      {Array.from({ length: DOTS }).map((_, i) => {
        const progress = ((frame * 0.04 + i * 0.08) % 1);
        const x = 10 + progress * 80;
        const y = 40 + Math.sin(progress * Math.PI * 2 + i) * 20;
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: `${x}%`,
              top: `${y}%`,
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: THEME.accent,
              opacity: 0.5 + Math.sin(progress * Math.PI) * 0.4,
              boxShadow: `0 0 8px ${THEME.accent}`,
            }}
          />
        );
      })}
    </div>
  );
};

// ─── WARNING PULSE ───────────────────────────────────────────────────────────
const WarningPulse: React.FC<{ frame: number }> = ({ frame }) => {
  const pulse = (Math.sin(frame * 0.15) + 1) / 2;
  return (
    <div
      style={{
        position: "absolute",
        top: "8%",
        right: "8%",
        width: 48,
        height: 48,
        borderRadius: "50%",
        border: `2px solid ${THEME.warning}`,
        opacity: 0.5 + pulse * 0.5,
        boxShadow: `0 0 ${20 + pulse * 20}px ${THEME.warning}66`,
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      <div style={{ color: THEME.warning, fontSize: 24, fontWeight: 900, fontFamily: "Inter, sans-serif" }}>!</div>
    </div>
  );
};

// ─── DAY LABEL ───────────────────────────────────────────────────────────────
const DayLabel: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = interpolate(frame, [10, 25], [0, 1], { extrapolateRight: "clamp", easing: Easing.bezier(0.16, 1, 0.3, 1) });
  return (
    <div
      style={{
        position: "absolute",
        top: "8%",
        left: "50%",
        transform: `translateX(-50%) translateY(${(1 - kf) * -30}px)`,
        opacity: kf,
        textAlign: "center",
      }}
    >
      <div style={{ fontSize: 14, fontWeight: 700, color: THEME.dimText, fontFamily: "Inter, sans-serif", letterSpacing: "0.15em", textTransform: "uppercase" }}>
        Day 1 — The Wrong Workflow
      </div>
    </div>
  );
};

// ─── SCENE 2 ROOT ────────────────────────────────────────────────────────────
const Scene2_WrongWorkflow: React.FC = () => {
  const frame = useCurrentFrame();

  const windows = [
    { startFrame: 15, x: 25, y: 30, w: 280, h: 180, rot: -8, opacity: 0.85 },
    { startFrame: 25, x: 60, y: 20, w: 260, h: 170, rot: 6, opacity: 0.75 },
    { startFrame: 35, x: 72, y: 50, w: 290, h: 185, rot: -4, opacity: 0.8 },
    { startFrame: 45, x: 35, y: 60, w: 250, h: 160, rot: 10, opacity: 0.7 },
    { startFrame: 20, x: 50, y: 75, w: 270, h: 175, rot: -6, opacity: 0.78 },
    { startFrame: 55, x: 15, y: 70, w: 240, h: 155, rot: 5, opacity: 0.65 },
  ];

  return (
    <AbsoluteFill style={{ background: THEME.bg }}>
      {/* grid bg */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)`,
          backgroundSize: "60px 60px",
        }}
      />
      <DayLabel frame={frame} />
      <WarningPulse frame={frame} />
      <UploadDots frame={frame} />
      {windows.map((w, i) => (
        <ChaoticWindow key={i} frame={frame} {...w} />
      ))}
    </AbsoluteFill>
  );
};

export default Scene2_WrongWorkflow;