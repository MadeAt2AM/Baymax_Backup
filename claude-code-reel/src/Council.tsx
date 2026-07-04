import React from "react";
import {
  useCurrentFrame,
  interpolate,
  Easing,
  AbsoluteFill,
  Sequence,
  useVideoConfig,
} from "remotion";
import { Audio } from "@remotion/media";
import {
  whoosh,
  uiSwitch,
  vineBoom,
  dramaticBoomer,
  yippee,
} from "@remotion/sfx";

const fps = 30;

// ─── THEME ───────────────────────────────────────────────────────────────────

const C = {
  bg: "#080B18",
  cyan: "#00E5FF",
  magenta: "#FF006E",
  red: "#FF3366",
  green: "#39FF14",
  purple: "#A855F7",
  yellow: "#FFB800",
  text: "#F0F4FF",
  glass: "rgba(17,24,39,0.75)",
  glassBorder: "rgba(255,255,255,0.1)",
} as const;

// ─── HELPER: Neon Glow ───────────────────────────────────────────────────────

const glowStyle = (color: string, intensity = 1) => ({
  boxShadow: `
    0 0 ${5 * intensity}px ${color},
    0 0 ${15 * intensity}px ${color},
    0 0 ${40 * intensity}px ${color},
    0 0 ${80 * intensity}px ${color}66
  `,
});

const textGlow = (color: string, blur = 20) => ({
  textShadow: `0 0 ${blur}px ${color}, 0 0 ${blur * 2}px ${color}`,
});

// ─── HELPER: 3D Card ─────────────────────────────────────────────────────────

const Card3D: React.FC<{
  x: number;
  y: number;
  width: number;
  height: number;
  color: string;
  icon: React.ReactNode;
  title: string;
  subtitle: string;
  startFrame: number;
  activeFrame: number;
}> = ({ x, y, width, height, color, icon, title, subtitle, startFrame, activeFrame }) => {
  const frame = useCurrentFrame();

  const relativeFrame = Math.max(0, frame - startFrame);

  // Spring fly-in: rotateX + rotateY + translateY
  const rotateX = interpolate(relativeFrame, [0, 30], [45, 0], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.34, 1.56, 0.64, 1),
  });
  const rotateY = interpolate(relativeFrame, [0, 30], [-30, 0], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.34, 1.56, 0.64, 1),
  });
  const translateY = interpolate(relativeFrame, [0, 30], [120, 0], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const scale = interpolate(relativeFrame, [0, 20], [0.6, 1], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  // Active pulse ring
  const timeSinceActive = Math.max(0, frame - activeFrame);
  const ringScale = interpolate(timeSinceActive, [0, 20], [1, 1.15], {
    extrapolateRight: "clamp",
  });
  const ringOpacity = interpolate(timeSinceActive, [0, 30], [0.8, 0], {
    extrapolateRight: "clamp",
  });

  const isActive = frame >= activeFrame && frame < activeFrame + 45;

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width,
        height,
        transformStyle: "preserve-3d",
        transform: `perspective(1000px) translateY(${translateY}px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(${scale})`,
        background: C.glass,
        border: `1px solid ${color}44`,
        borderRadius: 20,
        backdropFilter: "blur(12px)",
        ...glowStyle(color, isActive ? 1.5 : 0.6),
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        padding: 16,
        gap: 8,
      }}
    >
      {/* Active pulse ring */}
      {isActive && (
        <div
          style={{
            position: "absolute",
            inset: -4,
            borderRadius: 24,
            border: `2px solid ${color}`,
            transform: `scale(${ringScale})`,
            opacity: ringOpacity,
          }}
        />
      )}

      {/* Icon */}
      <div
        style={{
          width: 64,
          height: 64,
          borderRadius: 16,
          background: `${color}22`,
          border: `1px solid ${color}66`,
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          ...glowStyle(color, 0.8),
        }}
      >
        {icon}
      </div>

      {/* Title */}
      <span
        style={{
          color: C.text,
          fontSize: 18,
          fontWeight: 800,
          fontFamily: "Inter, sans-serif",
          letterSpacing: "0.05em",
          textTransform: "uppercase",
          textAlign: "center",
        }}
      >
        {title}
      </span>

      {/* Subtitle */}
      <span
        style={{
          color: `${C.text}bb`,
          fontSize: 13,
          fontFamily: "Inter, sans-serif",
          textAlign: "center",
          lineHeight: 1.4,
        }}
      >
        {subtitle}
      </span>
    </div>
  );
};

// ─── HELPER: Glitch Text ─────────────────────────────────────────────────────

const GlitchText: React.FC<{
  children: string;
  startFrame: number;
  style?: React.CSSProperties;
  glitchIntensity?: number;
}> = ({ children, startFrame, style, glitchIntensity = 1 }) => {
  const frame = useCurrentFrame();
  const relative = Math.max(0, frame - startFrame);

  const opacity = interpolate(relative, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  const rgbOffsetX = interpolate(relative, [0, 10, 20, 30], [0, -3 * glitchIntensity, 2 * glitchIntensity, 0], {
    extrapolateRight: "clamp",
  });

  const rgbOffsetY = interpolate(relative, [5, 15, 25], [0, 2 * glitchIntensity, 0], {
    extrapolateRight: "clamp",
  });

  return (
    <div style={{ position: "relative", opacity, ...style }}>
      {/* Cyan ghost */}
      <span
        style={{
          position: "absolute",
          inset: 0,
          color: "#00F5FF",
          ...textGlow("#00F5FF", 15),
          transform: `translate(${rgbOffsetX}px, ${rgbOffsetY}px)`,
          clipPath: `inset(${rgbOffsetY}px 0 0 0)`,
        }}
      >
        {children}
      </span>
      {/* Magenta ghost */}
      <span
        style={{
          position: "absolute",
          inset: 0,
          color: "#FF006E",
          ...textGlow("#FF006E", 15),
          transform: `translate(${-rgbOffsetX}px, ${-rgbOffsetY}px)`,
          clipPath: `inset(${-rgbOffsetY}px 0 0 0)`,
        }}
      >
        {children}
      </span>
      {/* Main text */}
      <span style={{ position: "relative", color: C.text }}>{children}</span>
    </div>
  );
};

// ─── HELPER: Floating Orb (seat) ─────────────────────────────────────────────

const SeatOrb: React.FC<{
  x: number;
  y: number;
  color: string;
  litFrame: number;
  size?: number;
}> = ({ x, y, color, litFrame, size = 40 }) => {
  const frame = useCurrentFrame();
  const lit = frame >= litFrame;

  const pulse = Math.sin((frame - litFrame) * 0.1) * 0.15 + 1;
  const opacity = interpolate(frame, [litFrame, litFrame + 20], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width: size,
        height: size,
        borderRadius: "50%",
        background: lit ? color : "transparent",
        border: `2px solid ${color}88`,
        transform: `scale(${lit ? pulse : 0.8})`,
        opacity: lit ? opacity : 0.3,
        ...glowStyle(color, lit ? 2 : 0.3),
        transition: "none",
      }}
    />
  );
};

// ─── HELPER: Energy Beam ─────────────────────────────────────────────────────

const EnergyBeam: React.FC<{
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  color: string;
  startFrame: number;
}> = ({ fromX, fromY, toX, toY, color, startFrame }) => {
  const frame = useCurrentFrame();
  const relative = Math.max(0, frame - startFrame);

  const opacity = interpolate(relative, [0, 20], [0, 0.7], {
    extrapolateRight: "clamp",
  });

  // Calculate line angle and length
  const dx = toX - fromX;
  const dy = toY - fromY;
  const length = Math.sqrt(dx * dx + dy * dy);
  const angle = Math.atan2(dy, dx) * (180 / Math.PI);

  // Travelling particle offset
  const particleOffset = interpolate(relative, [0, 60], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        left: fromX,
        top: fromY,
        width: length,
        height: 2,
        background: `linear-gradient(90deg, ${color}00, ${color}aa, ${color}00)`,
        transform: `rotate(${angle}deg)`,
        transformOrigin: "0 50%",
        opacity,
        overflow: "hidden",
      }}
    >
      {/* Travelling bright dot */}
      <div
        style={{
          position: "absolute",
          left: `${particleOffset * 100}%`,
          top: "50%",
          transform: "translate(-50%, -50%)",
          width: 8,
          height: 8,
          borderRadius: "50%",
          background: "white",
          boxShadow: `0 0 10px ${color}, 0 0 20px ${color}`,
        }}
      />
    </div>
  );
};

// ─── SCENE 1: HOOK ───────────────────────────────────────────────────────────

const Scene1_Hook: React.FC = () => {
  const frame = useCurrentFrame();

  // 5 seat orbs appear sequentially
  const orbPositions = [
    { x: 340, y: 320 },
    { x: 220, y: 480 },
    { x: 460, y: 480 },
    { x: 140, y: 640 },
    { x: 540, y: 640 },
  ];

  const orbColors = [C.red, C.cyan, C.green, C.purple, C.yellow];

  const text2Opacity = interpolate(frame, [70, 90], [0, 1], {
    extrapolateRight: "clamp",
  });

  const cameraPush = interpolate(frame, [0, 60], [0, -30], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: C.bg,
        perspective: 1000,
        transformStyle: "preserve-3d",
        transform: `translateZ(${cameraPush}px)`,
      }}
    >
      {/* Faint grid floor */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `
            linear-gradient(rgba(255,255,255,0.02) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.02) 1px, transparent 1px)
          `,
          backgroundSize: "60px 60px",
          transform: "perspective(500px) rotateX(60deg) translateY(100px)",
        }}
      />

      {/* The 5 seat orbs */}
      {orbPositions.map((pos, i) => (
        <SeatOrb
          key={i}
          x={pos.x}
          y={pos.y}
          color={orbColors[i]}
          litFrame={10 + i * 12}
          size={44}
        />
      ))}

      {/* Ring connecting orbs */}
      {frame >= 70 && (
        <div
          style={{
            position: "absolute",
            left: 120,
            top: 300,
            width: 500,
            height: 380,
            borderRadius: "50%",
            border: `1px solid ${C.cyan}22`,
            transform: "scaleX(0.7)",
          }}
        />
      )}

      {/* Hook text line 1 */}
      <div style={{ position: "absolute", top: 180, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
        <GlitchText
          startFrame={60}
          style={{ fontSize: 38, fontFamily: "Inter, sans-serif", fontWeight: 900, textAlign: "center", maxWidth: 800, lineHeight: 1.2, padding: "0 40px" }}
          glitchIntensity={2}
        >
          Everyone treats Claude like a yes man...
        </GlitchText>
      </div>

      {/* Hook text line 2 */}
      <div style={{ position: "absolute", top: 290, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
        <div style={{ opacity: text2Opacity }}>
          <span style={{ fontSize: 52, fontFamily: "Inter, sans-serif", fontWeight: 900, color: C.cyan, ...textGlow(C.cyan, 30) }}>
            but the top 10% do THIS instead
          </span>
        </div>
      </div>

      {/* Transition text */}
      <div style={{ position: "absolute", top: 880, left: 0, right: 0, display: "flex", justifyContent: "center" }}>
        <div style={{ opacity: text2Opacity }}>
          <span style={{ fontSize: 28, fontFamily: "Inter, sans-serif", fontWeight: 700, color: C.magenta, ...textGlow(C.magenta, 20) }}>
            Instead of asking Claude — ask the COUNCIL
          </span>
        </div>
      </div>
    </div>
  );
};

// ─── SCENE 2: THE FIVE AGENTS ────────────────────────────────────────────────

const Scene2_Agents: React.FC = () => {
  const { width, height } = useVideoConfig();
  const frame = useCurrentFrame();

  const W = width;
  const H = height;

  // Positions for 5 cards (centered, 2 rows)
  const cardW = 280;
  const cardH = 200;
  const cardConfigs = [
    // Row 1: 3 cards
    { x: W / 2 - cardW * 1.5 - 20, y: H / 2 - cardH - 30, start: 10, active: 40, color: C.red, title: "THE CONTRARIAN", subtitle: "Looks for what WILL fail — the problems you're ignoring" },
    { x: W / 2 - cardW / 2, y: H / 2 - cardH - 30, start: 25, active: 60, color: C.cyan, title: "FIRST PRINCIPLE", subtitle: "Rebuilds your problem from absolute ZERO" },
    { x: W / 2 + cardW / 2 + 20, y: H / 2 - cardH - 30, start: 40, active: 80, color: C.green, title: "THE EXPANSIONIST", subtitle: "Finds the UPSIDE hiding in your problem" },
    // Row 2: 2 cards centered
    { x: W / 2 - cardW - 10, y: H / 2 + 30, start: 55, active: 95, color: C.purple, title: "THE OUTSIDER", subtitle: "Strips ALL context — sees your raw problem" },
    { x: W / 2 + 10, y: H / 2 + 30, start: 70, active: 115, color: C.yellow, title: "THE EXECUTOR", subtitle: "First step FIRST — everything else follows" },
  ];

  // SVG icons for each agent
  const AgentIcons: React.ReactNode[] = [
    // Contrarian — cross/X
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
      <circle cx="16" cy="16" r="14" stroke={C.red} strokeWidth="2"/>
      <path d="M10 10L22 22M22 10L10 22" stroke={C.red} strokeWidth="2.5" strokeLinecap="round"/>
    </svg>,
    // First Principle — layers/build
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
      <rect x="4" y="18" width="24" height="6" rx="2" stroke={C.cyan} strokeWidth="2"/>
      <rect x="7" y="11" width="18" height="6" rx="2" stroke={C.cyan} strokeWidth="2"/>
      <rect x="10" y="4" width="12" height="6" rx="2" stroke={C.cyan} strokeWidth="2"/>
    </svg>,
    // Expansionist — up arrow
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
      <path d="M16 28V8M8 16L16 6L24 16" stroke={C.green} strokeWidth="2.5" strokeLinecap="round" strokeLinejoin="round"/>
    </svg>,
    // Outsider — eye with slash
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
      <path d="M4 16C7 10 12 6 16 6C20 6 25 10 28 16C25 22 20 26 16 26C12 26 7 22 4 16Z" stroke={C.purple} strokeWidth="2"/>
      <circle cx="16" cy="16" r="4" stroke={C.purple} strokeWidth="2"/>
      <path d="M4 4L28 28" stroke={C.purple} strokeWidth="2" strokeLinecap="round"/>
    </svg>,
    // Executor — checklist
    <svg width="32" height="32" viewBox="0 0 32 32" fill="none">
      <rect x="4" y="4" width="24" height="24" rx="3" stroke={C.yellow} strokeWidth="2"/>
      <path d="M10 13L14 17L22 9" stroke={C.yellow} strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"/>
      <path d="M10 22H22" stroke={C.yellow} strokeWidth="2" strokeLinecap="round"/>
    </svg>,
  ];

  // Malayalam subtitle fades
  const malayalamOpacity = interpolate(frame, [100, 120], [0, 1], { extrapolateRight: "clamp" });

  return (
    <div style={{ position: "absolute", inset: 0, background: C.bg }}>
      {/* Section title */}
      {frame >= 5 && (
        <div style={{ position: "absolute", top: 60, left: 0, right: 0, textAlign: "center" }}>
          <span style={{ fontSize: 22, fontFamily: "Inter, sans-serif", fontWeight: 800, color: C.cyan, letterSpacing: "0.15em", textTransform: "uppercase", ...textGlow(C.cyan, 15) }}>
            THE FIVE AGENTS
          </span>
        </div>
      )}

      {/* 5 Agent Cards */}
      {cardConfigs.map((cfg, i) => (
        <Card3D
          key={i}
          x={cfg.x}
          y={cfg.y}
          width={cardW}
          height={cardH}
          color={cfg.color}
          icon={AgentIcons[i]}
          title={cfg.title}
          subtitle={cfg.subtitle}
          startFrame={cfg.start}
          activeFrame={cfg.active}
        />
      ))}

      {/* Malayalam aside: 5 ennathhinum 5 swabavam */}
      <div style={{ position: "absolute", bottom: 120, left: 0, right: 0, textAlign: "center", opacity: malayalamOpacity }}>
        <span style={{ fontSize: 24, fontFamily: "Inter, sans-serif", color: `${C.text}aa` }}>
          "5 ennathhinum 5 swabavam"
        </span>
      </div>
    </div>
  );
};

// ─── SCENE 3: THE DEBATE ──────────────────────────────────────────────────────

const Scene3_Debate: React.FC = () => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();

  const W = width;
  const H = height;

  const centerX = W / 2;
  const centerY = H / 2 - 60;

  // 5 agent positions in semicircle
  const agentAngles = [210, 245, 270, 295, 330]; // degrees
  const radius = 300;
  const agentPositions = agentAngles.map((deg) => {
    const rad = (deg * Math.PI) / 180;
    return {
      x: centerX + radius * Math.cos(rad),
      y: centerY + radius * Math.sin(rad),
    };
  });

  const beamStartFrame = 10;
  const orbitAngle = interpolate(frame, [beamStartFrame, 150], [0, 60], {
    extrapolateRight: "clamp",
  });

  const beamOpacity = interpolate(frame, [beamStartFrame, beamStartFrame + 20], [0, 0.8], {
    extrapolateRight: "clamp",
  });

  const textOpacity = interpolate(frame, [30, 50], [0, 1], { extrapolateRight: "clamp" });

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: C.bg,
        perspective: 1200,
        transformStyle: "preserve-3d",
        transform: `rotateY(${orbitAngle * 0.15}deg)`,
      }}
    >
      {/* Faint grid */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: `
            linear-gradient(rgba(255,255,255,0.025) 1px, transparent 1px),
            linear-gradient(90deg, rgba(255,255,255,0.025) 1px, transparent 1px)
          `,
          backgroundSize: "60px 60px",
          transform: "perspective(600px) rotateX(65deg) translateY(80px)",
        }}
      />

      {/* Energy beams to center */}
      {agentPositions.map((pos, i) => {
        const colors = [C.red, C.cyan, C.green, C.purple, C.yellow];
        return (
          <EnergyBeam
            key={i}
            fromX={pos.x}
            fromY={pos.y}
            toX={centerX}
            toY={centerY}
            color={colors[i]}
            startFrame={beamStartFrame + i * 8}
          />
        );
      })}

      {/* Convergence glow at center */}
      <div
        style={{
          position: "absolute",
          left: centerX - 20,
          top: centerY - 20,
          width: 40,
          height: 40,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${C.cyan}88, transparent)`,
          opacity: beamOpacity,
          ...glowStyle(C.cyan, beamOpacity * 2),
        }}
      />

      {/* Agent orbs */}
      {agentPositions.map((pos, i) => {
        const colors = [C.red, C.cyan, C.green, C.purple, C.yellow];
        return (
          <div
            key={i}
            style={{
              position: "absolute",
              left: pos.x - 20,
              top: pos.y - 20,
              width: 40,
              height: 40,
              borderRadius: "50%",
              background: colors[i],
              opacity: beamOpacity,
              ...glowStyle(colors[i], beamOpacity * 1.5),
            }}
          />
        );
      })}

      {/* Debate text */}
      <div style={{ position: "absolute", top: 100, left: 0, right: 0, textAlign: "center", opacity: textOpacity }}>
        <span style={{ fontSize: 28, fontFamily: "Inter, sans-serif", fontWeight: 800, color: C.text, ...textGlow(C.cyan, 20) }}>
          Claude runs the question through all agents and debates...
        </span>
      </div>

      {/* Malayalam */}
      <div style={{ position: "absolute", bottom: 150, left: 0, right: 0, textAlign: "center", opacity: textOpacity }}>
        <span style={{ fontSize: 22, fontFamily: "Inter, sans-serif", color: `${C.text}88` }}>
          "ith okke kaziyyumbo Claude gives it to the CHAIRMAN"
        </span>
      </div>
    </div>
  );
};

// ─── SCENE 4: CHAIRMAN VERDICT ───────────────────────────────────────────────

const Scene4_Chairman: React.FC = () => {
  const frame = useCurrentFrame();

  const bloomPeak = 25;
  const bloomIntensity = interpolate(frame, [0, bloomPeak], [0, 3], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  const verdictOpacity = interpolate(frame, [30, 55], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  const verdictScale = interpolate(frame, [30, 60], [0.5, 1], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.34, 1.56, 0.64, 1),
  });

  const cameraPush = interpolate(frame, [0, bloomPeak], [0, -60], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  // Gavel icon (SVG)
  const GavelIcon = () => (
    <svg width="80" height="80" viewBox="0 0 80 80" fill="none">
      <rect x="28" y="35" width="24" height="8" rx="3" fill={C.cyan} style={{ boxShadow: `0 0 20px ${C.cyan}` }} />
      <rect x="38" y="42" width="6" height="28" rx="3" fill={C.cyan} />
      <rect x="16" y="30" width="18" height="14" rx="4" fill={C.cyan} />
    </svg>
  );

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: C.bg,
        perspective: 1000,
        transformStyle: "preserve-3d",
        transform: `translateZ(${cameraPush}px)`,
      }}
    >
      {/* Massive bloom */}
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: "40%",
          transform: "translate(-50%, -50%)",
          width: 400 * bloomIntensity,
          height: 400 * bloomIntensity,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${C.cyan}44, transparent 70%)`,
          opacity: Math.min(bloomIntensity, 1),
        }}
      />

      {/* Chairman seat glow */}
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: "40%",
          transform: "translate(-50%, -50%)",
          width: 120,
          height: 120,
          borderRadius: "50%",
          background: `radial-gradient(circle, ${C.cyan}66, ${C.cyan}22, transparent)`,
          ...glowStyle(C.cyan, bloomIntensity * 1.5),
        }}
      />

      {/* Gavel icon */}
      {frame >= 20 && (
        <div
          style={{
            position: "absolute",
            left: "50%",
            top: "35%",
            transform: `translate(-50%, -50%) scale(${verdictScale})`,
            opacity: verdictOpacity,
          }}
        >
          <GavelIcon />
        </div>
      )}

      {/* VERDICT text */}
      <div
        style={{
          position: "absolute",
          top: "58%",
          left: 0,
          right: 0,
          textAlign: "center",
          transform: `scale(${verdictScale})`,
          opacity: verdictOpacity,
        }}
      >
        <div style={{ fontSize: 72, fontFamily: "Inter, sans-serif", fontWeight: 900, color: C.cyan, letterSpacing: "0.05em", ...textGlow(C.cyan, 40 * bloomIntensity) }}>
          THE CHAIRMAN
        </div>
        <div style={{ fontSize: 56, fontFamily: "Inter, sans-serif", fontWeight: 900, color: C.magenta, marginTop: 8, ...textGlow(C.magenta, 30 * bloomIntensity) }}>
          GIVES YOU A VERDICT
        </div>
        <div style={{ fontSize: 22, fontFamily: "Inter, sans-serif", color: `${C.text}88`, marginTop: 16 }}>
          Not just an answer — a decision.
        </div>
      </div>
    </div>
  );
};

// ─── SCENE 5: CTA ────────────────────────────────────────────────────────────

const Scene5_CTA: React.FC = () => {
  const frame = useCurrentFrame();

  const fadeIn = interpolate(frame, [10, 40], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  const breathe = Math.sin(frame * 0.05) * 0.08 + 1;

  const malFade = interpolate(frame, [50, 75], [0, 1], {
    extrapolateRight: "clamp",
  });

  const byeFade = interpolate(frame, [90, 110], [0, 1], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: "#000000",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 24,
        opacity: fadeIn,
      }}
    >
      {/* Main CTA */}
      <div
        style={{
          transform: `scale(${breathe})`,
          textAlign: "center",
          padding: "0 60px",
        }}
      >
        <div
          style={{
            fontSize: 42,
            fontFamily: "Inter, sans-serif",
            fontWeight: 900,
            color: C.cyan,
            lineHeight: 1.2,
            ...textGlow(C.cyan, 30),
          }}
        >
          Comment "COUNCIL"
        </div>
        <div
          style={{
            fontSize: 42,
            fontFamily: "Inter, sans-serif",
            fontWeight: 900,
            color: C.magenta,
            marginTop: 8,
            ...textGlow(C.magenta, 25),
          }}
        >
          and I'll send you the guide
        </div>
      </div>

      {/* Malayalam */}
      <div style={{ opacity: malFade, textAlign: "center" }}>
        <span style={{ fontSize: 20, fontFamily: "Inter, sans-serif", color: `${C.text}77` }}>
          "if you want it comment council and i will sent you the guide"
        </span>
      </div>

      {/* Separator */}
      <div
        style={{
          width: 120,
          height: 2,
          background: `linear-gradient(90deg, transparent, ${C.cyan}, transparent)`,
          opacity: malFade,
        }}
      />

      {/* See you in the next one */}
      <div style={{ opacity: byeFade }}>
        <span
          style={{
            fontSize: 24,
            fontFamily: "Inter, sans-serif",
            fontWeight: 600,
            color: `${C.text}99`,
            ...textGlow(C.text, 10),
          }}
        >
          See you in the next one.
        </span>
      </div>
    </div>
  );
};

// ─── SFX LAYER ────────────────────────────────────────────────────────────────

// SFX timestamps (in frames, 0-indexed)
// Scene 1 — Hook: seat orbs appear
// Frame ~10: whoosh (seats lighting up)
// Frame ~60: yippee (text slam in)

// Scene 2 — Agents:
// Frame 8*30+10=250: whoosh (first card fly in)
// Frame 8*30+25=265: uiSwitch (second card)
// Frame 8*30+40=280: uiSwitch (third card)
// Frame 8*30+55=295: uiSwitch (fourth card)
// Frame 8*30+70=310: uiSwitch (fifth card)

// Scene 3 — Debate:
// Frame 38*30+10=1170: dramaticBoomer (beams appear)
// Frame 38*30+30=1190: vineBoom (convergence glow)

// Scene 4 — Chairman:
// Frame 48*30+25=1465: dramaticBoomer (bloom peak)
// Frame 48*30+30=1470: vineBoom (verdict slam)

// Scene 5 — CTA:
// Frame 58*30+40=1780: whoosh (fade to black)
// Frame 58*30+90=1830: uiSwitch (CTA breathe pulse)

const SFXLayer: React.FC = () => {
  return (
    <>
      {/* Scene 1 — Hook */}
      <Sequence from={10} durationInFrames={1}>
        <Audio src={whoosh} />
      </Sequence>
      <Sequence from={60} durationInFrames={1}>
        <Audio src={yippee} />
      </Sequence>

      {/* Scene 2 — Agent cards */}
      <Sequence from={250} durationInFrames={1}>
        <Audio src={whoosh} />
      </Sequence>
      <Sequence from={265} durationInFrames={1}>
        <Audio src={uiSwitch} />
      </Sequence>
      <Sequence from={280} durationInFrames={1}>
        <Audio src={uiSwitch} />
      </Sequence>
      <Sequence from={295} durationInFrames={1}>
        <Audio src={uiSwitch} />
      </Sequence>
      <Sequence from={310} durationInFrames={1}>
        <Audio src={uiSwitch} />
      </Sequence>

      {/* Scene 3 — Debate beams */}
      <Sequence from={1170} durationInFrames={1}>
        <Audio src={dramaticBoomer} />
      </Sequence>
      <Sequence from={1190} durationInFrames={1}>
        <Audio src={vineBoom} />
      </Sequence>

      {/* Scene 4 — Chairman */}
      <Sequence from={1465} durationInFrames={1}>
        <Audio src={dramaticBoomer} />
      </Sequence>
      <Sequence from={1470} durationInFrames={1}>
        <Audio src={vineBoom} />
      </Sequence>

      {/* Scene 5 — CTA */}
      <Sequence from={1780} durationInFrames={1}>
        <Audio src={whoosh} />
      </Sequence>
      <Sequence from={1830} durationInFrames={1}>
        <Audio src={uiSwitch} />
      </Sequence>
    </>
  );
};

// ─── MAIN COMPOSITION ────────────────────────────────────────────────────────

export const Council: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: C.bg }}>
      <Sequence from={0} durationInFrames={8 * fps}>
        <Scene1_Hook />
      </Sequence>
      <Sequence from={8 * fps} durationInFrames={30 * fps}>
        <Scene2_Agents />
      </Sequence>
      <Sequence from={38 * fps} durationInFrames={10 * fps}>
        <Scene3_Debate />
      </Sequence>
      <Sequence from={48 * fps} durationInFrames={10 * fps}>
        <Scene4_Chairman />
      </Sequence>
      <Sequence from={58 * fps} durationInFrames={12 * fps}>
        <Scene5_CTA />
      </Sequence>
      <SFXLayer />
    </AbsoluteFill>
  );
};

