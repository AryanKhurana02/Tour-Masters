import { motion, useReducedMotion } from "framer-motion";
import type { CrowdEstimate } from "../types/api";

const foregroundByLevel: Record<CrowdEstimate["level"], string> = {
  Quiet: "var(--quiet-fg)",
  Moderate: "var(--moderate-fg)",
  Busy: "var(--busy-fg)",
  "Very busy": "var(--very-busy-fg)",
};

export function CrowdDial({
  crowd,
  animate = true,
}: {
  crowd: CrowdEstimate;
  animate?: boolean;
}) {
  const reducedMotion = useReducedMotion();
  const radius = 44;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference * (1 - crowd.score / 100);

  return (
    <div className="crowd-dial" role="img" aria-label={`Estimated crowd level: ${crowd.score} out of 100, ${crowd.level}`}>
      <svg viewBox="0 0 112 112" aria-hidden="true">
        <circle className="dial-track" cx="56" cy="56" r={radius} />
        <motion.circle
          className="dial-value"
          cx="56"
          cy="56"
          r={radius}
          style={{ stroke: foregroundByLevel[crowd.level] }}
          initial={animate && !reducedMotion ? { strokeDashoffset: circumference } : false}
          animate={{ strokeDashoffset: offset }}
          transition={{ duration: animate && !reducedMotion ? 0.9 : 0, ease: "easeOut" }}
        />
      </svg>
      <span className="dial-copy">
        <strong>{crowd.score}</strong>
        <span>{crowd.level}</span>
      </span>
    </div>
  );
}
