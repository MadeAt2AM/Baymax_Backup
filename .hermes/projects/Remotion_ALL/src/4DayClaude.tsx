import React from "react";
import { useCurrentFrame, interpolate, Easing, AbsoluteFill, Sequence } from "remotion";

// ─── THEME ───────────────────────────────────────────────────────────────────
const THEME = {
  bg: "#1A1B2F",
  bgDeep: "#0A0B14",
  accent: "#00F2FE",
  accentDim: "#4FACFE",
  text: "#FFFFFF",
  neonPink: "#FF2D95",
  terminalGreen: "#00FF9F",
};

// ─── HELPERS ─────────────────────────────────────────────────────────────────
const bezier = (x: number, y: number, z: number, w: number) =>
  Easing.bezier(x, y, z, w);

const springEasing = bezier(0.22, 1, 0.36, 1);

const useAnim = (
  frame: number,
  keyframes: {
    frame: number;
    opacity?: number;
    scale?: number;
    translateX?: number;
    translateY?: number;
    rotateY?: number;
    rotateZ?: number;
    width?: string | number;
    glitch_intensity?: number;
    pulse_loop?: { min: number; max: number; frequency_frames: number };
    shake_intensity?: number;
    active?: boolean;
    rotation?: number;
    spin_loop_speed?: number;
    staggered_fade_in?: boolean;
    elements_count?: number;
  }[]
) => {
  let opacity = 1,
    scale = 1,
    translateX = 0,
    translateY = 0,
    rotateY = 0,
    rotateZ = 0,
    width: string | number = "100%",
    glitchIntensity = 0,
    shakeIntensity = 0,
    rotation = 0;

  for (let i = 0; i < keyframes.length - 1; i++) {
    const kf = keyframes[i];
    const next = keyframes[i + 1];
    if (frame >= kf.frame && frame < next.frame) {
      const t = (frame - kf.frame) / (next.frame - kf.frame);
      const e = bezier(0.22, 1, 0.36, 1);
      opacity = interpolate(t, [0, 1], [kf.opacity ?? 1, next.opacity ?? 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: e,
      });
      scale = interpolate(
        t,
        [0, 1],
        [kf.scale ?? 1, next.scale ?? 1],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: e }
      );
      translateX = interpolate(
        t,
        [0, 1],
        [kf.translateX ?? 0, next.translateX ?? 0],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: e }
      );
      translateY = interpolate(
        t,
        [0, 1],
        [kf.translateY ?? 0, next.translateY ?? 0],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: e }
      );
      rotateY = interpolate(
        t,
        [0, 1],
        [kf.rotateY ?? 0, next.rotateY ?? 0],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: e }
      );
      rotateZ = interpolate(
        t,
        [0, 1],
        [kf.rotateZ ?? 0, next.rotateZ ?? 0],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: e }
      );
      width =
        typeof kf.width === "number" && typeof next.width === "number"
          ? interpolate(
              t,
              [0, 1],
              [kf.width, next.width],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: e }
            )
          : "100%";
      glitchIntensity = interpolate(
        t,
        [0, 1],
        [
          kf.glitch_intensity ?? 0,
          next.glitch_intensity ?? 0,
        ],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: e }
      );
      shakeIntensity = interpolate(
        t,
        [0, 1],
        [
          kf.shake_intensity ?? 0,
          next.shake_intensity ?? 0,
        ],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: e }
      );
      rotation = interpolate(
        t,
        [0, 1],
        [kf.rotation ?? 0, next.rotation ?? 0],
        { extrapolateLeft: "clamp", extrapolateRight: "clamp", easing: e }
      );
    }
  }

  // pulse loop
  const lastKf = keyframes[keyframes.length - 1];
  if (
    lastKf.pulse_loop &&
    frame >= lastKf.frame
  ) {
    const pf = frame - lastKf.frame;
    const { min, max, frequency_frames } = lastKf.pulse_loop;
    scale =
      (min + max) / 2 +
      ((max - min) / 2) * Math.sin((pf / frequency_frames) * Math.PI * 2);
  }

  return { opacity, scale, translateX, translateY, rotateY, rotateZ, width, glitchIntensity, shakeIntensity, rotation };
};

// ─── SCENE 1 — COUNTDOWN HOOK ────────────────────────────────────────────────
const CountdownLayer: React.FC<{ frame: number }> = ({ frame }) => {
  let value = "";
  let scale = 0;
  let opacity = 0;

  if (frame < 15) {
    value = "4";
    scale = interpolate(frame, [0, 15], [0, 2.5], { extrapolateRight: "clamp", easing: springEasing });
    opacity = interpolate(frame, [0, 15], [0, 1], { extrapolateRight: "clamp" });
  } else if (frame < 30) {
    value = "4";
    scale = 2.5;
    opacity = 1;
  } else if (frame < 45) {
    value = "3";
    scale = 2.5;
    opacity = 1;
  } else if (frame < 60) {
    value = "2";
    scale = 2.5;
    opacity = 1;
  } else if (frame < 75) {
    value = "1";
    scale = 2.5;
    opacity = 1;
  } else {
    value = "";
    scale = 0;
    opacity = 0;
  }

  return (
    <div
      style={{
        position: "absolute",
        top: "50%",
        left: "50%",
        transform: `translate(-50%, -50%) scale(${scale})`,
        opacity,
        fontSize: "280px",
        fontWeight: 900,
        color: THEME.accent,
        fontFamily: "Inter, sans-serif",
        textShadow: `0 0 80px ${THEME.accent}, 0 0 160px ${THEME.accentDim}`,
        letterSpacing: "-0.05em",
        userSelect: "none",
      }}
    >
      {value}
    </div>
  );
};

const NoobCharacter: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = [
    { frame: 75, opacity: 0, translateX: -300, scale: 0.5 },
    { frame: 90, opacity: 1, translateX: 0, scale: 1.0 },
  ];
  const { opacity, scale, translateX } = useAnim(frame, kf);

  return (
    <div
      style={{
        position: "absolute",
        bottom: "15%",
        left: "15%",
        transform: `translateX(${translateX}px) scale(${scale})`,
        opacity,
      }}
    >
      {/* Inline pixel-art noob SVG */}
      <svg width="180" height="180" viewBox="0 0 32 32" fill="none">
        <rect x="12" y="4" width="8" height="8" fill="#FFE066" />
        <rect x="11" y="12" width="10" height="10" fill="#FFE066" />
        <rect x="10" y="22" width="4" height="6" fill="#3366FF" />
        <rect x="18" y="22" width="4" height="6" fill="#3366FF" />
        <rect x="8" y="14" width="4" height="4" fill="#FFE066" />
        <rect x="20" y="14" width="4" height="4" fill="#FFE066" />
        <rect x="14" y="6" width="2" height="2" fill="#111" />
        <rect x="17" y="6" width="2" height="2" fill="#111" />
        <rect x="14" y="10" width="4" height="2" fill="#FF6B6B" />
      </svg>
    </div>
  );
};

const ProgressBar: React.FC<{ frame: number }> = ({ frame }) => {
  const containerKf = [
    { frame: 90, opacity: 0, scale: 0.8 },
    { frame: 100, opacity: 1, scale: 1.0 },
  ];
  const fillKf = [
    { frame: 100, width: 0 },
    { frame: 135, width: 400 },
  ];

  const { opacity, scale } = useAnim(frame, containerKf);
  const fillWidth: number = useAnim(frame, fillKf).width as number;

  return (
    <div
      style={{
        position: "absolute",
        bottom: "30%",
        left: "50%",
        transform: `translateX(-50%) scale(${scale})`,
        opacity,
      }}
    >
      <div
        style={{
          width: "400px",
          height: "30px",
          border: "2px solid #333",
          borderRadius: "15px",
          overflow: "hidden",
          background: "rgba(255,255,255,0.05)",
        }}
      >
        <div
          style={{
            width: `${fillWidth}px`,
            height: "100%",
            background: `linear-gradient(90deg, ${THEME.accent} 0%, ${THEME.accentDim} 100%)`,
            borderRadius: "15px",
            boxShadow: `0 0 20px ${THEME.accent}`,
          }}
        />
      </div>
    </div>
  );
};

const ClaudeProBadge: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = [
    { frame: 135, opacity: 0, scale: 0.3, glitch_intensity: 0 },
    { frame: 145, opacity: 1, scale: 1.2, glitch_intensity: 0.8 },
    { frame: 150, scale: 1.0, glitch_intensity: 0 },
  ];
  const { opacity, scale, glitchIntensity } = useAnim(frame, kf);

  const glitchX = glitchIntensity * (Math.random() > 0.5 ? 1 : -1) * 8;

  return (
    <div
      style={{
        position: "absolute",
        top: "50%",
        left: "50%",
        transform: `translate(-50%, -50%) translateX(${glitchX}px) scale(${scale})`,
        opacity,
      }}
    >
      <svg width="220" height="220" viewBox="0 0 220 220" fill="none">
        <defs>
          <radialGradient id="meshGrad" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={THEME.accent} stopOpacity="0.6" />
            <stop offset="100%" stopColor={THEME.accentDim} stopOpacity="0" />
          </radialGradient>
          <filter id="glow">
            <feGaussianBlur stdDeviation="6" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <circle cx="110" cy="110" r="100" fill="url(#meshGrad)" filter="url(#glow)" />
        <circle cx="110" cy="110" r="80" stroke={THEME.accent} strokeWidth="1.5" strokeDasharray="8 4" fill="none" opacity="0.6" />
        <circle cx="110" cy="110" r="60" stroke={THEME.accent} strokeWidth="1" strokeDasharray="4 6" fill="none" opacity="0.4" />
        <text x="110" y="100" textAnchor="middle" fill={THEME.accent} fontSize="22" fontWeight="700" fontFamily="Inter, sans-serif">
          CLAUDE
        </text>
        <text x="110" y="128" textAnchor="middle" fill={THEME.text} fontSize="18" fontWeight="400" fontFamily="Inter, sans-serif" opacity="0.8">
          PRO
        </text>
        <polygon points="110,40 115,55 130,55 118,65 123,80 110,70 97,80 102,65 90,55 105,55" fill={THEME.accent} filter="url(#glow)" />
      </svg>
    </div>
  );
};

const Scene1Hook: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill
      style={{
        background: `radial-gradient(circle, rgba(26,27,47,1) 0%, rgba(10,11,20,1) 100%)`,
      }}
    >
      {/* Subtle grid overlay */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `
            linear-gradient(rgba(0,242,254,0.03) 1px, transparent 1px),
            linear-gradient(90deg, rgba(0,242,254,0.03) 1px, transparent 1px)
          `,
          backgroundSize: "60px 60px",
        }}
      />
      <CountdownLayer frame={frame} />
      <NoobCharacter frame={frame} />
      <ProgressBar frame={frame} />
      <ClaudeProBadge frame={frame} />
    </AbsoluteFill>
  );
};

// ─── SCENE 2 — DAY 1: SPLIT YOUR LIFE ───────────────────────────────────────
const UIWindow: React.FC<{
  frame: number;
  startFrame: number;
  theme: "neon_pink" | "terminal_dark" | "clean_white";
  label: string;
  icon?: string;
  codeSnippet?: string;
  checklistItems?: string[];
  translateX: number;
}> = ({ frame, startFrame, theme, label, icon, codeSnippet, checklistItems, translateX }) => {
  const kf = [
    {
      frame: startFrame,
      opacity: 0,
      scale: 0.5,
      rotateY: 45,
      translateX: translateX - 600,
    },
    {
      frame: startFrame + 20,
      opacity: 1,
      scale: 1,
      rotateY: -15,
      translateX: translateX - 500,
    },
  ];
  const { opacity, scale, rotateY } = useAnim(frame, kf);

  const configs = {
    neon_pink: { border: "#FF2D95", header: "#FF2D95", bg: "#1A0A14" },
    terminal_dark: { border: "#00FF9F", header: "#00FF9F", bg: "#0A1A10" },
    clean_white: { border: "#E0E0E0", header: "#111111", bg: "#FFFFFF" },
  };
  const c = configs[theme];

  return (
    <div
      style={{
        position: "absolute",
        top: "50%",
        left: "50%",
        width: "400px",
        height: "500px",
        transform: `translate(-50%, -50%) translateX(${translateX - 500}px) perspective(1000px) rotateY(${rotateY}deg) scale(${scale})`,
        opacity,
        border: `2px solid ${c.border}`,
        borderRadius: "16px",
        background: c.bg,
        overflow: "hidden",
        boxShadow: `0 0 40px ${c.border}33`,
      }}
    >
      {/* Window header bar */}
      <div style={{ height: "40px", background: `${c.border}22`, borderBottom: `1px solid ${c.border}44`, display: "flex", alignItems: "center", paddingLeft: 16, gap: 8 }}>
        <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#FF5F57" }} />
        <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#FFBD2E" }} />
        <div style={{ width: 12, height: 12, borderRadius: "50%", background: "#28CA41" }} />
        <span style={{ marginLeft: 12, color: c.border, fontSize: 13, fontFamily: "Inter, sans-serif", fontWeight: 600 }}>{label}</span>
      </div>

      {/* Content */}
      <div style={{ padding: 20 }}>
        {theme === "neon_pink" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 16 }}>
            {["Instagram", "YouTube", "LinkedIn"].map((s, i) => (
              <div key={s} style={{ height: 80, border: `1px solid ${c.border}44`, borderRadius: 12, display: "flex", alignItems: "center", paddingLeft: 16, gap: 12, background: `${c.border}11` }}>
                <div style={{ width: 40, height: 40, borderRadius: 10, background: c.border, opacity: 0.8 }} />
                <span style={{ color: THEME.text, fontFamily: "Inter, sans-serif", fontSize: 16 }}>{s}</span>
              </div>
            ))}
          </div>
        )}
        {theme === "terminal_dark" && (
          <div style={{ fontFamily: "monospace", fontSize: 14, color: c.border, lineHeight: 1.8 }}>
            {codeSnippet?.split("\n").map((line, i) => (
              <div key={i}>
                <span style={{ color: "#888" }}>$</span> {line}
              </div>
            ))}
          </div>
        )}
        {theme === "clean_white" && (
          <div style={{ display: "flex", flexDirection: "column", gap: 12 }}>
            {(checklistItems ?? []).map((item) => (
              <div key={item} style={{ display: "flex", alignItems: "center", gap: 12 }}>
                <div style={{ width: 24, height: 24, border: `2px solid ${c.border}`, borderRadius: 6 }} />
                <span style={{ color: "#111", fontFamily: "Inter, sans-serif", fontSize: 16, fontWeight: 500 }}>{item}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
};

const Scene2Day1: React.FC = () => {
  const frame = useCurrentFrame();

  const titleKf = [
    { frame: 151, opacity: 0, translateY: -50 },
    { frame: 165, opacity: 1, translateY: 0 },
  ];
  const { opacity: titleOpacity, translateY: titleY } = useAnim(frame, titleKf);

  return (
    <AbsoluteFill style={{ background: THEME.bg }}>
      {/* HUD title */}
      <div
        style={{
          position: "absolute",
          top: "10%",
          left: "50%",
          transform: `translateX(-50%) translateY(${titleY}px)`,
          opacity: titleOpacity,
          color: THEME.text,
          fontSize: "60px",
          fontWeight: 800,
          fontFamily: "Inter, sans-serif",
          letterSpacing: "-0.02em",
          textAlign: "center",
          textShadow: `0 0 60px ${THEME.accent}66`,
        }}
      >
        DAY 1: SPLIT YOUR LIFE
      </div>

      <UIWindow frame={frame} startFrame={200} theme="neon_pink" label="SOCIAL MEDIA" translateX={-350} />
      <UIWindow frame={frame} startFrame={240} theme="terminal_dark" label="WEB DEV" translateX={-150} codeSnippet="npm run dev \n > Ready in 45ms" />
      <UIWindow frame={frame} startFrame={280} theme="clean_white" label="PERSONAL" translateX={50} checklistItems={["Finance", "Schedules", "Inbox"]} />
    </AbsoluteFill>
  );
};

// ─── SCENE 3 — DAY 2: CO-WORK WITH CLAUDE ────────────────────────────────────
const AvatarCircle: React.FC<{
  frame: number;
  startFrame: number;
  side: "left" | "right";
  label: string;
  accentColor: string;
}> = ({ frame, startFrame, side, label, accentColor }) => {
  const baseX = side === "left" ? -300 : 300;
  const kf = [
    { frame: startFrame, opacity: 0, translateX: side === "left" ? -400 : 400, scale: 1 },
    { frame: startFrame + 19, opacity: 1, translateX: baseX, scale: 1 },
  ];
  const { opacity, translateX } = useAnim(frame, kf);

  return (
    <div
      style={{
        position: "absolute",
        top: "35%",
        left: "50%",
        transform: `translateX(${translateX}px)`,
        opacity,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        gap: 12,
      }}
    >
      <div
        style={{
          width: 120,
          height: 120,
          borderRadius: "50%",
          border: `3px solid ${accentColor}`,
          background: `${accentColor}22`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: `0 0 30px ${accentColor}66`,
        }}
      >
        {side === "left" ? (
          <svg width="60" height="60" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="12" r="7" fill="#FFE066" />
            <path d="M8 28c0-6 4-10 8-10s8 4 8 10" fill="#3366FF" />
          </svg>
        ) : (
          <svg width="70" height="70" viewBox="0 0 32 32" fill="none">
            <circle cx="16" cy="14" r="8" fill={THEME.accent} opacity="0.8" />
            <path d="M6 30c0-7 5-12 10-12s10 5 10 12" fill={THEME.accentDim} opacity="0.6" />
            <circle cx="16" cy="14" r="4" fill="#fff" opacity="0.3" />
          </svg>
        )}
      </div>
      <span style={{ color: THEME.text, fontFamily: "Inter, sans-serif", fontSize: 14, fontWeight: 600 }}>{label}</span>
    </div>
  );
};

const KanbanBoard: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = [
    { frame: 1230, opacity: 0, scale: 0.9 },
    { frame: 1245, opacity: 1, scale: 1.0 },
  ];
  const { opacity, scale } = useAnim(frame, kf);

  return (
    <div
      style={{
        position: "absolute",
        top: "25%",
        left: "50%",
        transform: `translateX(-50%) scale(${scale})`,
        opacity,
        display: "flex",
        gap: 24,
      }}
    >
      {["To Do", "Done"].map((col, ci) => (
        <div
          key={col}
          style={{
            width: 280,
            background: `${THEME.accent}0D`,
            border: `1px solid ${THEME.accent}33`,
            borderRadius: 16,
            padding: "16px",
          }}
        >
          <div
            style={{
              color: ci === 1 ? THEME.accent : THEME.text,
              fontFamily: "Inter, sans-serif",
              fontSize: 14,
              fontWeight: 700,
              marginBottom: 12,
              textTransform: "uppercase",
              letterSpacing: "0.1em",
            }}
          >
            {col}
          </div>
          {ci === 0 &&
            ["Reply to thread", "Fix bug", "Write docs"].map((item) => (
              <div
                key={item}
                style={{
                  background: "#1A1B2F",
                  border: "1px solid #333",
                  borderRadius: 8,
                  padding: "10px 14px",
                  marginBottom: 8,
                  color: THEME.text,
                  fontSize: 13,
                  fontFamily: "Inter, sans-serif",
                }}
              >
                {item}
              </div>
            ))}
          {ci === 1 &&
            ["Ship feature", "Deploy"].map((item) => (
              <div
                key={item}
                style={{
                  background: `${THEME.accent}15`,
                  border: `1px solid ${THEME.accent}44`,
                  borderRadius: 8,
                  padding: "10px 14px",
                  marginBottom: 8,
                  color: THEME.accent,
                  fontSize: 13,
                  fontFamily: "Inter, sans-serif",
                }}
              >
                {item}
              </div>
            ))}
        </div>
      ))}
    </div>
  );
};

const ParticleStream: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = [
    { frame: 1245, active: true },
    { frame: 1280, active: true },
  ];
  const { opacity: _op } = useAnim(frame, kf);
  const active = frame >= 1245 && frame < 1300;

  if (!active) return null;

  const progress = (frame - 1245) / 55;

  return (
    <div style={{ position: "absolute", inset: 0, pointerEvents: "none" }}>
      {/* User → Kanban particles */}
      {[0, 1, 2].map((i) => {
        const startX = 50 + (-300 / 1920) * 100;
        const startY = 35 + (35 / 1080) * 100;
        const endX = startX + (500 / 19.2);
        const endY = startY - (50 / 10.8);
        const currentX = startX + (endX - startX) * progress;
        const currentY = startY + (endY - startY) * progress;
        return (
          <div
            key={`up-${i}`}
            style={{
              position: "absolute",
              left: `${currentX}%`,
              top: `${currentY}%`,
              width: 6,
              height: 6,
              borderRadius: "50%",
              background: "#FFE066",
              transform: `translate(${progress * 500 - 150}px, ${progress * -50}px)`,
              opacity: 0.8,
              boxShadow: "0 0 8px #FFE066",
            }}
          />
        );
      })}
      {/* Claude → Kanban particles */}
      {[0, 1, 2].map((i) => (
        <div
          key={`cp-${i}`}
          style={{
            position: "absolute",
            left: `${50 + (300 / 1920) * 100}%`,
            top: `${35 + (35 / 1080) * 100}%`,
            width: 6,
            height: 6,
            borderRadius: "50%",
            background: THEME.accent,
            transform: `translate(${-progress * 500 + 150}px, ${-progress * 50}px)`,
            opacity: 0.8,
            boxShadow: `0 0 8px ${THEME.accent}`,
          }}
        />
      ))}
    </div>
  );
};

const CTAOverlay: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = [
    { frame: 1500, opacity: 0, scale: 1.5 },
    { frame: 1515, opacity: 1, scale: 1.0 },
  ];
  const { opacity, scale } = useAnim(frame, kf);

  return (
    <div
      style={{
        position: "absolute",
        bottom: "12%",
        left: "50%",
        transform: `translateX(-50%) scale(${scale})`,
        opacity,
        background: "rgba(0,0,0,0.85)",
        borderRadius: 16,
        padding: "24px 48px",
        border: `2px solid ${THEME.accent}`,
        boxShadow: `0 0 60px ${THEME.accent}44`,
      }}
    >
      <span
        style={{
          fontSize: "90px",
          fontWeight: 900,
          color: THEME.accent,
          fontFamily: "Inter, sans-serif",
          letterSpacing: "-0.03em",
          textShadow: `0 0 40px ${THEME.accent}`,
        }}
      >
        COMMENT "CLAUDE"
      </span>
    </div>
  );
};

const Scene3Day2: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: THEME.bg }}>
      <AvatarCircle frame={frame} startFrame={1201} side="left" label="YOU" accentColor="#FFE066" />
      <AvatarCircle frame={frame} startFrame={1201} side="right" label="CLAUDE" accentColor={THEME.accent} />
      <KanbanBoard frame={frame} />
      <ParticleStream frame={frame} />
      <CTAOverlay frame={frame} />
    </AbsoluteFill>
  );
};

// ─── SCENE 4 — DAY 3: CONNECT TOOLS ─────────────────────────────────────────
const ToolIcon: React.FC<{
  frame: number;
  startFrame: number;
  translateX: number;
  translateY: number;
  targetX: number;
  targetY: number;
  label: string;
  color: string;
}> = ({ frame, startFrame, translateX, translateY, targetX, targetY, label, color }) => {
  const kf = [
    { frame: startFrame, opacity: 0, translateX, translateY },
    { frame: startFrame + 20, opacity: 1, translateX: targetX, translateY: targetY },
  ];
  const { opacity, translateX: tx, translateY: ty } = useAnim(frame, kf);

  return (
    <div
      style={{
        position: "absolute",
        top: "50%",
        left: "50%",
        transform: `translate(calc(-50% + ${tx}px), calc(-50% + ${ty}px))`,
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
          fontSize: 32,
          fontFamily: "Inter, sans-serif",
          fontWeight: 700,
          color: color,
        }}
      >
        {label.slice(0, 2).toUpperCase()}
      </div>
      <span style={{ color: THEME.text, fontSize: 13, fontFamily: "Inter, sans-serif", fontWeight: 600 }}>{label}</span>
    </div>
  );
};

const CentralAIOrb: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = [
    { frame: 1651, scale: 0, rotation: 0 },
    { frame: 1670, scale: 1.0, rotation: 360 },
  ];
  const { scale, rotation } = useAnim(frame, kf);

  return (
    <div
      style={{
        position: "absolute",
        top: "50%",
        left: "50%",
        width: "250px",
        height: "250px",
        transform: `translate(-50%, -50%) scale(${scale}) rotate(${rotation}deg)`,
      }}
    >
      <svg width="250" height="250" viewBox="0 0 250 250" fill="none">
        <defs>
          <radialGradient id="orbGrad" cx="40%" cy="35%" r="60%">
            <stop offset="0%" stopColor={THEME.accent} stopOpacity="0.9" />
            <stop offset="60%" stopColor={THEME.accentDim} stopOpacity="0.4" />
            <stop offset="100%" stopColor={THEME.accentDim} stopOpacity="0" />
          </radialGradient>
          <filter id="orbGlow">
            <feGaussianBlur stdDeviation="12" result="blur" />
            <feMerge>
              <feMergeNode in="blur" />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>
        <circle cx="125" cy="125" r="100" fill="url(#orbGrad)" filter="url(#orbGlow)" />
        <circle cx="125" cy="125" r="70" stroke={THEME.accent} strokeWidth="1.5" strokeDasharray="6 4" fill="none" opacity="0.5" />
        <circle cx="125" cy="125" r="45" stroke={THEME.text} strokeWidth="1" strokeDasharray="3 5" fill="none" opacity="0.2" />
        <text x="125" y="120" textAnchor="middle" fill={THEME.text} fontSize="16" fontWeight="700" fontFamily="Inter, sans-serif" opacity="0.9">AI</text>
        <text x="125" y="140" textAnchor="middle" fill={THEME.accent} fontSize="12" fontFamily="Inter, sans-serif" opacity="0.7">HUB</text>
      </svg>
    </div>
  );
};

const OrbitRings: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = [
    { frame: 1670, opacity: 0, spin_loop_speed: 1 },
    { frame: 1690, opacity: 1, spin_loop_speed: 1 },
  ];
  const { opacity } = useAnim(frame, kf);
  const spinAngle = ((frame - 1690) * 2) % 360;

  return (
    <div
      style={{
        position: "absolute",
        top: "50%",
        left: "50%",
        transform: `translate(-50%, -50%) rotate(${spinAngle}deg)`,
        opacity,
      }}
    >
      <svg width="700" height="700" viewBox="-350 -350 700 700" fill="none">
        {[200, 280, 360].map((r, i) => (
          <circle
            key={r}
            r={r}
            stroke={`rgba(0,242,254,${0.15 - i * 0.04})`}
            strokeWidth="1"
            strokeDasharray={`5 ${8 - i * 2}`}
            fill="none"
          />
        ))}
      </svg>
    </div>
  );
};

const Scene4Day3: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: THEME.bg }}>
      <OrbitRings frame={frame} />
      <CentralAIOrb frame={frame} />
      <ToolIcon frame={frame} startFrame={1680} translateX={-500} translateY={-300} targetX={-200} targetY={-150} label="Drive" color="#4FACFE" />
      <ToolIcon frame={frame} startFrame={1690} translateX={500} translateY={-300} targetX={200} targetY={-150} label="Gmail" color="#FF4444" />
      <ToolIcon frame={frame} startFrame={1700} translateX={500} translateY={300} targetX={200} targetY={150} label="Notion" color={THEME.text} />
    </AbsoluteFill>
  );
};

// ─── SCENE 5 — DAY 4: CLAUDE CODE & AUTOMATION ───────────────────────────────
const TerminalEmulator: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = [
    { frame: 2251, opacity: 0 },
    { frame: 2270, opacity: 0.4 },
  ];
  const { opacity } = useAnim(frame, kf);

  const lines = [
    "npm install -g @anthropic-ai/claude-code",
    "compiling components...",
    "success! running local server on port 3000",
    "building custom workflow app...",
  ];

  const visibleLines = Math.min(
    lines.length,
    Math.floor(interpolate(frame, [2270, 2350], [0, lines.length], { extrapolateRight: "clamp" }))
  );

  return (
    <div
      style={{
        position: "absolute",
        bottom: 0,
        left: 0,
        right: 0,
        height: "60%",
        background: "rgba(0,0,0,0.6)",
        opacity,
        padding: "32px 48px",
        fontFamily: "monospace",
        fontSize: 20,
        lineHeight: 2,
      }}
    >
      {lines.slice(0, visibleLines).map((line, i) => (
        <div key={i} style={{ color: i === 0 ? THEME.terminalGreen : `${THEME.terminalGreen}BB` }}>
          <span style={{ color: "#666" }}>{">"} </span>{line}
        </div>
      ))}
      {frame < 2350 && frame > 2270 && (
        <div style={{ width: 12, height: 24, background: THEME.terminalGreen, display: "inline-block", marginTop: 8, opacity: (frame % 40) < 20 ? 1 : 0 }} />
      )}
    </div>
  );
};

const SmartphoneMockup: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = [
    { frame: 2280, opacity: 0, translateY: 600, scale: 0.5, rotateZ: -10 },
    { frame: 2310, opacity: 1, translateY: 0, scale: 1.0, rotateZ: 0 },
  ];
  const { opacity, translateY, scale, rotateZ } = useAnim(frame, kf);

  return (
    <div
      style={{
        position: "absolute",
        top: "10%",
        right: "8%",
        transform: `translateY(${translateY}px) scale(${scale}) rotate(${rotateZ}deg)`,
        opacity,
        width: "360px",
        height: "740px",
        borderRadius: 48,
        border: "3px solid #333",
        background: "#111",
        overflow: "hidden",
        boxShadow: `0 0 80px ${THEME.accent}22`,
      }}
    >
      {/* Phone notch */}
      <div style={{ height: 32, background: "#111", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div style={{ width: 100, height: 24, background: "#111", borderRadius: "0 0 16px 16px", border: "1px solid #333", borderTop: "none" }} />
      </div>
      {/* Phone UI elements */}
      <div style={{ padding: "20px 16px" }}>
        {["Workflow Dashboard", "Automations", "Integrations", "Settings"].map((item, i) => (
          <div
            key={item}
            style={{
              background: i === 0 ? `${THEME.accent}22` : "#1A1A2F",
              border: `1px solid ${i === 0 ? THEME.accent : "#333"}44`,
              borderRadius: 12,
              padding: "14px 16px",
              marginBottom: 10,
              color: THEME.text,
              fontFamily: "Inter, sans-serif",
              fontSize: 14,
              fontWeight: i === 0 ? 600 : 400,
            }}
          >
            {item}
          </div>
        ))}
      </div>
    </div>
  );
};

const FinalCTAButton: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = [
    { frame: 2400, opacity: 0, scale: 0 },
    { frame: 2415, opacity: 1, scale: 1.0 },
    { frame: 2416, pulse_loop: { min: 1.0, max: 1.08, frequency_frames: 30 } },
  ];
  const { opacity, scale } = useAnim(frame, kf);

  return (
    <div
      style={{
        position: "absolute",
        bottom: "18%",
        left: "50%",
        transform: `translateX(-50%) scale(${scale})`,
        opacity,
      }}
    >
      <div
        style={{
          background: THEME.accent,
          color: "#000",
          fontFamily: "Inter, sans-serif",
          fontSize: "52px",
          fontWeight: 900,
          padding: "20px 60px",
          borderRadius: 16,
          cursor: "pointer",
          boxShadow: `0 0 80px ${THEME.accent}88`,
          letterSpacing: "-0.02em",
        }}
      >
        COMMENT "CLAUDE"
      </div>
    </div>
  );
};

const ScreenShakeEvent: React.FC<{ frame: number }> = ({ frame }) => {
  const kf = [
    { frame: 2310, shake_intensity: 15 },
    { frame: 2320, shake_intensity: 0 },
  ];
  const { shakeIntensity } = useAnim(frame, kf);

  if (shakeIntensity === 0) return null;

  const offsetX = (Math.random() - 0.5) * shakeIntensity * 2;
  const offsetY = (Math.random() - 0.5) * shakeIntensity * 2;

  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        right: 0,
        bottom: 0,
        transform: `translate(${offsetX}px, ${offsetY}px)`,
      }}
    />
  );
};

const Scene5Day4: React.FC = () => {
  const frame = useCurrentFrame();
  return (
    <AbsoluteFill style={{ background: THEME.bg }}>
      <ScreenShakeEvent frame={frame} />
      <TerminalEmulator frame={frame} />
      <SmartphoneMockup frame={frame} />
      <FinalCTAButton frame={frame} />
    </AbsoluteFill>
  );
};

// ─── MAIN COMPOSITION — ALL 5 SCENES IN ONE TIMELINE ─────────────────────────
export const FourDayClaude: React.FC = () => (
  <AbsoluteFill style={{ background: THEME.bg }}>
    {/* Scene 1: Hook / Countdown — frames 0–150 */}
    <Sequence from={0} durationInFrames={151}>
      <Scene1Hook />
    </Sequence>
    {/* Scene 2: Day 1 — frames 151–1200 */}
    <Sequence from={151} durationInFrames={1050}>
      <Scene2Day1 />
    </Sequence>
    {/* Scene 3: Day 2 — frames 1201–1650 */}
    <Sequence from={1201} durationInFrames={450}>
      <Scene3Day2 />
    </Sequence>
    {/* Scene 4: Day 3 — frames 1651–2250 */}
    <Sequence from={1651} durationInFrames={600}>
      <Scene4Day3 />
    </Sequence>
    {/* Scene 5: Day 4 / Outro — frames 2251–2700 */}
    <Sequence from={2251} durationInFrames={450}>
      <Scene5Day4 />
    </Sequence>
  </AbsoluteFill>
);

// ─── STUB EXPORTS — individual scenes (for per-scene scrubbing in Studio) ───────
export const Scene1Hook_comp = Scene1Hook;
export const Scene2Day1_comp = Scene2Day1;
export const Scene3Day2_comp = Scene3Day2;
export const Scene4Day3_comp = Scene4Day3;
export const Scene5Day4_comp = Scene5Day4;