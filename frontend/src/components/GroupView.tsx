"use client";
import { useState } from "react";
import { ArrowLeftIcon, ChevronRightIcon } from "@heroicons/react/24/solid";
import { WCGroup, WCMatch } from "@/lib/wc2026Groups";
import FlagIcon from "@/components/FlagIcon";
import GroupStandings, { Standing } from "@/components/GroupStandings";
import { predict } from "@/lib/api";

interface Props {
  group: WCGroup;
  onBack: () => void;
  onPredict: (match: WCMatch) => void;
}

function formatDate(iso: string) {
  const d = new Date(iso + "T12:00:00");
  return d.toLocaleDateString("en-US", { month: "short", day: "numeric" });
}

const MATCHDAY_LABELS = ["MD 1", "MD 1", "MD 2", "MD 2", "MD 3", "MD 3"];

function parseScoreline(s: string): [number, number] {
  const [h, a] = s.split("-").map(Number);
  return [h ?? 0, a ?? 0];
}

function buildStandings(
  teams: string[],
  results: Array<{ match: WCMatch; homeGoals: number; awayGoals: number }>
): Standing[] {
  const map: Record<string, Standing> = {};
  for (const t of teams) {
    map[t] = { team: t, played: 0, won: 0, drawn: 0, lost: 0, gf: 0, ga: 0, gd: 0, points: 0 };
  }
  for (const { match, homeGoals, awayGoals } of results) {
    const h = map[match.home];
    const a = map[match.away];
    if (!h || !a) continue;
    h.played++;
    a.played++;
    h.gf += homeGoals;
    h.ga += awayGoals;
    a.gf += awayGoals;
    a.ga += homeGoals;
    if (homeGoals > awayGoals) {
      h.won++; h.points += 3; a.lost++;
    } else if (homeGoals === awayGoals) {
      h.drawn++; h.points += 1; a.drawn++; a.points += 1;
    } else {
      a.won++; a.points += 3; h.lost++;
    }
    h.gd = h.gf - h.ga;
    a.gd = a.gf - a.ga;
  }
  return Object.values(map);
}

export default function GroupView({ group, onBack, onPredict }: Props) {
  const [standings, setStandings] = useState<Standing[] | null>(null);
  const [predicting, setPredicting] = useState(false);
  const [progress, setProgress] = useState(0);
  const [predError, setPredError] = useState<string | null>(null);

  async function handlePredictAll() {
    setPredicting(true);
    setProgress(0);
    setPredError(null);
    setStandings(null);

    const results: Array<{ match: WCMatch; homeGoals: number; awayGoals: number }> = [];

    for (const match of group.matches) {
      try {
        const res = await predict({
          home_team: match.home,
          away_team: match.away,
          match_date: match.date,
          competition: "FIFA World Cup",
          neutral: true,
          tournament_stage: "Group Stage",
        });

        const p = res.probabilities;
        const dominant =
          p.home_win >= p.draw && p.home_win >= p.away_win ? "H" :
          p.away_win >= p.draw && p.away_win >= p.home_win ? "A" : "D";

        let homeGoals: number;
        let awayGoals: number;

        if (res.top_scorelines.length > 0) {
          // Pick the best scoreline that matches the dominant outcome
          const matching = res.top_scorelines.find((s) => {
            const [hg, ag] = parseScoreline(s.scoreline);
            if (dominant === "H") return hg > ag;
            if (dominant === "A") return ag > hg;
            return hg === ag;
          });
          if (matching) {
            [homeGoals, awayGoals] = parseScoreline(matching.scoreline);
          } else {
            // No scoreline in top-5 matches dominant outcome — use default
            if (dominant === "H") { homeGoals = 1; awayGoals = 0; }
            else if (dominant === "A") { homeGoals = 0; awayGoals = 1; }
            else { homeGoals = 1; awayGoals = 1; }
          }
        } else if (res.expected_goals) {
          homeGoals = Math.round(res.expected_goals.home);
          awayGoals = Math.round(res.expected_goals.away);
          if (dominant === "H" && homeGoals <= awayGoals) homeGoals = awayGoals + 1;
          if (dominant === "A" && awayGoals <= homeGoals) awayGoals = homeGoals + 1;
          if (dominant === "D") homeGoals = awayGoals = Math.round((homeGoals + awayGoals) / 2);
        } else {
          if (dominant === "H") { homeGoals = 1; awayGoals = 0; }
          else if (dominant === "A") { homeGoals = 0; awayGoals = 1; }
          else { homeGoals = 1; awayGoals = 1; }
        }

        results.push({ match, homeGoals, awayGoals });
        setProgress((prev) => prev + 1);
      } catch {
        setPredError("Prediction failed — is the backend running?");
        setPredicting(false);
        return;
      }
    }

    setStandings(buildStandings(group.teams, results));
    setPredicting(false);
  }

  return (
    <div className="flex flex-col gap-4">
      {/* Header */}
      <div className="flex items-center gap-3">
        <button
          onClick={onBack}
          className="p-1.5 rounded-lg bg-[#0d1428] border border-slate-800 text-slate-400 hover:text-white hover:border-slate-600 transition-colors"
        >
          <ArrowLeftIcon className="h-4 w-4" />
        </button>
        <div className="flex-1">
          <h2 className="text-lg font-bold text-white">Group {group.id}</h2>
          <p className="text-xs text-slate-500">{group.teams.join(" · ")}</p>
        </div>
        <button
          onClick={handlePredictAll}
          disabled={predicting}
          className="flex items-center gap-2 px-4 py-2 rounded-xl bg-[#d4af37] text-[#0a0e1a] text-sm font-bold hover:bg-[#e8c84a] transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {predicting ? (
            <>
              <span className="inline-block w-3 h-3 border-2 border-[#0a0e1a]/40 border-t-[#0a0e1a] rounded-full animate-spin" />
              {progress}/6
            </>
          ) : (
            "Predict All"
          )}
        </button>
      </div>

      {/* Error */}
      {predError && (
        <div className="bg-red-950 border border-red-800 rounded-xl px-4 py-3 text-red-300 text-sm">
          {predError}
        </div>
      )}

      {/* Standings */}
      {standings && <GroupStandings standings={standings} groupId={group.id} />}

      {/* Teams strip */}
      <div className="bg-[#0d1428] border border-slate-800 rounded-xl p-4">
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
          {group.teams.map((team) => (
            <div key={team} className="flex flex-col items-center gap-1.5">
              <FlagIcon team={team} className="w-10 h-7 rounded" />
              <span className="text-xs font-medium text-slate-300 text-center leading-tight">
                {team === "United States" ? "USA" : team}
              </span>
              {["Mexico", "United States", "Canada"].includes(team) && (
                <span className="text-[10px] text-[#d4af37]">Host</span>
              )}
            </div>
          ))}
        </div>
      </div>

      {/* Match cards */}
      <div className="flex flex-col gap-2">
        <h3 className="text-sm font-semibold text-slate-400 uppercase tracking-wider">Fixtures</h3>
        {group.matches.map((match, idx) => (
          <div
            key={idx}
            className="bg-[#0d1428] border border-slate-800 rounded-xl p-4 flex items-center gap-3"
          >
            <div className="hidden sm:block w-16 flex-shrink-0">
              <span className="text-[10px] text-slate-500 uppercase tracking-wider">
                {MATCHDAY_LABELS[idx]}
              </span>
              <div className="text-xs text-slate-400 mt-0.5">{formatDate(match.date)}</div>
              <div className="text-[10px] text-slate-600 mt-0.5 truncate">{match.venue}</div>
            </div>

            <div className="flex-1 flex items-center justify-between gap-2">
              <div className="flex items-center gap-2 flex-1">
                <FlagIcon team={match.home} className="w-7 h-5 rounded-sm flex-shrink-0" />
                <span className="text-sm font-semibold text-white truncate">
                  {match.home === "United States" ? "USA" : match.home}
                </span>
              </div>

              <div className="flex flex-col items-center gap-0.5 flex-shrink-0 px-2">
                <span className="text-xs font-bold text-slate-500">VS</span>
                <span className="sm:hidden text-[10px] text-slate-600">{formatDate(match.date)}</span>
              </div>

              <div className="flex items-center gap-2 flex-1 justify-end">
                <span className="text-sm font-semibold text-white truncate text-right">
                  {match.away === "United States" ? "USA" : match.away}
                </span>
                <FlagIcon team={match.away} className="w-7 h-5 rounded-sm flex-shrink-0" />
              </div>
            </div>

            <button
              onClick={() => onPredict(match)}
              className="flex-shrink-0 flex items-center gap-1 px-3 py-1.5 rounded-lg bg-[#d4af37]/10 border border-[#d4af37]/30 text-[#d4af37] text-xs font-semibold hover:bg-[#d4af37]/20 hover:border-[#d4af37]/60 transition-all"
            >
              Predict
              <ChevronRightIcon className="h-3 w-3" />
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
