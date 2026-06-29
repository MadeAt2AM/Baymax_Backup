import React from "react";
import { useCurrentFrame, interpolate, Easing, AbsoluteFill } from "remotion";

const THEME = {
  bg: "#0A0B14",
  accent: "#FF6B35",
  accentDim: "#FF9A5C",
  text: "#FFFFFF",
  dimText: "rgba(255,255,255,0.55)",
  gridLine: "rgba(255,107,53,0.05)",
};

const SPRING = Easing.bezier(0.22, 1, 0.36, 1);

// ─── MAIN HEADER ─────────────────────────────────────────────────────────────
const MainHeader: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = interpolate(frame, [0, 20], [0, 1], { extrapolateRight: "clamp", easing: SPRING });
  const y = (1 - kf) * -40;
  return (
    <div
      style={{
        position: "absolute",
        top: "18%",
        left: "50%",
        transform: `translateX(-50%) translateY(${y}px)`,
        opacity: kf,
        textAlign: "center",
      }}
    >
      <div
        style={{
          fontSize: "88px",
          fontWeight: 900,
          color: THEME.text,
          fontFamily: "Poppins, sans-serif",
          letterSpacing: "-0.04em",
          lineHeight: 1,
          textShadow: `0 0 80px ${THEME.accent}33`,
        }}
      >
        EXPLORE
      </div>
      <div
        style={{
          fontSize: "88px",
          fontWeight: 900,
          color: THEME.accent,
          fontFamily: "Poppins, sans-serif",
          letterSpacing: "-0.04em",
          lineHeight: 1,
          textShadow: `0 0 100px ${THEME.accent}88`,
        }}
      >
        THE ROADMAP
      </div>
    </div>
  );
};

// ─── CTA BOX ─────────────────────────────────────────────────────────────────
const CTABox: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = interpolate(frame, [30, 50], [0, 1], { extrapolateRight: "clamp", easing: SPRING });
  const opacity = kf;
  const y = (1 - kf) * 50;
  const pulse = (Math.sin((frame - 50) * 0.1) + 1) / 2;

  return (
    <div
      style={{
        position: "absolute",
        top: "50%",
        left: "50%",
        transform: `translate(-50%, -50%) translateY(${y}px)`,
        opacity,
        textAlign: "center",
      }}
    >
      <div
        style={{
          background: "rgba(0,0,0,0.85)",
          border: `2px solid ${THEME.accent}`,
          borderRadius: 20,
          padding: "36px 72px",
          boxShadow: `0 0 ${60 + pulse * 40}px ${THEME.accent}44`,
        }}
      >
        <div
          style={{
            fontSize: "100px",
            fontWeight: 900,
            color: THEME.accent,
            fontFamily: "Poppins, sans-serif",
            letterSpacing: "-0.04em",
            textShadow: `0 0 60px ${THEME.accent}`,
            lineHeight: 1,
          }}
        >
          COMMENT
        </div>
        <div
          style={{
            marginTop: 8,
            fontSize: "80px",
            fontWeight: 900,
            color: THEME.text,
            fontFamily: "Poppins, sans-serif",
            letterSpacing: "-0.04em",
            lineHeight: 1,
          }}
        >
          "CLAUDE"
        </div>
      </div>
    </div>
  );
};

// ─── RESOURCE CARD ───────────────────────────────────────────────────────────
const ResourceCard: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = interpolate(frame, [70, 95], [0, 1], { extrapolateRight: "clamp", easing: SPRING });
  const y = (1 - kf) * 120;
  const opacity = kf;

  return (
    <div
      style={{
        position: "absolute",
        bottom: "8%",
        left: "50%",
        transform: `translateX(-50%) translateY(${y}px)`,
        opacity,
        background: "rgba(255,255,255,0.04)",
        border: "1px solid rgba(255,255,255,0.1)",
        borderRadius: 16,
        backdropFilter: "blur(16px)",
        padding: "20px 40px",
        display: "flex",
        alignItems: "center",
        gap: 20,
        boxShadow: "0 8px 40px rgba(0,0,0,0.4)",
      }}
    >
      {/* icon strip */}
      {["📋", "📁", "🔗", "⚡", "📖"].map((emoji, i) => (
        <div
          key={i}
          style={{
            fontSize: 28,
            opacity: 0.6 + i * 0.08,
          }}
        >
          {emoji}
        </div>
      ))}
      <div style={{ width: 1, height: 40, background: "rgba(255,255,255,0.1)" }} />
      <div>
        <div style={{ color: THEME.text, fontFamily: "Inter, sans-serif", fontSize: 16, fontWeight: 600 }}>
          Full Resource Bundle
        </div>
        <div style={{ color: THEME.dimText, fontFamily: "Inter, sans-serif", fontSize: 13, marginTop: 2 }}>
          Prompts, templates, connectors, & getting-started guide
        </div>
      </div>
    </div>
  );
};

// ─── SCENE 7 ROOT ────────────────────────────────────────────────────────────
const Scene7_Outro: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: THEME.bg }}>
      {/* grid */}
      <div style={{ position: "absolute", inset: 0, backgroundImage: `linear-gradient(${THEME.gridLine} 1px, transparent 1px), linear-gradient(90deg, ${THEME.gridLine} 1px, transparent 1px)`, backgroundSize: "60px 60px" }} />
      {/* vignette */}
      <div style={{ position: "absolute", inset: 0, background: `radial-gradient(ellipse at 50% 40%, transparent 30%, ${THEME.bg} 80%)`, pointerEvents: "none" }} />
      <MainHeader frame={frame} />
      <CTABox frame={frame} />
      <ResourceCard frame={frame} />
    </AbsoluteFill>
  );
};

export default Scene7_Outro;