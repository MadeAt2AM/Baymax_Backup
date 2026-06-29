import React from "react";
import { useCurrentFrame, interpolate, Easing, AbsoluteFill } from "remotion";

const THEME = {
  bg: "#0A0B14",
  bgMid: "#1A1B2F",
  accent: "#FF6B35",
  accentDim: "#FF9A5C",
  text: "#FFFFFF",
  dimText: "rgba(255,255,255,0.55)",
  gridLine: "rgba(255,107,53,0.05)",
};

const SPRING = Easing.bezier(0.22, 1, 0.36, 1);

const useKF = (frame: number, keyframes: { frame: number; [key: string]: any }[]) => {
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

// ─── SECTION CARD ─────────────────────────────────────────────────────────────
const SectionCard: React.FC<{
  frame: number;
  startFrame: number;
  x: number;
  label: string;
  theme: { border: string; header: string; bg: string; text: string; icon: string };
  items: string[];
}> = ({ frame, startFrame, x, label, theme, items }) => {
  const kf = useKF(frame, [
    { frame: startFrame, opacity: 0, y: 80, scale: 0.8, rotY: 30 },
    { frame: startFrame + 25, opacity: 1, y: 0, scale: 1, rotY: -8 },
    { frame: startFrame + 35, rotY: 0 },
  ]);
  const opacity = kf.opacity ?? 0;
  const y = kf.y ?? 0;
  const scale = kf.scale ?? 1;
  const rotY = kf.rotY ?? 0;

  return (
    <div
      style={{
        position: "absolute",
        top: "50%",
        left: `${x}%`,
        transform: `translate(-50%, -50%) translateY(${y}px) perspective(1000px) rotateY(${rotY}deg) scale(${scale})`,
        opacity,
        width: 360,
        border: `2px solid ${theme.border}`,
        borderRadius: 20,
        background: theme.bg,
        overflow: "hidden",
        boxShadow: `0 0 50px ${theme.border}33`,
      }}
    >
      {/* header */}
      <div style={{ height: 52, background: `${theme.border}18`, borderBottom: `1px solid ${theme.border}33`, display: "flex", alignItems: "center", paddingLeft: 20, gap: 12 }}>
        <div style={{ width: 14, height: 14, borderRadius: 4, background: theme.border, opacity: 0.9 }} />
        <span style={{ color: theme.border, fontFamily: "Inter, sans-serif", fontSize: 14, fontWeight: 700, letterSpacing: "0.08em" }}>{label}</span>
      </div>
      {/* items */}
      <div style={{ padding: "20px 20px", display: "flex", flexDirection: "column", gap: 12 }}>
        {items.map((item, i) => (
          <div key={item} style={{ display: "flex", alignItems: "center", gap: 12 }}>
            <div style={{ width: 20, height: 20, borderRadius: 6, border: `2px solid ${theme.border}66`, flexShrink: 0 }} />
            <span style={{ color: theme.text, fontFamily: "Inter, sans-serif", fontSize: 15, fontWeight: 500 }}>{item}</span>
          </div>
        ))}
      </div>
    </div>
  );
};

// ─── PERMANENT CONTEXT LABEL ──────────────────────────────────────────────────
const PermanentContextLabel: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = useKF(frame, [
    { frame: 120, opacity: 0, y: 20 },
    { frame: 135, opacity: 1, y: 0 },
  ]);
  const opacity = kf.opacity ?? 0;
  const y = kf.y ?? 0;

  return (
    <div
      style={{
        position: "absolute",
        bottom: "12%",
        left: "50%",
        transform: `translateX(-50%) translateY(${y}px)`,
        opacity,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 8,
      }}
    >
      <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
        {[0, 1, 2].map((i) => (
          <React.Fragment key={i}>
            {i > 0 && <div style={{ width: 40, height: 2, background: THEME.accent, opacity: 0.5 }} />}
            <div style={{ width: 10, height: 10, borderRadius: "50%", background: THEME.accent, boxShadow: `0 0 12px ${THEME.accent}` }} />
          </React.Fragment>
        ))}
      </div>
      <div
        style={{
          fontSize: 13,
          fontWeight: 700,
          color: THEME.accent,
          fontFamily: "Inter, sans-serif",
          letterSpacing: "0.18em",
          textTransform: "uppercase",
          textShadow: `0 0 20px ${THEME.accent}66`,
        }}
      >
        PERMANENT CONTEXT
      </div>
    </div>
  );
};

// ─── TITLE ───────────────────────────────────────────────────────────────────
const Title: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = useKF(frame, [
    { frame: 0, opacity: 0, y: -50 },
    { frame: 15, opacity: 1, y: 0 },
  ]);
  const opacity = kf.opacity ?? 0;
  const y = kf.y ?? 0;

  return (
    <div
      style={{
        position: "absolute",
        top: "10%",
        left: "50%",
        transform: `translateX(-50%) translateY(${y}px)`,
        opacity,
        textAlign: "center",
      }}
    >
      <div style={{ fontSize: 13, fontWeight: 700, color: THEME.dimText, fontFamily: "Inter, sans-serif", letterSpacing: "0.2em", textTransform: "uppercase", marginBottom: 8 }}>
        Day 2
      </div>
      <div
        style={{
          fontSize: "64px",
          fontWeight: 900,
          color: THEME.text,
          fontFamily: "Poppins, sans-serif",
          letterSpacing: "-0.03em",
          textShadow: `0 0 60px ${THEME.accent}33`,
          lineHeight: 1,
        }}
      >
        CREATE YOUR PROJECTS
      </div>
    </div>
  );
};

// ─── SCENE 3 ROOT ────────────────────────────────────────────────────────────
const Scene3_Day1: React.FC = () => {
  const frame = useCurrentFrame();
  const CARD_THEMES = {
    social: { border: "#FF2D95", header: "#FF2D95", bg: "#1A0A14", text: "#FFFFFF", icon: "●" },
    webdev: { border: "#00FF9F", header: "#00FF9F", bg: "#0A1A10", text: "#FFFFFF", icon: "●" },
    admin:  { border: "#E0E0E0", header: "#E0E0E0", bg: "#111111", text: "#E0E0E0", icon: "●" },
  };

  return (
    <AbsoluteFill style={{ background: THEME.bg }}>
      {/* grid */}
      <div style={{ position: "absolute", inset: 0, backgroundImage: `linear-gradient(${THEME.gridLine} 1px, transparent 1px), linear-gradient(90deg, ${THEME.gridLine} 1px, transparent 1px)`, backgroundSize: "60px 60px" }} />
      {/* vignette */}
      <div style={{ position: "absolute", inset: 0, background: `radial-gradient(ellipse at 50% 40%, transparent 30%, ${THEME.bg} 80%)`, pointerEvents: "none" }} />
      <Title frame={frame} />
      <SectionCard frame={frame} startFrame={40}  x={22} label="SOCIAL MEDIA" theme={CARD_THEMES.social} items={["Instagram posts", "YouTube content", "LinkedIn outreach", "X threads"]} />
      <SectionCard frame={frame} startFrame={60}  x={50} label="WEB DEV"        theme={CARD_THEMES.webdev} items={["Build features", "Fix bugs", "Deploy projects", "Code reviews"]} />
      <SectionCard frame={frame} startFrame={80}  x={78} label="PERSONAL ADMIN"  theme={CARD_THEMES.admin}  items={["Finance tracker", "Daily schedule", "Inbox zero", "Health & fitness"]} />
      <PermanentContextLabel frame={frame} />
    </AbsoluteFill>
  );
};

export default Scene3_Day1;