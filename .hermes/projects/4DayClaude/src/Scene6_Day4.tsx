import React from "react";
import { useCurrentFrame, interpolate, Easing, AbsoluteFill } from "remotion";

const THEME = {
  bg: "#0A0B14",
  bgMid: "#1A1B2F",
  accent: "#FF6B35",
  accentDim: "#FF9A5C",
  text: "#FFFFFF",
  dimText: "rgba(255,255,255,0.55)",
  terminalGreen: "#00FF9F",
  gridLine: "rgba(255,107,53,0.05)",
};

const SPRING = Easing.bezier(0.22, 1, 0.36, 1);

// ─── TERMINAL ────────────────────────────────────────────────────────────────
const Terminal: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp", easing: SPRING });
  const opacity = kf;

  const LINES = [
    { text: "npm install -g @anthropic-ai/claude-code", color: THEME.terminalGreen },
    { text: "✓ Compiling components...", color: THEME.dimText },
    { text: "✓ Local server running on port 3000", color: THEME.dimText },
    { text: "✓ Building your custom workflow app...", color: THEME.accent },
    { text: "✓ Ship it.", color: THEME.terminalGreen },
  ];

  const visible = Math.min(LINES.length, Math.floor(interpolate(frame, [20, 80], [0, LINES.length], { extrapolateRight: "clamp" })));

  return (
    <div
      style={{
        position: "absolute",
        bottom: 0,
        left: 0,
        right: 0,
        height: "65%",
        background: "rgba(0,0,0,0.65)",
        opacity,
        borderTop: `1px solid rgba(255,255,255,0.08)`,
        backdropFilter: "blur(12px)",
        padding: "28px 48px",
      }}
    >
      {/* terminal header */}
      <div style={{ display: "flex", alignItems: "center", gap: 8, marginBottom: 20 }}>
        <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#FF5F57" }} />
        <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#FFBD2E" }} />
        <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#28CA41" }} />
        <span style={{ marginLeft: 12, color: "rgba(255,255,255,0.3)", fontSize: 13, fontFamily: "monospace" }}>bash — claude-code</span>
      </div>
      {/* lines */}
      <div style={{ fontFamily: "monospace", fontSize: 20, lineHeight: 2.2 }}>
        {LINES.slice(0, visible).map((line, i) => (
          <div key={i} style={{ color: line.color }}>
            <span style={{ color: "rgba(255,255,255,0.25)" }}>{">"} </span>{line.text}
          </div>
        ))}
        {frame < 80 && (
          <div style={{ display: "inline-block", width: 12, height: 22, background: THEME.terminalGreen, opacity: (frame % 30) < 15 ? 1 : 0, marginTop: 4 }} />
        )}
      </div>
    </div>
  );
};

// ─── PHONE MOCKUP ────────────────────────────────────────────────────────────
const PhoneMockup: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = interpolate(frame, [50, 80], [0, 1], { extrapolateRight: "clamp", easing: SPRING });
  const opacity = kf;
  const y = (1 - kf) * 500;
  const rot = (1 - kf) * -12;

  const shake = frame >= 80 && frame <= 90 ? interpolate(frame, [80, 90], [12, 0], { extrapolateRight: "clamp" }) : 0;
  const sx = shake * (Math.random() > 0.5 ? 1 : -1);

  return (
    <div
      style={{
        position: "absolute",
        top: "8%",
        right: "6%",
        transform: `translate(${sx}px, calc(-50% + ${y}px)) rotate(${rot}deg)`,
        opacity,
        width: 340,
        height: 700,
        borderRadius: 44,
        border: "3px solid #333",
        background: "#0D0D12",
        overflow: "hidden",
        boxShadow: `0 0 80px ${THEME.accent}22`,
      }}
    >
      {/* notch */}
      <div style={{ height: 32, background: "#0D0D12", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ width: 90, height: 24, background: "#0D0D12", borderRadius: "0 0 14px 14px", border: "1px solid #333", borderTop: "none" }} />
      </div>
      {/* UI */}
      <div style={{ padding: "16px 14px" }}>
        {[
          { label: "Workflow Dashboard", accent: true },
          { label: "My Automations", accent: false },
          { label: "Integrations", accent: false },
          { label: "Settings", accent: false },
        ].map((item) => (
          <div
            key={item.label}
            style={{
              background: item.accent ? `${THEME.accent}20` : "#141420",
              border: `1px solid ${item.accent ? THEME.accent : "#2A2A3A"}44`,
              borderRadius: 12,
              padding: "14px 16px",
              marginBottom: 10,
              color: THEME.text,
              fontFamily: "Inter, sans-serif",
              fontSize: 14,
              fontWeight: item.accent ? 600 : 400,
            }}
          >
            {item.label}
          </div>
        ))}
      </div>
    </div>
  );
};

// ─── BUILDING BLOCKS ANIMATION ───────────────────────────────────────────────
const BuildingBlocks: React.FC<{ frame: number }> = ({ frame }) => {
  const BLOCKS = ["APP UI", "WORKFLOW", "AUTOMATION", "DASHBOARD"];
  const visible = Math.min(BLOCKS.length, Math.floor(interpolate(frame, [90, 140], [0, BLOCKS.length], { extrapolateRight: "clamp" })));

  return (
    <div
      style={{
        position: "absolute",
        top: "50%",
        left: "28%",
        transform: "translate(-50%, -50%)",
        display: "flex",
        flexDirection: "column",
        gap: 8,
        alignItems: "center",
      }}
    >
      {BLOCKS.slice(0, visible).map((block, i) => (
        <div
          key={block}
          style={{
            padding: "10px 28px",
            background: `${THEME.accent}18`,
            border: `1px solid ${THEME.accent}55`,
            borderRadius: 8,
            color: THEME.accent,
            fontFamily: "Inter, sans-serif",
            fontSize: 14,
            fontWeight: 700,
            letterSpacing: "0.05em",
            boxShadow: `0 0 20px ${THEME.accent}22`,
          }}
        >
          {block}
        </div>
      ))}
      {visible >= BLOCKS.length && (
        <div style={{ fontSize: 11, color: THEME.dimText, fontFamily: "Inter, sans-serif", letterSpacing: "0.1em", marginTop: 4 }}>
          ↑ REPETITIVE → SIMPLE
        </div>
      )}
    </div>
  );
};

// ─── DAY TITLE ───────────────────────────────────────────────────────────────
const DayTitle: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp", easing: SPRING });
  return (
    <div style={{ position: "absolute", top: "6%", left: "50%", transform: `translateX(-50%) translateY(${(1 - kf) * -30}px)`, opacity: kf, textAlign: "center" }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: THEME.dimText, fontFamily: "Inter, sans-serif", letterSpacing: "0.2em", textTransform: "uppercase" }}>Day 5</div>
      <div style={{ fontSize: "58px", fontWeight: 900, color: THEME.text, fontFamily: "Poppins, sans-serif", letterSpacing: "-0.03em", textShadow: `0 0 60px ${THEME.accent}33`, lineHeight: 1.1, marginTop: 6 }}>
        CLAUDE CODE
      </div>
      <div style={{ marginTop: 8, fontSize: 18, color: THEME.dimText, fontFamily: "Inter, sans-serif", letterSpacing: "0.02em" }}>
        Build anything. Automate everything.
      </div>
    </div>
  );
};

// ─── SCENE 6 ROOT ────────────────────────────────────────────────────────────
const Scene6_Day4: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: THEME.bg }}>
      <div style={{ position: "absolute", inset: 0, backgroundImage: `linear-gradient(${THEME.gridLine} 1px, transparent 1px), linear-gradient(90deg, ${THEME.gridLine} 1px, transparent 1px)`, backgroundSize: "60px 60px" }} />
      <div style={{ position: "absolute", inset: 0, background: `radial-gradient(ellipse at 50% 60%, transparent 30%, ${THEME.bg} 80%)`, pointerEvents: "none" }} />
      <DayTitle frame={frame} />
      <Terminal frame={frame} />
      <PhoneMockup frame={frame} />
      <BuildingBlocks frame={frame} />
    </AbsoluteFill>
  );
};

export default Scene6_Day4;