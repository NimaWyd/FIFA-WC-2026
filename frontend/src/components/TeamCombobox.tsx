"use client";
import { useState } from "react";
import { Combobox, ComboboxButton, ComboboxInput, ComboboxOption, ComboboxOptions } from "@headlessui/react";
import { ChevronUpDownIcon, CheckIcon } from "@heroicons/react/20/solid";
import clsx from "clsx";
import type { TeamInfo } from "@/lib/types";

const CONF_COLORS: Record<string, string> = {
  UEFA: "bg-blue-700 text-blue-100",
  CONMEBOL: "bg-yellow-700 text-yellow-100",
  CONCACAF: "bg-red-700 text-red-100",
  CAF: "bg-green-700 text-green-100",
  AFC: "bg-orange-700 text-orange-100",
  OFC: "bg-purple-700 text-purple-100",
  UNKNOWN: "bg-slate-700 text-slate-100",
};

interface Props {
  value: TeamInfo | null;
  onChange: (t: TeamInfo | null) => void;
  label: string;
  placeholder?: string;
  teams: TeamInfo[];
  disabledTeam?: TeamInfo | null;
}

export default function TeamCombobox({ value, onChange, label, placeholder = "Search team…", teams, disabledTeam }: Props) {
  const [query, setQuery] = useState("");

  const filtered = query === ""
    ? teams
    : teams.filter((t) => {
        const q = query.toLowerCase();
        return (
          t.display_name.toLowerCase().includes(q) ||
          t.canonical_name.toLowerCase().includes(q) ||
          t.aliases.some((a) => a.toLowerCase().includes(q))
        );
      });

  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-semibold text-slate-300 uppercase tracking-wider">{label}</label>
      <Combobox value={value} onChange={onChange}>
        <div className="relative">
          <ComboboxInput
            className="w-full rounded-lg bg-navy-700 border border-slate-600 text-white px-4 py-3 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-gold-500 placeholder-slate-500"
            displayValue={(t: TeamInfo | null) => t?.display_name ?? ""}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={placeholder}
          />
          <ComboboxButton className="absolute inset-y-0 right-0 flex items-center pr-3">
            <ChevronUpDownIcon className="h-5 w-5 text-slate-400" />
          </ComboboxButton>
        </div>
        <ComboboxOptions className="absolute z-50 mt-1 max-h-64 w-full overflow-auto rounded-lg bg-navy-800 border border-slate-600 shadow-xl text-sm">
          {filtered.length === 0 ? (
            <div className="px-4 py-3 text-slate-400">No teams found</div>
          ) : (
            filtered.map((team) => (
              <ComboboxOption
                key={team.canonical_name}
                value={team}
                disabled={disabledTeam?.canonical_name === team.canonical_name}
                className={({ active, disabled }) =>
                  clsx(
                    "flex items-center gap-3 px-4 py-2.5 cursor-pointer",
                    active && !disabled && "bg-navy-600",
                    disabled && "opacity-40 cursor-not-allowed"
                  )
                }
              >
                {({ selected }) => (
                  <>
                    <span className={clsx("text-xs px-1.5 py-0.5 rounded font-bold shrink-0", CONF_COLORS[team.confederation])}>
                      {team.confederation}
                    </span>
                    <span className="flex-1 text-white">{team.display_name}</span>
                    {team.fifa_rank && (
                      <span className="text-xs text-slate-400">#{team.fifa_rank}</span>
                    )}
                    {selected && <CheckIcon className="h-4 w-4 text-gold-400 shrink-0" />}
                  </>
                )}
              </ComboboxOption>
            ))
          )}
        </ComboboxOptions>
      </Combobox>
    </div>
  );
}
