import React from "react";
import { useCurrentFrame, interpolate, Easing, AbsoluteFill } from "remotion";

const THEME = {
  bg: "#0A0B14",
  accent: "#FF6B35",
  accentDim: "#FF9A5C",
  cyan: "#00F2FE",
  text: "#FFFFFF",
  dimText: "rgba(255,255,255,0.55)",
  gridLine: "rgba(255,107,53,0.05)",
};

const SPRING = Easing.bezier(0.22, 1, 0.36, 1);

// ─── CENTRAL ORB ─────────────────────────────────────────────────────────────
const CentralOrb: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = interpolate(frame, [0, 25], [0, 1], { extrapolateRight: "clamp", easing: SPRING });
  const scale = kf;
  const spin = (frame % 360);

  return (
    <div
      style={{
        position: "absolute",
        top: "50%",
        left: "50%",
        transform: `translate(-50%, -50%) scale(${scale})`,
        opacity: kf,
      }}
    >
      {/* orbit rings behind */}
      <div style={{ position: "absolute", top: "50%", left: "50%", transform: `translate(-50%, -50%) rotate(${spin}deg)`, opacity: 0.3 }}>
        <svg width="700" height="700" viewBox="-350 -350 700 700" fill="none">
          {[200, 280, 360].map((r, i) => (
            <circle key={r} r={r} stroke={`rgba(255,107,53,${0.2 - i * 0.05})`} strokeWidth="1" strokeDasharray={`5 ${10 - i * 2}`} fill="none" />
          ))}
        </svg>
      </div>
      {/* orb */}
      <svg width="240" height="240" viewBox="0 0 240 240" fill="none">
        <defs>
          <radialGradient id="orbG" cx="40%" cy="35%" r="65%">
            <stop offset="0%" stopColor={THEME.accent} stopOpacity="0.9" />
            <stop offset="60%" stopColor={THEME.accentDim} stopOpacity="0.4" />
            <stop offset="100%" stopColor={THEME.accentDim} stopOpacity="0" />
          </radialGradient>
          <filter id="orbGlow">
            <feGaussianBlur stdDeviation="14" result="blur" />
            <feMerge><feMergeNode in="blur" /><feMergeNode in="SourceGraphic" /></feMerge>
          </filter>
        </defs>
        <circle cx="120" cy="120" r="100" fill="url(#orbG)" filter="url(#orbGlow)" />
        <circle cx="120" cy="120" r="72" stroke={THEME.accent} strokeWidth="1.5" strokeDasharray="6 4" fill="none" opacity="0.5" />
        <circle cx="120" cy="120" r="48" stroke="rgba(255,255,255,0.2)" strokeWidth="1" strokeDasharray="3 5" fill="none" />
        <text x="120" y="114" textAnchor="middle" fill={THEME.text} fontSize="15" fontWeight="700" fontFamily="Inter, sans-serif" opacity="0.9">AI</text>
        <text x="120" y="136" textAnchor="middle" fill={THEME.accent} fontSize="12" fontFamily="Inter, sans-serif" opacity="0.7">HUB</text>
      </svg>
    </div>
  );
};

// ─── TOOL ICON ───────────────────────────────────────────────────────────────
const ToolIcon: React.FC<{
  frame: number; startFrame: number;
  fromX: number; fromY: number;
  toX: number; toY: number;
  label: string; color: string;
  initial: string;
  connected?: boolean;
}> = ({ frame, startFrame, fromX, fromY, toX, toY, label, color, initial, connected }) => {
  const kf = interpolate(frame, [startFrame, startFrame + 25], [0, 1], { extrapolateRight: "clamp", easing: SPRING });
  const x = fromX + (toX - fromX) * kf;
  const y = fromY + (toY - fromY) * kf;
  const opacity = kf;

  return (
    <div
      style={{
        position: "absolute",
        top: "50%",
        left: "50%",
        transform: `translate(calc(-50% + ${x}px), calc(-50% + ${y}px))`,
        opacity,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 8,
      }}
    >
      <div
        style={{
          width: 80,
          height: 80,
          borderRadius: 20,
          background: `${color}22`,
          border: `2px solid ${color}`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: `0 0 30px ${color}44`,
          fontSize: 28,
          fontWeight: 900,
          fontFamily: "Inter, sans-serif",
          color: color,
        }}
      >
        {initial}
      </div>
      <span style={{ color: THEME.text, fontSize: 13, fontFamily: "Inter, sans-serif", fontWeight: 600 }}>{label}</span>
      {connected && (
        <div
          style={{
            fontSize: 10,
            fontWeight: 700,
            color: color,
            fontFamily: "Inter, sans-serif",
            letterSpacing: "0.1em",
            textShadow: `0 0 10px ${color}`,
          }}
        >
          CONNECTED
        </div>
      )}
    </div>
  );
};

// ─── CONNECTING LINES ────────────────────────────────────────────────────────
const ConnectLines: React.FC<{ frame: number }> = ({ frame }) => {
  const TOOLS = [
    { x: -220, y: -150, color: "#4FACFE" },
    { x: 220, y: -150, color: "#FF4444" },
    { x: 220, y: 150, color: "#AAAAAA" },
  ];
  const progress = interpolate(frame, [40, 90], [0, 1], { extrapolateRight: "clamp" });
  if (progress === 0) return null;

  return (
    <div style={{ position: "absolute", top: "50%", left: "50%", transform: "translate(-50%, -50%)", pointerEvents: "none" }}>
      <svg width="1920" height="1080" viewBox="-960 -540 1920 1080" fill="none">
        {TOOLS.map((t, i) => (
          <line
            key={i}
            x1={0} y1={0}
            x2={t.x} y2={t.y}
            stroke={t.color}
            strokeWidth="1.5"
            strokeDasharray="4 6"
            opacity={progress * 0.6}
            style={{ filter: `drop-shadow(0 0 6px ${t.color})` }}
          />
        ))}
      </svg>
    </div>
  );
};

// ─── DAY TITLE ───────────────────────────────────────────────────────────────
const DayTitle: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp", easing: SPRING });
  return (
    <div style={{ position: "absolute", top: "8%", left: "50%", transform: `translateX(-50%) translateY(${(1 - kf) * -30}px)`, opacity: kf, textAlign: "center" }}>
      <div style={{ fontSize: 13, fontWeight: 700, color: THEME.dimText, fontFamily: "Inter, sans-serif", letterSpacing: "0.2em", textTransform: "uppercase" }}>Day 4</div>
      <div style={{ fontSize: "58px", fontWeight: 900, color: THEME.text, fontFamily: "Poppins, sans-serif", letterSpacing: "-0.03em", textShadow: `0 0 60px ${THEME.accent}33`, lineHeight: 1.1, marginTop: 6 }}>
        CONNECT YOUR TOOLS
      </div>
    </div>
  );
};

// ─── SCENE 5 ROOT ────────────────────────────────────────────────────────────
const Scene5_Day3: React.FC = () => {
  const frame = useCurrentFrame();
  const connected = frame > 90;

  return (
    <AbsoluteFill style={{ background: THEME.bg }}>
      <div style={{ position: "absolute", inset: 0, backgroundImage: `linear-gradient(${THEME.gridLine} 1px, transparent 1px), linear-gradient(90deg, ${THEME.gridLine} 1px, transparent 1px)`, backgroundSize: "60px 60px" }} />
      <div style={{ position: "absolute", inset: 0, background: `radial-gradient(ellipse at 50% 50%, transparent 35%, ${THEME.bg} 75%)`, pointerEvents: "none" }} />
      <DayTitle frame={frame} />
      <CentralOrb frame={frame} />
      <ConnectLines frame={frame} />
      <ToolIcon frame={frame} startFrame={40} fromX={-500} fromY={-280} toX={-220} toY={-150} label="Google Drive" color="#4FACFE" initial="DR" connected={connected} />
      <ToolIcon frame={frame} startFrame={55} fromX={500} fromY={-280} toX={220} toY={-150} label="Gmail" color="#FF4444" initial="GM" connected={connected} />
      <ToolIcon frame={frame} startFrame={70} fromX={500} fromY={280} toX={220} toY={150} label="Notion" color="#AAAAAA" initial="NT" connected={connected} />
    </AbsoluteFill>
  );
};

export default Scene5_Day3;