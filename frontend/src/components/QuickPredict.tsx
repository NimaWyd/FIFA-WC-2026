"use client";

import { useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import Link from "next/link";
import {
  Combobox,
  ComboboxInput,
  ComboboxButton,
  ComboboxOptions,
  ComboboxOption,
} from "@headlessui/react";
import { ChevronUpDownIcon } from "@heroicons/react/20/solid";
import { useTeams } from "@/hooks/useTeams";
import { usePredict } from "@/hooks/usePredict";
import FlagIcon from "@/components/FlagIcon";
import type { TeamInfo, PredictResponse } from "@/lib/types";
import { WC2026_TEAMS } from "@/lib/wc2026Teams";

/* ── Team picker (hero-themed combobox) ─────────────────────── */
function TeamPicker({
  value,
  onChange,
  label,
  placeholder,
  teams,
  disabledTeam,
}: {
  value: TeamInfo | null;
  onChange: (t: TeamInfo | null) => void;
  label: string;
  placeholder: string;
  teams: TeamInfo[];
  disabledTeam: TeamInfo | null;
}) {
  const [query, setQuery] = useState("");
  const filtered =
    query === ""
      ? teams
      : teams.filter(
          (t) =>
            t.display_name.toLowerCase().includes(query.toLowerCase()) ||
            t.canonical_name.toLowerCase().includes(query.toLowerCase()),
        );

  return (
    <div className="flex flex-col gap-1.5">
      <span className="font-jb text-[10px] tracking-[0.14em] uppercase text-[rgba(240,236,226,0.35)]">
        {label}
      </span>
      <Combobox value={value} onChange={onChange}>
        <div className="relative">
          <div className="flex items-center bg-white/[0.06] border border-white/[0.10] rounded-[4px] focus-within:border-pitch-400/40 transition-colors">
            {value && (
              <span className="pl-3.5 flex-shrink-0 pointer-events-none">
                <FlagIcon team={value.display_name} className="w-6 h-[18px] rounded-[2px]" />
              </span>
            )}
            <ComboboxInput
              className={`flex-1 bg-transparent text-[#f0ece2] font-semibold text-[15px] py-3.5 ${value ? "pl-2.5" : "pl-3.5"} pr-2 placeholder-[rgba(240,236,226,0.28)] focus:outline-none min-w-0 truncate`}
              displayValue={(t: TeamInfo | null) => t?.display_name ?? ""}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={placeholder}
            />
            <ComboboxButton className="pr-3 flex-shrink-0">
              <ChevronUpDownIcon className="w-4 h-4 text-[rgba(240,236,226,0.25)]" />
            </ComboboxButton>
          </div>

          <ComboboxOptions className="absolute z-50 top-full mt-1.5 w-full max-h-56 overflow-y-auto bg-navy-800 border border-white/[0.12] rounded-[4px] shadow-2xl [scrollbar-width:thin]">
            {filtered.length === 0 ? (
              <div className="px-4 py-3 font-jb text-[rgba(240,236,226,0.3)] text-[13px]">
                No teams found
              </div>
            ) : (
              filtered.map((team) => {
                const disabled = disabledTeam?.canonical_name === team.canonical_name;
                return (
                  <ComboboxOption
                    key={team.canonical_name}
                    value={team}
                    disabled={disabled}
                    className="flex items-center gap-3 px-4 py-2.5 cursor-pointer select-none data-[active]:bg-white/[0.05] data-[disabled]:opacity-25 data-[disabled]:cursor-not-allowed"
                  >
                    <FlagIcon
                      team={team.display_name}
                      className="w-5 h-[15px] rounded-[2px] flex-shrink-0"
                    />
                    <span className="text-[#f0ece2] text-[14px]">{team.display_name}</span>
                    {team.fifa_rank && (
                      <span className="ml-auto font-jb text-[rgba(240,236,226,0.28)] text-[11px] flex-shrink-0 tabular-nums">
                        #{team.fifa_rank}
                      </span>
                    )}
                  </ComboboxOption>
                );
              })
            )}
          </ComboboxOptions>
        </div>
      </Combobox>
    </div>
  );
}

/* ── Result panel ───────────────────────────────────────────── */
function ResultPanel({
  result,
  onReset,
}: {
  result: PredictResponse;
  onReset: () => void;
}) {
  const { probabilities: p, top_scorelines } = result;
  const best = Math.max(p.home_win, p.draw, p.away_win);
  const homeWins = p.home_win === best;
  const awayWins = !homeWins && p.away_win === best;
  const isDraw = !homeWins && !awayWins;
  const topScore = top_scorelines[0];

  const homeDisplay = result.home_team === "United States" ? "USA" : result.home_team;
  const awayDisplay = result.away_team === "United States" ? "USA" : result.away_team;

  const predictLink = `/predict?home=${encodeURIComponent(result.home_team)}&away=${encodeURIComponent(result.away_team)}&date=2026-06-11&stage=Group+Stage`;

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -8 }}
      transition={{ duration: 0.5, ease: [0.22, 1, 0.36, 1] }}
      className="mt-8 pt-8 border-t border-white/[0.07]"
    >
      {/* Match header */}
      <div className="flex items-center gap-3 mb-6 flex-wrap">
        <FlagIcon team={result.home_team} className="w-7 h-5 rounded-[2px]" />
        <span className="font-anton text-[18px] leading-none">{homeDisplay}</span>
        <span className="font-jb text-[10px] text-[rgba(240,236,226,0.22)] tracking-[0.2em] mx-0.5">
          VS
        </span>
        <FlagIcon team={result.away_team} className="w-7 h-5 rounded-[2px]" />
        <span className="font-anton text-[18px] leading-none">{awayDisplay}</span>
        <button
          onClick={onReset}
          className="ml-auto font-jb text-[11px] text-[rgba(240,236,226,0.25)] hover:text-[rgba(240,236,226,0.55)] transition-colors"
        >
          ✕ reset
        </button>
      </div>

      {/* 3 outcome cards */}
      <div className="grid grid-cols-3 gap-2.5 mb-4">
        {/* Home win */}
        <div
          className={`rounded-[4px] px-4 py-4 md:px-5 md:py-5 ${
            homeWins
              ? "bg-pitch-400/[0.09] border border-pitch-400/25"
              : "bg-white/[0.03] border border-white/[0.06]"
          }`}
        >
          <div className="font-jb text-[9px] uppercase tracking-[0.14em] text-[rgba(240,236,226,0.35)] mb-2 truncate">
            {homeDisplay}
          </div>
          <div
            className={`font-anton text-[38px] md:text-[46px] leading-none tabular-nums ${
              homeWins ? "text-pitch-400" : "text-[rgba(240,236,226,0.52)]"
            }`}
          >
            {(p.home_win * 100).toFixed(0)}%
          </div>
          {homeWins && (
            <div className="font-jb text-[9px] uppercase tracking-[0.1em] text-pitch-400/60 mt-2">
              Favoured
            </div>
          )}
        </div>

        {/* Draw */}
        <div
          className={`rounded-[4px] px-4 py-4 md:px-5 md:py-5 flex flex-col items-center text-center ${
            isDraw
              ? "bg-white/[0.06] border border-white/[0.14]"
              : "bg-white/[0.03] border border-white/[0.06]"
          }`}
        >
          <div className="font-jb text-[9px] uppercase tracking-[0.14em] text-[rgba(240,236,226,0.35)] mb-2">
            Draw
          </div>
          <div
            className={`font-anton text-[38px] md:text-[46px] leading-none tabular-nums ${
              isDraw ? "text-[#f0ece2]" : "text-[rgba(240,236,226,0.42)]"
            }`}
          >
            {(p.draw * 100).toFixed(0)}%
          </div>
          {isDraw && (
            <div className="font-jb text-[9px] uppercase tracking-[0.1em] text-[rgba(240,236,226,0.45)] mt-2">
              Likely
            </div>
          )}
        </div>

        {/* Away win */}
        <div
          className={`rounded-[4px] px-4 py-4 md:px-5 md:py-5 text-right ${
            awayWins
              ? "bg-[rgba(245,200,66,0.07)] border border-[rgba(245,200,66,0.20)]"
              : "bg-white/[0.03] border border-white/[0.06]"
          }`}
        >
          <div className="font-jb text-[9px] uppercase tracking-[0.14em] text-[rgba(240,236,226,0.35)] mb-2 truncate">
            {awayDisplay}
          </div>
          <div
            className={`font-anton text-[38px] md:text-[46px] leading-none tabular-nums ${
              awayWins ? "text-gold-500" : "text-[rgba(240,236,226,0.52)]"
            }`}
          >
            {(p.away_win * 100).toFixed(0)}%
          </div>
          {awayWins && (
            <div className="font-jb text-[9px] uppercase tracking-[0.1em] text-gold-500/60 mt-2">
              Favoured
            </div>
          )}
        </div>
      </div>

      {/* Segmented probability bar */}
      <div className="h-[3px] flex rounded-full overflow-hidden mb-5">
        <motion.div
          className="h-full bg-pitch-400"
          initial={{ width: 0 }}
          animate={{ width: `${(p.home_win * 100).toFixed(2)}%` }}
          transition={{ duration: 0.8, ease: "easeOut" }}
        />
        <motion.div
          className="h-full bg-white/20"
          initial={{ width: 0 }}
          animate={{ width: `${(p.draw * 100).toFixed(2)}%` }}
          transition={{ duration: 0.8, delay: 0.06, ease: "easeOut" }}
        />
        <motion.div
          className="h-full bg-gold-500/50"
          initial={{ width: 0 }}
          animate={{ width: `${(p.away_win * 100).toFixed(2)}%` }}
          transition={{ duration: 0.8, delay: 0.12, ease: "easeOut" }}
        />
      </div>

      {/* Footer: top scoreline + full analysis link */}
      <div className="flex items-center gap-4 flex-wrap">
        {topScore && (
          <div className="flex items-center gap-3">
            <span className="font-jb text-[10px] uppercase tracking-[0.12em] text-[rgba(240,236,226,0.28)]">
              Top scoreline
            </span>
            <span className="font-anton text-[22px] leading-none">{topScore.scoreline}</span>
            <span className="font-jb text-[11px] text-[rgba(240,236,226,0.3)]">
              {(topScore.probability * 100).toFixed(1)}%
            </span>
          </div>
        )}
        <Link
          href={predictLink}
          className="ml-auto font-anton text-[13px] tracking-[0.08em] uppercase text-[rgba(240,236,226,0.38)] hover:text-pitch-400 transition-colors"
        >
          Full analysis →
        </Link>
      </div>
    </motion.div>
  );
}

/* ── Main export ────────────────────────────────────────────── */
export default function QuickPredict() {
  const { teams: allTeams, loading: teamsLoading } = useTeams();
  const { predict, result, loading, error, reset } = usePredict();
  const [home, setHome] = useState<TeamInfo | null>(null);
  const [away, setAway] = useState<TeamInfo | null>(null);

  const teams = allTeams.filter((t) => WC2026_TEAMS.has(t.canonical_name));

  function handlePredict() {
    if (!home || !away) return;
    predict({
      home_team: home.canonical_name,
      away_team: away.canonical_name,
      match_date: "2026-06-11",
      competition: "FIFA World Cup",
      neutral: true,
      tournament_stage: "Group Stage",
    });
  }

  return (
    <section className="relative bg-navy-900 border-t border-white/[0.06]">
      <div
        aria-hidden
        className="pointer-events-none absolute inset-0"
        style={{
          background:
            "radial-gradient(ellipse at 70% 50%, rgba(34,160,82,0.06) 0%, transparent 55%)",
        }}
      />

      <div className="relative max-w-7xl mx-auto px-8 md:px-14 py-16 md:py-20">
        <p className="font-jb text-[11px] tracking-[0.18em] uppercase text-pitch-400 mb-6">
          ◆ Quick Predict
        </p>

        {/* Form row */}
        <div className="flex flex-col md:flex-row gap-3 md:gap-4 md:items-end">
          {teamsLoading ? (
            <div className="flex-1 h-[62px] rounded-[4px] bg-white/[0.04] animate-pulse" />
          ) : (
            <div className="flex-1">
              <TeamPicker
                label="Home"
                placeholder="Search home team…"
                value={home}
                onChange={(t) => { setHome(t); reset(); }}
                teams={teams}
                disabledTeam={away}
              />
            </div>
          )}

          <div className="hidden md:flex items-center justify-center pb-[14px] px-1">
            <span className="font-anton text-[16px] text-[rgba(240,236,226,0.18)] tracking-[0.22em]">
              VS
            </span>
          </div>

          {teamsLoading ? (
            <div className="flex-1 h-[62px] rounded-[4px] bg-white/[0.04] animate-pulse" />
          ) : (
            <div className="flex-1">
              <TeamPicker
                label="Away"
                placeholder="Search away team…"
                value={away}
                onChange={(t) => { setAway(t); reset(); }}
                teams={teams}
                disabledTeam={home}
              />
            </div>
          )}

          <button
            onClick={handlePredict}
            disabled={!home || !away || loading}
            className="font-anton text-[15px] tracking-[0.09em] px-8 py-[15px] bg-pitch-400 text-navy-900 rounded-[4px] hover:bg-pitch-300 disabled:opacity-35 disabled:cursor-not-allowed transition-colors whitespace-nowrap flex-shrink-0"
          >
            {loading ? "PREDICTING…" : "PREDICT →"}
          </button>
        </div>

        {error && (
          <p className="mt-4 font-jb text-[12px] text-red-400/80 tracking-wide">
            {error === "Failed to fetch"
              ? "Cannot connect to backend — make sure the API server is running."
              : error}
          </p>
        )}

        <AnimatePresence mode="wait">
          {result && (
            <ResultPanel
              key={`${result.home_team}-${result.away_team}`}
              result={result}
              onReset={() => {
                reset();
                setHome(null);
                setAway(null);
              }}
            />
          )}
        </AnimatePresence>
      </div>
    </section>
  );
}
