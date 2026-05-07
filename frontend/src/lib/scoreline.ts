import type { Scoreline } from "./types";

export function selectScoreline(
  dominant: "H" | "A" | "D",
  topScorelinesArg: Scoreline[],
  xgHome: number,
  xgAway: number
): [number, number] {
  const match = topScorelinesArg.find(({ scoreline }) => {
    const [h, a] = scoreline.split("-").map(Number);
    if (h + a > 6) return false;
    return dominant === "H" ? h > a : dominant === "A" ? a > h : h === a;
  });
  if (match) {
    const [h, a] = match.scoreline.split("-").map(Number);
    return [h, a];
  }
  const h = Math.min(3, Math.round(xgHome));
  const a = Math.min(3, Math.round(xgAway));
  if (dominant === "H") return h > a ? [h, a] : [a + 1, a];
  if (dominant === "A") return a > h ? [h, a] : [h, h + 1];
  const d = Math.min(h, a);
  return [d, d];
}
