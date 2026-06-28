import React from "react";
import { AbsoluteFill } from "remotion";

// ─── THEME ───────────────────────────────────────────────────────────────────
const THEME = {
  bg: "#0A0A0F",
  gridLine: "rgba(255,255,255,0.03)",
  glassBg: "rgba(255,255,255,0.05)",
  glassBorder: "rgba(255,255,255,0.10)",
  accentOrange: "#FF6B00",
  accentOrangeBright: "#FF8C00",
  accentOrangeDim: "rgba(255,107,0,0.20)",
  textPrimary: "#F0EDE8",
  textSecondary: "rgba(240,237,232,0.55)",
  textMuted: "rgba(240,237,232,0.30)",
};

// ─── HELPERS ─────────────────────────────────────────────────────────────────
const SectionBadge: React.FC<{ label: string; color?: string }> = ({
  label,
  color,
}) => (
  <div
    style={{
      display: "inline-block",
      background: color ?? "rgba(255,140,0,0.15)",
      border: `1px solid ${color ?? "rgba(255,140,0,0.30)"}`,
      borderRadius: 4,
      padding: "2px 10px",
      fontSize: 11,
      fontFamily: "Poppins, sans-serif",
      fontWeight: 600,
      letterSpacing: "0.12em",
      color: color ?? "#FF8C00",
      textTransform: "uppercase",
      marginBottom: 10,
    }}
  >
    {label}
  </div>
);

const GlassCard: React.FC<{
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({ children, style }) => (
  <div
    style={{
      background: THEME.glassBg,
      border: `1px solid ${THEME.glassBorder}`,
      borderRadius: 16,
      backdropFilter: "blur(12px)",
      WebkitBackdropFilter: "blur(12px)",
      padding: "20px 24px",
      ...style,
    }}
  >
    {children}
  </div>
);

const BodyText: React.FC<{
  children: React.ReactNode;
  style?: React.CSSProperties;
}> = ({ children, style }) => (
  <span
    style={{
      fontSize: 12,
      fontFamily: "Inter, sans-serif",
      fontWeight: 400,
      lineHeight: 1.65,
      color: THEME.textSecondary,
      letterSpacing: "0.01em",
      ...style,
    }}
  >
    {children}
  </span>
);

const Keyword: React.FC<{ children: React.ReactNode }> = ({ children }) => (
  <span
    style={{
      color: THEME.textPrimary,
      fontWeight: 600,
      fontFamily: "Poppins, sans-serif",
      fontSize: 12,
    }}
  >
    {children}
  </span>
);

// ─── GRID BACKGROUND ─────────────────────────────────────────────────────────
const GridBg: React.FC = () => (
  <svg
    style={{ position: "absolute", inset: 0, width: "100%", height: "100%" }}
    xmlns="http://www.w3.org/2000/svg"
  >
    <defs>
      <pattern
        id="grid"
        width="60"
        height="60"
        patternUnits="userSpaceOnUse"
      >
        <path
          d="M 60 0 L 0 0 0 60"
          fill="none"
          stroke={THEME.gridLine}
          strokeWidth="1"
        />
      </pattern>
    </defs>
    <rect width="100%" height="100%" fill="url(#grid)" />
  </svg>
);

// ─── ORANGE GRADIENT DIVIDER ──────────────────────────────────────────────────
const OrangeDivider: React.FC = () => (
  <div
    style={{
      height: 2,
      background: `linear-gradient(90deg, transparent, ${THEME.accentOrange}, ${THEME.accentOrangeBright}, transparent)`,
      borderRadius: 2,
      margin: "10px 0",
    }}
  />
);

// ─── BADGE: DO / DON'T PAIR ───────────────────────────────────────────────────
const DoDont: React.FC<{ do: string; dont: string }> = ({ do: doStr, dont }) => (
  <div
    style={{
      display: "flex",
      gap: 12,
      marginTop: 8,
      flexWrap: "wrap",
    }}
  >
    <div
      style={{
        flex: 1,
        minWidth: 120,
        background: "rgba(0,255,140,0.08)",
        border: "1px solid rgba(0,255,140,0.25)",
        borderRadius: 8,
        padding: "6px 10px",
        fontSize: 11,
        fontFamily: "Inter, sans-serif",
        color: "#00FF9F",
      }}
    >
      ✓ {doStr}
    </div>
    <div
      style={{
        flex: 1,
        minWidth: 120,
        background: "rgba(255,45,149,0.08)",
        border: "1px solid rgba(255,45,149,0.25)",
        borderRadius: 8,
        padding: "6px 10px",
        fontSize: 11,
        fontFamily: "Inter, sans-serif",
        color: "#FF2D95",
      }}
    >
      ✗ {dont}
    </div>
  </div>
);

// ─── VERSIONING ROW ───────────────────────────────────────────────────────────
const VersionRow: React.FC<{ label: string; color?: string }> = ({
  label,
  color,
}) => (
  <div
    style={{
      display: "inline-flex",
      alignItems: "center",
      background: color ?? THEME.glassBg,
      border: `1px solid ${color ? "rgba(255,255,255,0.15)" : THEME.glassBorder}`,
      borderRadius: 8,
      padding: "4px 12px",
      fontSize: 11,
      fontFamily: "Poppins, sans-serif",
      fontWeight: 700,
      color: color ?? THEME.textPrimary,
      letterSpacing: "0.04em",
      marginRight: 8,
    }}
  >
    {label}
  </div>
);

// ─── METAPHOR BADGE ──────────────────────────────────────────────────────────
const MetaphorBadge: React.FC<{ category: string; visual: string }> = ({
  category,
  visual,
}) => (
  <div
    style={{
      display: "inline-flex",
      alignItems: "center",
      gap: 8,
      background: "rgba(255,107,0,0.10)",
      border: "1px solid rgba(255,107,0,0.25)",
      borderRadius: 8,
      padding: "5px 12px",
      margin: "3px 4px 3px 0",
    }}
  >
    <span
      style={{
        fontSize: 10,
        fontFamily: "Poppins, sans-serif",
        fontWeight: 700,
        color: THEME.accentOrange,
        letterSpacing: "0.08em",
        textTransform: "uppercase",
      }}
    >
      {category}
    </span>
    <span style={{ fontSize: 14, color: THEME.textMuted }}>→</span>
    <span
      style={{
        fontSize: 11,
        fontFamily: "Inter, sans-serif",
        color: THEME.textPrimary,
        fontWeight: 500,
      }}
    >
      {visual}
    </span>
  </div>
);

// ─── MAIN STILL COMPONENT ─────────────────────────────────────────────────────
const ChronixelMotionSystem: React.FC = () => {
  return (
    <AbsoluteFill style={{ background: THEME.bg, fontFamily: "Inter, sans-serif" }}>
      <GridBg />

      {/* ── HEADER ── */}
      <div
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          right: 0,
          height: 90,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          borderBottom: `1px solid ${THEME.glassBorder}`,
          background: "rgba(10,10,15,0.80)",
          backdropFilter: "blur(8px)",
          WebkitBackdropFilter: "blur(8px)",
          zIndex: 10,
        }}
      >
        <div
          style={{
            fontSize: 13,
            fontFamily: "Poppins, sans-serif",
            fontWeight: 700,
            letterSpacing: "0.45em",
            color: THEME.accentOrange,
            textTransform: "uppercase",
            marginBottom: 4,
          }}
        >
          Creative Direction Framework
        </div>
        <div
          style={{
            fontSize: 30,
            fontFamily: "Poppins, sans-serif",
            fontWeight: 800,
            letterSpacing: "-0.02em",
            color: THEME.textPrimary,
            lineHeight: 1,
          }}
        >
          CHRONIXEL MOTION GRAPHICS SYSTEM
        </div>
        <div
          style={{
            fontSize: 11,
            fontFamily: "Inter, sans-serif",
            color: THEME.textMuted,
            marginTop: 4,
            letterSpacing: "0.06em",
          }}
        >
          Remotion Motion Design Agent · System Instructions v1.0
        </div>
      </div>

      {/* ── BODY: 6 CARDS IN 3×2 GRID ── */}
      <div
        style={{
          position: "absolute",
          top: 105,
          left: 20,
          right: 20,
          bottom: 20,
          display: "grid",
          gridTemplateColumns: "1fr 1fr 1fr",
          gridTemplateRows: "1fr 1fr",
          gap: 14,
        }}
      >
        {/* ─ CARD 1: Core Objective ─ */}
        <GlassCard>
          <SectionBadge label="01 · Core Objective" />
          <div
            style={{
              fontSize: 14,
              fontFamily: "Poppins, sans-serif",
              fontWeight: 700,
              letterSpacing: "-0.01em",
              color: THEME.textPrimary,
              lineHeight: 1.3,
              marginBottom: 8,
            }}
          >
            Act like a Creative Director, not a Caption Generator
          </div>
          <OrangeDivider />
          <BodyText>
            The <Keyword>script provides the meaning</Keyword>; your motion graphics
            provide the <Keyword>visual explanation</Keyword>. Show the concept rather
            than repeating words literally. Protect the meaning while freely improving
            the visual execution.
          </BodyText>
        </GlassCard>

        {/* ─ CARD 2: Typography ─ */}
        <GlassCard>
          <SectionBadge label="02 · Typography" color="rgba(0,242,254,0.12)" />
          <div
            style={{
              fontFamily: "Poppins, sans-serif",
              fontWeight: 800,
              letterSpacing: "-0.03em",
              color: THEME.textPrimary,
              lineHeight: 1.1,
              marginBottom: 6,
              fontSize: 22,
            }}
          >
            POPPINS EXTRA BOLD
          </div>
          <div
            style={{
              fontSize: 10,
              fontFamily: "Inter, sans-serif",
              color: THEME.textMuted,
              letterSpacing: "0.55em",
              marginBottom: 8,
              textTransform: "uppercase",
            }}
          >
            Tight · Premium · High-Impact
          </div>
          <OrangeDivider />
          <BodyText>
            <Keyword>Letter spacing</Keyword> must be very tight — letters almost
            touching. Headings feel <Keyword>bold, premium, tight</Keyword> and
            high-impact. Never wide-tracked body text.
          </BodyText>
        </GlassCard>

        {/* ─ CARD 3: Visual Communication ─ */}
        <GlassCard>
          <SectionBadge label="03 · Visual Language" color="rgba(0,255,140,0.12)" />
          <div
            style={{
              fontSize: 13,
              fontFamily: "Poppins, sans-serif",
              fontWeight: 700,
              color: THEME.textPrimary,
              marginBottom: 8,
              lineHeight: 1.3,
            }}
          >
            Visual Communication First · Words Second
          </div>
          <DoDont
            do="MESSY TIMELINE → CLEAN SYSTEM"
            dont="Script sentence on screen"
          />
          <BodyText style={{ marginTop: 8 }}>
            Use 1–4 word labels, UI tags, button labels. Avoid full sentences
            unless <Keyword>absolutely critical</Keyword>. Show the point, don't
            caption it.
          </BodyText>
        </GlassCard>

        {/* ─ CARD 4: Translation Metaphors ─ */}
        <GlassCard>
          <SectionBadge label="04 · Translation Metaphors" color="rgba(180,0,255,0.12)" />
          <div
            style={{
              display: "flex",
              flexWrap: "wrap",
              gap: 4,
              marginBottom: 8,
            }}
          >
            <MetaphorBadge category="Speed" visual="Progress bars · Fast cards" />
            <MetaphorBadge category="Confusion" visual="Scattered panels · Blur" />
            <MetaphorBadge category="Clarity" visual="Snap alignment · Clean glass" />
            <MetaphorBadge category="Growth" visual="Rising graphs · Level up" />
            <MetaphorBadge category="AI / Auto" visual="Glowing nodes · Clean flows" />
          </div>
          <OrangeDivider />
          <BodyText>
            Ask: <Keyword>"What is this line really saying visually?"</Keyword>{" "}
            Create a scene that represents the underlying idea. No cheesy robots —
            clean automation flows and glowing nodes.
          </BodyText>
        </GlassCard>

        {/* ─ CARD 5: Creative Unlock ─ */}
        <GlassCard>
          <SectionBadge label="05 · Creative Unlock" color="rgba(255,215,0,0.12)" />
          <div
            style={{
              fontSize: 12,
              fontFamily: "Inter, sans-serif",
              fontWeight: 600,
              color: THEME.accentOrange,
              letterSpacing: "0.04em",
              marginBottom: 6,
            }}
          >
            YOU HAVE FULL CREATIVE CONTROL
          </div>
          <BodyText>
            The script is your <Keyword>starting point, not your ceiling</Keyword>.
            Think beyond the literal. Add supporting motion, UI, 3D, symbols,
            rhythm. Remove text when the visual carries it alone.
          </BodyText>
          <div
            style={{
              marginTop: 10,
              display: "flex",
              gap: 6,
              flexWrap: "wrap",
            }}
          >
            {["UI Elements", "3D accents", "Metaphors", "Clean rhythm", "Zero clutter"].map(
              (t) => (
                <div
                  key={t}
                  style={{
                    background: "rgba(255,215,0,0.08)",
                    border: "1px solid rgba(255,215,0,0.20)",
                    borderRadius: 6,
                    padding: "2px 8px",
                    fontSize: 10,
                    fontFamily: "Poppins, sans-serif",
                    fontWeight: 600,
                    color: "#FFD700",
                  }}
                >
                  {t}
                </div>
              )
            )}
          </div>
        </GlassCard>

        {/* ─ CARD 6: Scene Versioning ─ */}
        <GlassCard>
          <SectionBadge label="06 · Scene Versioning" color="rgba(255,45,149,0.12)" />
          <div
            style={{
              fontSize: 12,
              fontFamily: "Inter, sans-serif",
              fontWeight: 600,
              color: THEME.textMuted,
              marginBottom: 8,
              letterSpacing: "0.02em",
            }}
          >
            Never Replace · Always Version
          </div>
          <div
            style={{ display: "flex", flexDirection: "column", gap: 5, marginBottom: 8 }}
          >
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <VersionRow label="Scene 2 V2" />
              <span
                style={{
                  fontSize: 11,
                  color: THEME.textSecondary,
                  fontFamily: "Inter, sans-serif",
                }}
              >
                The Workflow Problem
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <VersionRow label="Scene 2 V3" />
              <span
                style={{
                  fontSize: 11,
                  color: THEME.textSecondary,
                  fontFamily: "Inter, sans-serif",
                }}
              >
                The Workflow Problem
              </span>
            </div>
            <div style={{ display: "flex", alignItems: "center", gap: 6 }}>
              <VersionRow label="Scene 2 V4" />
              <span
                style={{
                  fontSize: 11,
                  color: THEME.textSecondary,
                  fontFamily: "Inter, sans-serif",
                }}
              >
                The Workflow Problem
              </span>
            </div>
          </div>
          <OrangeDivider />
          <BodyText>
            Use the <Keyword>latest version</Keyword> as the base for the next revision.
            Scene number stays the same — only version increases. Never edit in place.
          </BodyText>
        </GlassCard>
      </div>

      {/* ── FOOTER ── */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          left: 0,
          right: 0,
          height: 28,
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          padding: "0 24px",
          borderTop: `1px solid ${THEME.glassBorder}`,
          background: "rgba(10,10,15,0.60)",
        }}
      >
        <div
          style={{
            fontSize: 10,
            fontFamily: "Inter, sans-serif",
            color: THEME.textMuted,
            letterSpacing: "0.08em",
          }}
        >
          CHRONIXEL AESTHETIC · Dark BG + Grid · Orange Highlights · Glass UI · Off-White Text · Tight Tracking
        </div>
        <div
          style={{
            fontSize: 10,
            fontFamily: "Poppins, sans-serif",
            fontWeight: 700,
            color: THEME.accentOrange,
            letterSpacing: "0.12em",
          }}
        >
          ← SCRIPT PROVIDES MEANING · MOTION PROVIDES VISUAL EXPLANATION →
        </div>
      </div>
    </AbsoluteFill>
  );
};

export default ChronixelMotionSystem;
