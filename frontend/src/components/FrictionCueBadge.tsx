import React from "react";

interface FrictionCueBadgeProps {
  cue: {
    cue_type: "weather_warning" | "road_bottleneck" | "water_scarcity" | "resting";
    message: string;
    severity: "low" | "medium" | "high";
  };
  severityColor?: string;
}

const severityStyles: Record<"low" | "medium" | "high", { background: string; color: string }> = {
  low: { background: "var(--quiet-bg)", color: "var(--quiet-text)" },
  medium: { background: "var(--moderate-bg)", color: "var(--moderate-text)" },
  high: { background: "var(--busy-bg)", color: "var(--busy-text)" },
};

export function FrictionCueBadge({ cue, severityColor }: FrictionCueBadgeProps) {
  const style = severityStyles[cue.severity] || severityStyles.medium;

  return (
    <div
      style={{
        backgroundColor: style.background,
        color: style.color,
        padding: "8px 12px",
        borderRadius: "999px",
        fontSize: "11px",
        fontWeight: 600,
        marginTop: "8px",
        display: "inline-flex",
        alignItems: "center",
        gap: "6px",
      }}
    >
      <span style={{ fontSize: "12px" }}>
        {cue.cue_type.replace(/_/g, " ")}
      </span>
      <span>{cue.message}</span>
    </div>
  );
}