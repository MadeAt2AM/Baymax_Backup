import {
  useCurrentFrame,
  interpolate,
  Easing,
  AbsoluteFill,
  Sequence,
} from "remotion";

// ─── HELPERS ────────────────────────────────────────────────────────────────

const DarkGrid = () => (
  <div
    style={{
      position: "absolute",
      inset: 0,
      backgroundColor: "#0d0d0f",
      backgroundImage: `
        linear-gradient(rgba(255,255,255,0.03) 1px, transparent 1px),
        linear-gradient(90deg, rgba(255,255,255,0.03) 1px, transparent 1px)
      `,
      backgroundSize: "48px 48px",
    }}
  />
);

// ─── SCENE 1 ───────────────────────────────────────────────────────────────
// Day 1: Three project folders spinning in with 3D card effect

const SocialCard = ({ frame }: { frame: number }) => {
  const opacity = interpolate(frame, [0, 20], [0, 1], {
    extrapolateRight: "clamp",
  });
  const scale = interpolate(frame, [0, 30], [0.5, 1], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const rotateX = interpolate(frame, [0, 30], [30, 15], {
    extrapolateRight: "clamp",
  });
  const rotateY = interpolate(frame, [0, 30], [-20, -10], {
    extrapolateRight: "clamp",
  });
  const translateY = interpolate(frame, [0, 30], [80, 0], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        left: 80,
        top: 320,
        width: 280,
        height: 380,
        background: "linear-gradient(145deg, #1a0a20, #2d0f40)",
        borderRadius: 20,
        border: "1px solid rgba(219, 112, 219, 0.4)",
        boxShadow:
          "0 0 40px rgba(219, 112, 219, 0.3), inset 0 0 20px rgba(219, 112, 219, 0.1)",
        opacity,
        transform: `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(${scale}) translateY(${translateY}px)`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        padding: "30px 20px",
        gap: 16,
      }}
    >
      <div
        style={{
          fontSize: 13,
          color: "#ff6bcb",
          fontWeight: 700,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
        }}
      >
        Social Media
      </div>
      {/* Instagram icon */}
      <svg width="60" height="60" viewBox="0 0 24 24" fill="none">
        <rect
          x="2"
          y="2"
          width="20"
          height="20"
          rx="5"
          stroke="#ff6bcb"
          strokeWidth="1.5"
        />
        <circle cx="12" cy="12" r="5" stroke="#ff6bcb" strokeWidth="1.5" />
        <circle cx="17.5" cy="6.5" r="1" fill="#ff6bcb" />
      </svg>
      {/* YouTube icon */}
      <svg width="60" height="60" viewBox="0 0 24 24" fill="none">
        <rect
          x="2"
          y="4"
          width="20"
          height="16"
          rx="4"
          stroke="#a855f7"
          strokeWidth="1.5"
        />
        <polygon points="10,8 16,12 10,16" fill="#a855f7" />
      </svg>
      <div
        style={{ fontSize: 11, color: "rgba(255,255,255,0.5)", marginTop: 8 }}
      >
        Instagram · YouTube · X
      </div>
      <div
        style={{
          marginTop: 16,
          padding: "8px 16px",
          background: "linear-gradient(90deg, #ff6bcb, #a855f7)",
          borderRadius: 8,
          fontSize: 11,
          color: "#fff",
          fontWeight: 700,
        }}
      >
        Content & Scheduling
      </div>
    </div>
  );
};

const WebDevCard = ({ frame }: { frame: number }) => {
  const opacity = interpolate(frame, [10, 30], [0, 1], {
    extrapolateRight: "clamp",
  });
  const scale = interpolate(frame, [10, 40], [0.5, 1], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const rotateX = interpolate(frame, [10, 40], [30, 15], {
    extrapolateRight: "clamp",
  });
  const rotateY = interpolate(frame, [10, 40], [20, 10], {
    extrapolateRight: "clamp",
  });
  const translateY = interpolate(frame, [10, 40], [80, 0], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        left: 400,
        top: 320,
        width: 280,
        height: 380,
        background: "linear-gradient(145deg, #0a1a1a, #0f2d2d)",
        borderRadius: 20,
        border: "1px solid rgba(52, 211, 153, 0.4)",
        boxShadow:
          "0 0 40px rgba(52, 211, 153, 0.3), inset 0 0 20px rgba(52, 211, 153, 0.1)",
        opacity,
        transform: `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(${scale}) translateY(${translateY}px)`,
        display: "flex",
        flexDirection: "column",
        padding: "24px 20px",
        gap: 12,
      }}
    >
      <div
        style={{
          fontSize: 13,
          color: "#34d399",
          fontWeight: 700,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
        }}
      >
        Web Dev
      </div>
      {/* Terminal window */}
      <div
        style={{
          background: "#0a0e0e",
          borderRadius: 10,
          border: "1px solid rgba(52, 211, 153, 0.3)",
          padding: "12px 16px",
          fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
          fontSize: 11,
          lineHeight: 1.8,
          flex: 1,
        }}
      >
        <div style={{ color: "#34d399" }}>
          <span style={{ color: "#f97316" }}>$</span> npm run dev
        </div>
        <div style={{ color: "#6ee7b7", marginTop: 4 }}>▶ Compiling...</div>
        <div style={{ color: "#6ee7b7" }}>▶ Ready on :3000</div>
        <div style={{ color: "rgba(255,255,255,0.3)", marginTop: 8 }}>
          <span style={{ color: "#a78bfa" }}>{"<"}</span>
          <span style={{ color: "#f97316" }}>div</span>
          <span style={{ color: "#a78bfa" }}>{">"}</span>
          {" App"}
        </div>
      </div>
      <div
        style={{
          padding: "8px 16px",
          background: "linear-gradient(90deg, #059669, #34d399)",
          borderRadius: 8,
          fontSize: 11,
          color: "#fff",
          fontWeight: 700,
          textAlign: "center",
        }}
      >
        Sites & Web Apps
      </div>
    </div>
  );
};

const AdminCard = ({ frame }: { frame: number }) => {
  const opacity = interpolate(frame, [20, 40], [0, 1], {
    extrapolateRight: "clamp",
  });
  const scale = interpolate(frame, [20, 50], [0.5, 1], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const rotateX = interpolate(frame, [20, 50], [30, 15], {
    extrapolateRight: "clamp",
  });
  const rotateY = interpolate(frame, [20, 50], [10, -10], {
    extrapolateRight: "clamp",
  });
  const translateY = interpolate(frame, [20, 50], [80, 0], {
    extrapolateRight: "clamp",
  });

  const tasks = ["Project Tracker", "Finances", "Notes", "Habits"];
  return (
    <div
      style={{
        position: "absolute",
        left: 720,
        top: 320,
        width: 280,
        height: 380,
        background: "linear-gradient(145deg, #1a150a, #2d2510)",
        borderRadius: 20,
        border: "1px solid rgba(251, 191, 36, 0.4)",
        boxShadow:
          "0 0 40px rgba(251, 191, 36, 0.3), inset 0 0 20px rgba(251, 191, 36, 0.1)",
        opacity,
        transform: `perspective(1000px) rotateX(${rotateX}deg) rotateY(${rotateY}deg) scale(${scale}) translateY(${translateY}px)`,
        display: "flex",
        flexDirection: "column",
        padding: "24px 20px",
        gap: 14,
      }}
    >
      <div
        style={{
          fontSize: 13,
          color: "#fbbf24",
          fontWeight: 700,
          letterSpacing: "0.1em",
          textTransform: "uppercase",
        }}
      >
        Personal Admin
      </div>
      <div
        style={{ display: "flex", flexDirection: "column", gap: 10, flex: 1 }}
      >
        {tasks.map((task, i) => {
          const checkFrame = frame - 40 - i * 6;
          const checked = checkFrame > 0;
          return (
            <div
              key={task}
              style={{ display: "flex", alignItems: "center", gap: 10 }}
            >
              <div
                style={{
                  width: 20,
                  height: 20,
                  borderRadius: 5,
                  border: "2px solid #fbbf24",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  flexShrink: 0,
                  transform: `scale(${checked ? 1 : 0})`,
                }}
              >
                <svg width="12" height="12" viewBox="0 0 12 12" fill="none">
                  <polyline
                    points="2,6 5,9 10,3"
                    stroke="#fbbf24"
                    strokeWidth="2"
                    strokeLinecap="round"
                    strokeLinejoin="round"
                  />
                </svg>
              </div>
              <span
                style={{
                  fontSize: 12,
                  color: checked
                    ? "rgba(255,255,255,0.5)"
                    : "rgba(255,255,255,0.8)",
                  textDecoration: checked ? "line-through" : "none",
                }}
              >
                {task}
              </span>
            </div>
          );
        })}
      </div>
      <div
        style={{
          padding: "8px 16px",
          background: "linear-gradient(90deg, #d97706, #fbbf24)",
          borderRadius: 8,
          fontSize: 11,
          color: "#fff",
          fontWeight: 700,
          textAlign: "center",
        }}
      >
        Life Admin Hub
      </div>
    </div>
  );
};

const KineticWord = ({
  children,
  startFrame,
}: {
  children: string;
  startFrame: number;
}) => {
  const frame = useCurrentFrame();
  const f = frame - startFrame;
  const opacity = interpolate(f, [0, 10, 40, 50], [0, 1, 1, 0], {
    extrapolateRight: "clamp",
  });
  const translateX = interpolate(f, [0, 50], [-100, 1200], {
    extrapolateRight: "clamp",
    easing: Easing.linear,
  });
  const scale = interpolate(f, [0, 20, 40], [0.5, 1.2, 0.8], {
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        top: "50%",
        left: 0,
        transform: `translateX(${translateX}px) scale(${scale})`,
        opacity,
        fontSize: 120,
        fontFamily: "'Space Grotesk', sans-serif",
        fontWeight: 900,
        color: "transparent",
        WebkitTextStroke: "1px rgba(255,255,255,0.15)",
        whiteSpace: "nowrap",
        pointerEvents: "none",
        zIndex: 0,
      }}
    >
      {children}
    </div>
  );
};

const Day1Scene = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ backgroundColor: "#0d0d0f", overflow: "hidden" }}>
      <DarkGrid />
      <div
        style={{
          position: "absolute",
          top: 60,
          left: 0,
          right: 0,
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: 14,
            color: "rgba(255,255,255,0.4)",
            fontFamily: "'Space Grotesk', sans-serif",
            letterSpacing: "0.3em",
            textTransform: "uppercase",
          }}
        >
          Day 1
        </div>
        <div
          style={{
            fontSize: 52,
            fontWeight: 900,
            color: "#fff",
            fontFamily: "'Space Grotesk', sans-serif",
            marginTop: 8,
            lineHeight: 1.1,
          }}
        >
          Create Projects For
          <br />
          Different Parts Of Your Life
        </div>
      </div>
      <SocialCard frame={Math.max(0, frame - 40)} />
      <WebDevCard frame={Math.max(0, frame - 50)} />
      <AdminCard frame={Math.max(0, frame - 60)} />
      <KineticWord startFrame={0}>SOCIAL</KineticWord>
      <KineticWord startFrame={15}>DEV</KineticWord>
      <KineticWord startFrame={30}>ADMIN</KineticWord>
    </AbsoluteFill>
  );
};

// ─── SCENE 2 ───────────────────────────────────────────────────────────────
// Day 2: User + Claude collaboration with tasks flying

const UserIcon = ({ frame }: { frame: number }) => {
  const opacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });
  return (
    <div
      style={{
        position: "absolute",
        left: 60,
        top: 360,
        width: 160,
        height: 200,
        background: "linear-gradient(145deg, #1a1a2e, #16213e)",
        borderRadius: 20,
        border: "1px solid rgba(96, 165, 250, 0.4)",
        boxShadow: "0 0 30px rgba(96, 165, 250, 0.2)",
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 12,
        opacity,
        transform: `perspective(1000px) rotateY(-8deg)`,
      }}
    >
      <div
        style={{
          width: 64,
          height: 64,
          borderRadius: "50%",
          background: "linear-gradient(135deg, #60a5fa, #3b82f6)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 28,
          fontWeight: 900,
          color: "#fff",
          fontFamily: "'Space Grotesk', sans-serif",
        }}
      >
        CV
      </div>
      <div
        style={{
          fontSize: 12,
          color: "rgba(255,255,255,0.6)",
          fontFamily: "'Space Grotesk', sans-serif",
        }}
      >
        Christus Vincent
      </div>
      <div
        style={{
          fontSize: 10,
          color: "rgba(255,255,255,0.3)",
          fontFamily: "'Space Grotesk', sans-serif",
        }}
      >
        @made.at.2am
      </div>
    </div>
  );
};

const ClaudeIcon = ({ frame }: { frame: number }) => {
  const opacity = interpolate(frame, [0, 15], [0, 1], {
    extrapolateRight: "clamp",
  });
  const pulse = Math.sin(frame * 0.15) * 0.5 + 0.5;
  const glowSize = 20 + pulse * 30;
  return (
    <div
      style={{
        position: "absolute",
        right: 60,
        top: 360,
        width: 160,
        height: 200,
        background: "linear-gradient(145deg, #1a1208, #2d2008)",
        borderRadius: 20,
        border: "1px solid rgba(210, 168, 76, 0.5)",
        boxShadow: `0 0 ${glowSize}px rgba(210, 168, 76, ${0.3 + pulse * 0.3})`,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        gap: 12,
        opacity,
        transform: `perspective(1000px) rotateY(8deg)`,
      }}
    >
      <div
        style={{
          width: 64,
          height: 64,
          borderRadius: 16,
          background: "linear-gradient(135deg, #d2a84c, #8b6914)",
          display: "flex",
          alignItems: "center",
          justifyContent: "center",
          fontSize: 10,
          fontWeight: 900,
          color: "#fff",
          fontFamily: "'Space Grotesk', sans-serif",
          textAlign: "center",
          lineHeight: 1.2,
        }}
      >
        CLAUDE
        <br />
        <span style={{ fontSize: 8 }}>by Anthropic</span>
      </div>
      <div
        style={{
          fontSize: 12,
          color: "rgba(255,255,255,0.6)",
          fontFamily: "'Space Grotesk', sans-serif",
        }}
      >
        AI Assistant
      </div>
      <div
        style={{
          fontSize: 10,
          color: "rgba(210, 168, 76, 0.6)",
          fontFamily: "'Space Grotesk', sans-serif",
        }}
      >
        ↗ Online
      </div>
    </div>
  );
};

const TaskBeam = ({ index, total }: { index: number; total: number }) => {
  const frame = useCurrentFrame();
  const delay = index * 20;
  const f = frame - delay;
  const progress = interpolate(f, [0, 60], [0, 1], {
    extrapolateRight: "clamp",
  });
  const tasks = [
    "Write Code",
    "Review PR",
    "Fix Bug",
    "Add Feature",
    "Refactor",
  ];
  const task = tasks[index % tasks.length];

  const x = interpolate(progress, [0, 1], [200, 720]);
  const opacity = interpolate(progress, [0, 0.1, 0.8, 1], [0, 1, 1, 0]);
  const done = progress > 0.6;
  const scale = interpolate(progress, [0, 0.5, 0.6, 1], [0.8, 1.1, 1, 0.8]);

  return (
    <div
      style={{
        position: "absolute",
        top: 200 + index * 50,
        transform: `translateX(${x}px) scale(${scale})`,
        opacity,
        background: done
          ? "linear-gradient(90deg, #059669, #34d399)"
          : "linear-gradient(90deg, #3b82f6, #60a5fa)",
        borderRadius: 8,
        padding: "6px 16px",
        fontSize: 11,
        fontWeight: 700,
        color: "#fff",
        fontFamily: "'Space Grotesk', sans-serif",
        whiteSpace: "nowrap",
        boxShadow: done
          ? "0 0 20px rgba(52, 211, 153, 0.5)"
          : "0 0 15px rgba(96, 165, 250, 0.4)",
      }}
    >
      {task} {done ? "✓" : "→"}
    </div>
  );
};

const CommentCTA = () => {
  const frame = useCurrentFrame();
  const blink = Math.floor(frame / 15) % 2;
  return (
    <div
      style={{
        position: "absolute",
        bottom: 80,
        left: 0,
        right: 0,
        textAlign: "center",
      }}
    >
      <div
        style={{
          display: "inline-block",
          padding: "16px 48px",
          background: "linear-gradient(90deg, #d2a84c, #f5d98a, #d2a84c)",
          borderRadius: 12,
          fontSize: 42,
          fontWeight: 900,
          color: "#0a0a0a",
          fontFamily: "'Space Grotesk', sans-serif",
          letterSpacing: "0.05em",
          boxShadow: "0 0 60px rgba(210, 168, 76, 0.5)",
        }}
      >
        COMMENT "CLAUDE"{blink === 0 ? "_" : " "}
      </div>
    </div>
  );
};

const Day2Scene = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ backgroundColor: "#0a0a12", overflow: "hidden" }}>
      <DarkGrid />
      <div
        style={{
          position: "absolute",
          top: 60,
          left: 0,
          right: 0,
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: 14,
            color: "rgba(255,255,255,0.4)",
            fontFamily: "'Space Grotesk', sans-serif",
            letterSpacing: "0.3em",
            textTransform: "uppercase",
          }}
        >
          Day 2
        </div>
        <div
          style={{
            fontSize: 44,
            fontWeight: 900,
            color: "#fff",
            fontFamily: "'Space Grotesk', sans-serif",
            marginTop: 8,
            lineHeight: 1.2,
            padding: "0 80px",
          }}
        >
          Try Claude Code —<br />
          Comment & Get Resources
        </div>
      </div>
      <UserIcon frame={Math.max(0, frame - 0)} />
      <ClaudeIcon frame={Math.max(0, frame - 0)} />
      {[0, 1, 2, 3, 4].map((i) => (
        <TaskBeam key={i} index={i} total={5} />
      ))}
      <Sequence from={40}>
        <CommentCTA />
      </Sequence>
    </AbsoluteFill>
  );
};

// ─── SCENE 3 ───────────────────────────────────────────────────────────────
// Day 3: Claude logo magnet pulling in Drive, Gmail, Notion

const OrbitRing = ({
  radius,
  frame,
  color,
  dashOffset,
}: {
  radius: number;
  frame: number;
  color: string;
  dashOffset: number;
}) => {
  const circumference = 2 * Math.PI * radius;
  const rotation = (frame * 2) % 360;
  return (
    <svg
      style={{
        position: "absolute",
        top: "50%",
        left: "50%",
        transform: `translate(-50%, -50%) rotate(${rotation}deg)`,
        overflow: "visible",
      }}
      width={radius * 2}
      height={radius * 2}
    >
      <circle
        cx={radius}
        cy={radius}
        r={radius}
        fill="none"
        stroke={color}
        strokeWidth="1"
        strokeDasharray={`${circumference * 0.3} ${circumference * 0.7}`}
        strokeDashoffset={dashOffset}
        opacity={0.4}
      />
    </svg>
  );
};

const FloatingApp = ({
  app,
  startFrame,
  x,
  y,
  color,
}: {
  app: string;
  startFrame: number;
  x: number;
  y: number;
  color: string;
}) => {
  const frame = useCurrentFrame();
  const f = Math.max(0, frame - startFrame);

  const progress = interpolate(f, [0, 40], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  const connected = f > 35;
  const scale = connected
    ? interpolate(f, [35, 45], [1, 1.2, 1], { extrapolateRight: "clamp" })
    : progress;
  const flashOpacity = connected
    ? interpolate(f, [35, 38], [0.8, 0], { extrapolateRight: "clamp" })
    : 0;

  const label: Record<string, string> = {
    drive: "Google Drive",
    gmail: "Gmail",
    notion: "Notion",
  };

  return (
    <>
      {flashOpacity > 0 && (
        <div
          style={{
            position: "absolute",
            left: x - 30,
            top: y - 30,
            width: 60,
            height: 60,
            borderRadius: "50%",
            background: "#fff",
            opacity: flashOpacity,
            pointerEvents: "none",
          }}
        />
      )}
      <div
        style={{
          position: "absolute",
          left: x,
          top: y,
          transform: `translate(-50%, -50%) scale(${scale})`,
          background: "linear-gradient(145deg, #1a1a1a, #252525)",
          borderRadius: 16,
          border: `1px solid ${color}`,
          boxShadow: connected ? `0 0 30px ${color}` : "none",
          padding: "16px 20px",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          gap: 8,
          minWidth: 100,
        }}
      >
        <div style={{ fontSize: 24 }}>
          {app === "drive" && (
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
              <path
                d="M12 2L2 9l10 7 10-7-10-7z"
                fill="#4285F4"
                opacity="0.7"
              />
              <path d="M2 9v8l10 7 10-7V9" stroke="#4285F4" strokeWidth="1.5" />
              <path d="M2 17l10 7 10-7" stroke="#4285F4" strokeWidth="1.5" />
              <path d="M12 2v15" stroke="#34A853" strokeWidth="1.5" />
            </svg>
          )}
          {app === "gmail" && (
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
              <rect
                x="2"
                y="4"
                width="20"
                height="16"
                rx="2"
                fill="#EA4335"
                opacity="0.8"
              />
              <path d="M2 7l10 6 10-6" stroke="#fff" strokeWidth="1.5" />
            </svg>
          )}
          {app === "notion" && (
            <svg width="32" height="32" viewBox="0 0 24 24" fill="none">
              <rect
                x="3"
                y="3"
                width="18"
                height="18"
                rx="3"
                fill="#fff"
                opacity="0.9"
              />
              <rect x="7" y="7" width="4" height="3" rx="1" fill="#000" />
              <rect x="13" y="7" width="4" height="3" rx="1" fill="#000" />
              <rect x="7" y="12" width="10" height="2" rx="1" fill="#000" />
            </svg>
          )}
        </div>
        <div
          style={{
            fontSize: 10,
            color: "rgba(255,255,255,0.7)",
            fontFamily: "'Space Grotesk', sans-serif",
            fontWeight: 600,
          }}
        >
          {label[app]}
        </div>
      </div>
    </>
  );
};

const Day3Scene = () => {
  const frame = useCurrentFrame();
  const centerX = 540;
  const centerY = 500;

  const pulse = Math.sin(frame * 0.1) * 0.5 + 0.5;

  return (
    <AbsoluteFill style={{ backgroundColor: "#08080f", overflow: "hidden" }}>
      <DarkGrid />
      <div
        style={{
          position: "absolute",
          top: 60,
          left: 0,
          right: 0,
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: 14,
            color: "rgba(255,255,255,0.4)",
            fontFamily: "'Space Grotesk', sans-serif",
            letterSpacing: "0.3em",
            textTransform: "uppercase",
          }}
        >
          Day 3
        </div>
        <div
          style={{
            fontSize: 40,
            fontWeight: 900,
            color: "#fff",
            fontFamily: "'Space Grotesk', sans-serif",
            marginTop: 8,
            lineHeight: 1.2,
            padding: "0 60px",
          }}
        >
          Connect All Your Tools —<br />
          Drive, Gmail, Notion & More
        </div>
      </div>

      {/* Orbit rings */}
      <OrbitRing radius={180} frame={frame} color="#d2a84c" dashOffset={0} />
      <OrbitRing radius={260} frame={frame} color="#d2a84c" dashOffset={100} />

      {/* Claude center */}
      <div
        style={{
          position: "absolute",
          left: centerX,
          top: centerY,
          transform: "translate(-50%, -50%)",
          width: 100,
          height: 100,
          borderRadius: 24,
          background: "linear-gradient(135deg, #d2a84c, #8b6914)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          boxShadow: `0 0 ${40 + pulse * 40}px rgba(210, 168, 76, ${0.4 + pulse * 0.3})`,
          fontSize: 9,
          fontWeight: 900,
          color: "#fff",
          fontFamily: "'Space Grotesk', sans-serif",
          textAlign: "center",
          lineHeight: 1.3,
          zIndex: 10,
        }}
      >
        CLAUDE
        <span style={{ fontSize: 7, fontWeight: 400 }}>by Anthropic</span>
      </div>

      {/* App icons */}
      <FloatingApp
        app="drive"
        startFrame={30}
        x={120}
        y={220}
        color="rgba(66, 133, 244, 0.6)"
      />
      <FloatingApp
        app="gmail"
        startFrame={50}
        x={960}
        y={220}
        color="rgba(234, 67, 53, 0.6)"
      />
      <FloatingApp
        app="notion"
        startFrame={70}
        x={120}
        y={780}
        color="rgba(255, 255, 255, 0.4)"
      />
    </AbsoluteFill>
  );
};

// ─── SCENE 4 ───────────────────────────────────────────────────────────────
// Day 4: Matrix-style terminal → phone UI pops out with camera shake

const CodeRain = ({ frame }: { frame: number }) => {
  const lines = [
    "import { useState } from 'react';",
    "const fetch = require('fets');",
    "npm install @anthropic-ai/claude-code",
    "claude-code --init",
    "mkdir new-project && cd new-project",
    "npm init -y",
    "touch App.tsx",
    "npx remotion studio",
    "npm run dev",
    "git add .",
    "git commit -m 'init'",
    "git push origin main",
    "export default function App() {",
    "  const [state, setState] = useState({});",
    "  return <div className='app'>...</div>;",
    "}",
  ];

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        overflow: "hidden",
        opacity: 0.15,
        fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
        fontSize: 11,
        lineHeight: 1.6,
        color: "#4ade80",
        padding: "20px 40px",
      }}
    >
      {lines.map((line, i) => {
        const f = (frame - i * 3) % (lines.length * 6);
        const visible = f < 60;
        const yOffset = visible ? interpolate(f, [0, 60], [0, 900]) : 0;
        return (
          <div key={i} style={{ transform: `translateY(${yOffset}px)` }}>
            {line}
          </div>
        );
      })}
    </div>
  );
};

const PhoneMockup = ({ frame }: { frame: number }) => {
  const f = Math.max(0, frame - 20);
  const popProgress = interpolate(f, [0, 40], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1.4, 0.3, 1),
  });
  const scale = popProgress;
  const shake = f < 8 ? interpolate(f, [0, 2, 4, 6, 8], [0, -6, 6, -4, 0]) : 0;

  const elements = [
    { y: 60, w: 100, h: 12, color: "#60a5fa", label: "Header" },
    { y: 85, w: 140, h: 8, color: "rgba(255,255,255,0.4)", label: "Subtitle" },
    { y: 110, w: 160, h: 60, color: "#34d399", label: "Chart" },
    { y: 185, w: 75, h: 40, color: "#f472b6", label: "Card 1" },
    { y: 185, w: 75, h: 40, color: "#fbbf24", label: "Card 2" },
    { y: 240, w: 160, h: 20, color: "#a78bfa", label: "Button" },
  ];

  return (
    <div
      style={{
        position: "absolute",
        left: 540,
        top: 480,
        transform: `translate(-50%, -50%) scale(${scale}) translateX(${shake}px)`,
        width: 180,
        height: 360,
        background: "#111",
        borderRadius: 28,
        border: "3px solid #333",
        boxShadow: "0 0 60px rgba(0,0,0,0.8)",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
        padding: 16,
        gap: 8,
      }}
    >
      {/* notch */}
      <div
        style={{
          width: 60,
          height: 8,
          background: "#222",
          borderRadius: 4,
          margin: "0 auto 8px",
        }}
      />
      {elements.map((el, i) => (
        <div
          key={i}
          style={{
            position: "absolute",
            left: 10,
            top: el.y,
            width: el.w,
            height: el.h,
            background: el.color,
            borderRadius: 6,
            opacity: 0.9,
          }}
        />
      ))}
    </div>
  );
};

const Day4Scene = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ backgroundColor: "#050a05", overflow: "hidden" }}>
      <DarkGrid />
      <CodeRain frame={Math.max(0, frame - 0)} />
      <div
        style={{
          position: "absolute",
          top: 60,
          left: 0,
          right: 0,
          textAlign: "center",
        }}
      >
        <div
          style={{
            fontSize: 14,
            color: "rgba(255,255,255,0.4)",
            fontFamily: "'Space Grotesk', sans-serif",
            letterSpacing: "0.3em",
            textTransform: "uppercase",
          }}
        >
          Day 4
        </div>
        <div
          style={{
            fontSize: 40,
            fontWeight: 900,
            color: "#fff",
            fontFamily: "'Space Grotesk', sans-serif",
            marginTop: 8,
            lineHeight: 1.2,
            padding: "0 60px",
          }}
        >
          Install Claude Code —<br />
          Build Anything You Want
        </div>
      </div>
      <PhoneMockup frame={Math.max(0, frame - 40)} />
    </AbsoluteFill>
  );
};

// ─── OUTRO / CTA ────────────────────────────────────────────────────────────
// Comment CLAUDE → DM popup

const CommentBox = ({ frame }: { frame: number }) => {
  const progress = interpolate(frame, [0, 50], [0, 1], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const letters = "CLAUDE".split("");
  return (
    <div
      style={{
        position: "absolute",
        bottom: 200,
        left: "50%",
        transform: `translateX(-50%)`,
        display: "flex",
        alignItems: "center",
        gap: 4,
        opacity: progress,
      }}
    >
      {letters.map((letter, i) => {
        const letterProgress = interpolate(frame, [i * 6, i * 6 + 20], [0, 1], {
          extrapolateRight: "clamp",
        });
        return (
          <div
            key={i}
            style={{
              width: 40,
              height: 50,
              background: "#1a1a1a",
              borderRadius: 8,
              border: "1px solid #333",
              display: "flex",
              alignItems: "center",
              justifyContent: "center",
              fontSize: 22,
              fontWeight: 900,
              color: letterProgress > 0.5 ? "#d2a84c" : "#333",
              fontFamily: "'Space Grotesk', sans-serif",
              transition: "color 0.1s",
            }}
          >
            {letter}
          </div>
        );
      })}
    </div>
  );
};

const InstagramDM = ({ frame }: { frame: number }) => {
  const f = Math.max(0, frame - 30);
  const slideUp = interpolate(f, [0, 40], [200, 0], {
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const pulse = (Math.sin(f * 0.1) + 1) * 0.5;
  const scale = 1 + pulse * 0.06;

  return (
    <div
      style={{
        position: "absolute",
        right: 80,
        bottom: 80,
        width: 300,
        background: "#121212",
        borderRadius: 20,
        border: "1px solid #2a2a2a",
        overflow: "hidden",
        transform: `translateY(${slideUp}px)`,
        boxShadow: "0 20px 60px rgba(0,0,0,0.6)",
      }}
    >
      {/* DM header */}
      <div
        style={{
          background: "#1a1a1a",
          padding: "12px 16px",
          display: "flex",
          alignItems: "center",
          gap: 10,
          borderBottom: "1px solid #2a2a2a",
        }}
      >
        <div
          style={{
            width: 32,
            height: 32,
            borderRadius: "50%",
            background: "linear-gradient(135deg, #d2a84c, #8b6914)",
            display: "flex",
            alignItems: "center",
            justifyContent: "center",
            fontSize: 8,
            fontWeight: 900,
            color: "#fff",
            fontFamily: "'Space Grotesk', sans-serif",
          }}
        >
          MADE
          <br />
          AT2AM
        </div>
        <div>
          <div
            style={{
              fontSize: 12,
              color: "#fff",
              fontFamily: "'Space Grotesk', sans-serif",
              fontWeight: 700,
            }}
          >
            @made.at.2am
          </div>
          <div
            style={{
              fontSize: 10,
              color: "rgba(255,255,255,0.4)",
              fontFamily: "'Space Grotesk', sans-serif",
            }}
          >
            Active now
          </div>
        </div>
      </div>
      {/* Message bubble */}
      <div style={{ padding: "16px 16px 8px" }}>
        <div
          style={{
            background: "linear-gradient(135deg, #d2a84c, #8b6914)",
            borderRadius: "16px 16px 16px 4px",
            padding: "12px 16px",
            fontSize: 12,
            color: "#fff",
            fontFamily: "'Space Grotesk', sans-serif",
            lineHeight: 1.5,
          }}
        >
          Here's your roadmap to get started with Claude Code! 🚀
        </div>
      </div>
      {/* Action button */}
      <div style={{ padding: "8px 16px 16px" }}>
        <div
          style={{
            background: "linear-gradient(90deg, #d2a84c, #f5d98a, #d2a84c)",
            borderRadius: 10,
            padding: "12px 16px",
            textAlign: "center",
            fontSize: 14,
            fontWeight: 900,
            color: "#0a0a0a",
            fontFamily: "'Space Grotesk', sans-serif",
            transform: `scale(${scale})`,
            cursor: "pointer",
            boxShadow: `0 0 ${20 + pulse * 20}px rgba(210, 168, 76, 0.4)`,
          }}
        >
          GET ROADMAP ↓
        </div>
      </div>
    </div>
  );
};

const OutroScene = () => {
  const frame = useCurrentFrame();

  return (
    <AbsoluteFill style={{ backgroundColor: "#0d0d0f", overflow: "hidden" }}>
      <DarkGrid />
      <div
        style={{
          position: "absolute",
          top: 100,
          left: 0,
          right: 0,
          textAlign: "center",
        }}
      >
        <div
          style={{
            display: "inline-block",
            padding: "20px 64px",
            background: "linear-gradient(90deg, #d2a84c, #f5d98a, #d2a84c)",
            borderRadius: 16,
            fontSize: 56,
            fontWeight: 900,
            color: "#0a0a0a",
            fontFamily: "'Space Grotesk', sans-serif",
            letterSpacing: "0.05em",
            boxShadow: "0 0 80px rgba(210, 168, 76, 0.5)",
          }}
        >
          COMMENT "CLAUDE"
        </div>
        <div
          style={{
            marginTop: 24,
            fontSize: 22,
            color: "rgba(255,255,255,0.6)",
            fontFamily: "'Space Grotesk', sans-serif",
            lineHeight: 1.5,
          }}
        >
          I'll send you all the resources
          <br />
          you need to get started
        </div>
      </div>
      <CommentBox frame={Math.max(0, frame - 20)} />
      <InstagramDM frame={Math.max(0, frame - 10)} />
    </AbsoluteFill>
  );
};

// ─── MAIN COMPOSITION ───────────────────────────────────────────────────────

export const MainComposition: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: "#0d0d0f" }}>
      {/* Scene 1: Day 1 — 0 to 30 frames (0:00 – 1:00) */}
      <Sequence from={2} durationInFrames={110}>
        <Day1Scene />
      </Sequence>
      {/* Scene 2: Day 2 — 90 to 165 (1:00 – 2:45) */}
      <Sequence from={110} durationInFrames={75}>
        <Day2Scene />
      </Sequence>
      {/* Scene 3: Day 3 — 165 to 225 (2:45 – 4:30) */}
      <Sequence from={165} durationInFrames={60}>
        <Day3Scene />
      </Sequence>
      {/* Scene 4: Day 4 — 225 to 315 (4:30 – 7:30) */}
      <Sequence from={225} durationInFrames={90}>
        <Day4Scene />
      </Sequence>
      {/* Outro: 315 to 450 (7:30 – 10:00) */}
      <Sequence from={315}>
        <OutroScene />
      </Sequence>
    </AbsoluteFill>
  );
};
