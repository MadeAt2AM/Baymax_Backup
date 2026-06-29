import React from "react";
import { useCurrentFrame, interpolate, Easing, AbsoluteFill } from "remotion";

const THEME = {
  bg: "#0A0B14",
  accent: "#FF6B35",
  accentDim: "#FF9A5C",
  text: "#FFFFFF",
  dimText: "rgba(255,255,255,0.55)",
  userYellow: "#FFE066",
  gridLine: "rgba(255,107,53,0.05)",
};

const SPRING = Easing.bezier(0.22, 1, 0.36, 1);

// ─── AVATAR ──────────────────────────────────────────────────────────────────
const Avatar: React.FC<{ frame: number; startFrame: number; side: "left" | "right"; label: string; color: string }> = ({ frame, startFrame, side, label, color }) => {
  const kf = interpolate(frame, [startFrame, startFrame + 20], [0, 1], { extrapolateRight: "clamp", easing: SPRING });
  const cx = side === "left" ? "50%" : "50%";

  return (
    <div
      style={{
        position: "absolute",
        top: "30%",
        left: cx,
        transform: `translate(${side === "left" ? "-100%" : "0"}%, -50%) translateX(${(1 - kf) * (side === "left" ? -200 : 200)}px)`,
        opacity: kf,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 10,
      }}
    >
      {/* avatar circle */}
      <div
        style={{
          width: 120,
          height: 120,
          borderRadius: "50%",
          border: `3px solid ${color}`,
          background: `${color}18`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: `0 0 40px ${color}55`,
        }}
      >
        {side === "left" ? (
          <svg width="56" height="56" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="12" r="7" fill={THEME.userYellow} />
            <path d="M8 28c0-6 4-10 8-10s8 4 8 10" fill={THEME.userYellow} opacity="0.7" />
            <circle cx="13" cy="11" r="1.5" fill="#111" />
            <circle cx="19" cy="11" r="1.5" fill="#111" />
          </svg>
        ) : (
          <svg width="60" height="60" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="14" r="9" fill={THEME.accent} opacity="0.9" />
            <path d="M6 30c0-7 5-12 10-12s10 5 10 12" fill={THEME.accentDim} opacity="0.5" />
            <circle cx="16" cy="14" r="4" fill="#fff" opacity="0.25" />
          </svg>
        )}
      </div>
      <span style={{ color, fontFamily: "Inter, sans-serif", fontSize: 13, fontWeight: 700, letterSpacing: "0.1em" }}>{label}</span>
    </div>
  );
};

// ─── PIPELINE ────────────────────────────────────────────────────────────────
const Pipeline: React.FC<{ frame: number }> = ({ frame }) => {
  const STEPS = ["STEP 01", "STEP 02", "STEP 03", "STEP 04"];
  const activeCount = Math.min(STEPS.length, Math.floor(interpolate(frame, [80, 160], [0, STEPS.length], { extrapolateRight: "clamp" })));

  return (
    <div
      style={{
        position: "absolute",
        top: "50%",
        left: "50%",
        transform: "translate(-50%, -50%)",
        display: "flex",
        alignItems: "center",
        gap: 0,
      }}
    >
      {STEPS.map((step, i) => {
        const done = i < activeCount;
        const active = i === activeCount - 1;
        const opacity = interpolate(frame, [80 + i * 20, 90 + i * 20], [0, 1], { extrapolateRight: "clamp", easing: SPRING });
        return (
          <React.Fragment key={step}>
            <div
              style={{
                opacity,
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                gap: 6,
              }}
            >
              <div
                style={{
                  width: 72,
                  height: 72,
                  borderRadius: 16,
                  border: `2px solid ${done || active ? THEME.accent : "rgba(255,255,255,0.1)"}`,
                  background: done ? `${THEME.accent}22` : active ? `${THEME.accent}15` : "rgba(255,255,255,0.03)",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  boxShadow: done ? `0 0 30px ${THEME.accent}44` : active ? `0 0 20px ${THEME.accent}22` : "none",
                  transition: "all 0.4s",
                }}
              >
                <span style={{ color: done || active ? THEME.accent : "rgba(255,255,255,0.2)", fontFamily: "Inter, sans-serif", fontSize: 12, fontWeight: 700 }}>{step}</span>
              </div>
            </div>
            {i < STEPS.length - 1 && (
              <div style={{ width: 48, height: 2, background: i < activeCount - 1 ? THEME.accent : "rgba(255,255,255,0.1)", transition: "background 0.4s" }} />
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
};

// ─── CLAUDE COMMENT BUTTON ───────────────────────────────────────────────────
const CommentButton: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = interpolate(frame, [170, 185], [0, 1], { extrapolateRight: "clamp", easing: SPRING });
  const opacity = kf;
  const slideX = (1 - kf) * 120;

  return (
    <div
      style={{
        position: "absolute",
        bottom: "14%",
        right: "10%",
        transform: `translateX(${slideX}px)`,
        opacity,
        border: `2px solid ${THEME.accent}`,
        borderRadius: 12,
        background: `${THEME.accent}15`,
        padding: "14px 28px",
        boxShadow: `0 0 40px ${THEME.accent}44`,
      }}
    >
      <span style={{ color: THEME.accent, fontFamily: "Inter, sans-serif", fontSize: 18, fontWeight: 700, letterSpacing: "0.04em" }}>
        COMMENT "CLAUDE"
      </span>
    </div>
  );
};

// ─── DAY TITLE ───────────────────────────────────────────────────────────────
const DayTitle: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp", easing: SPRING });
  return (
    <div style={{ position: "absolute", top: "8%", left: "50%", transform: `translateX(-50%) translateY(${(1 - kf) * -30}px)`, opacity: kf, textAlign: "center" }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: THEME.dimText, fontFamily: "Inter, sans-serif", letterSpacing: "0.2em", textTransform: "uppercase" }}>Day 3</div>
      <div style={{ fontSize: "58px", fontWeight: 900, color: THEME.text, fontFamily: "Poppins, sans-serif", letterSpacing: "-0.03em", textShadow: `0 0 60px ${THEME.accent}33`, lineHeight: 1.1, marginTop: 6 }}>
        CLAUDE COWORK
      </div>
    </div>
  );
};

// ─── SCENE 4 ROOT ────────────────────────────────────────────────────────────
const Scene4_Day2: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: THEME.bg }}>
      <div style={{ position: "absolute", inset: 0, backgroundImage: `linear-gradient(${THEME.gridLine} 1px, transparent 1px), linear-gradient(90deg, ${THEME.gridLine} 1px, transparent 1px)`, backgroundSize: "60px 60px" }} />
      <div style={{ position: "absolute", inset: 0, background: `radial-gradient(ellipse at 50% 50%, transparent 35%, ${THEME.bg} 75%)`, pointerEvents: "none" }} />
      <DayTitle frame={frame} />
      <Avatar frame={frame} startFrame={30} side="left" label="YOU" color={THEME.userYellow} />
      <Avatar frame={frame} startFrame={40} side="right" label="CLAUDE" color={THEME.accent} />
      <Pipeline frame={frame} />
      <CommentButton frame={frame} />
    </AbsoluteFill>
  );
};

export default Scene4_Day2;