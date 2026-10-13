import { motion, useReducedMotion } from "framer-motion";
import type { CrowdEstimate } from "../types/api";
import { Badge } from "./ui/Badge";
import { getCrowdLevelClass } from "../utils/theme";

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
  const score = Math.max(0, Math.min(100, crowd.score));
  const offset = circumference * (1 - score / 100);
  const toneClass = getCrowdLevelClass(crowd.level);

  return (
    <div className={`crowd-dial ${toneClass}`} role="img" aria-label={`Estimated crowd level: ${crowd.score} out of 100, ${crowd.level}`}>
      <svg viewBox="0 0 112 112" aria-hidden="true">
        <circle className="dial-track" cx="56" cy="56" r={radius} />
        <motion.circle
          className="dial-value"
          cx="56"
          cy="56"
          r={radius}
          strokeDashoffset={offset}
          initial={animate && !reducedMotion ? { opacity: 0 } : false}
          animate={{ opacity: 1 }}
          transition={{ duration: animate && !reducedMotion ? 0.2 : 0 }}
        />
      </svg>
      <span className="dial-copy">
        <strong>{crowd.score}</strong>
        <span>{crowd.level}</span>
        <Badge className="crowd-estimated">Estimated</Badge>
      </span>
    </div>
  );
}
