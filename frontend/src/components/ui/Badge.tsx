import type { HTMLAttributes, ReactNode } from "react";
import type { CrowdEstimate } from "../../types/api";
import { getCrowdLevelClass } from "../../utils/theme";

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  children: ReactNode;
  level?: CrowdEstimate["level"];
}

export function Badge({ children, className = "", level, ...props }: BadgeProps) {
  const toneClass = level ? ` ${getCrowdLevelClass(level)}` : "";

  return (
    <span
      className={`ui-badge${toneClass}${className ? ` ${className}` : ""}`}
      {...props}
    >
      {children}
    </span>
  );
}
