import type { CrowdEstimate } from "../types/api";

const crowdLevelClasses: Record<CrowdEstimate["level"], string> = {
  Quiet: "crowd-tone--quiet",
  Moderate: "crowd-tone--moderate",
  Busy: "crowd-tone--busy",
  "Very busy": "crowd-tone--verybusy",
};

export function getCrowdLevelClass(level: CrowdEstimate["level"]): string {
  return crowdLevelClasses[level];
}
