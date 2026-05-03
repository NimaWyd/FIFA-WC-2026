"use client";
import { useState } from "react";
import {
  Combobox,
  ComboboxButton,
  ComboboxInput,
  ComboboxOption,
  ComboboxOptions,
} from "@headlessui/react";
import { ChevronUpDownIcon, CheckIcon } from "@heroicons/react/20/solid";
import type { TeamInfo } from "@/lib/types";
import FlagIcon from "@/components/FlagIcon";

const CONF_COLORS: Record<string, string> = {
  UEFA: "bg-blue-800 text-blue-200",
  CONMEBOL: "bg-yellow-800 text-yellow-200",
  CONCACAF: "bg-red-800 text-red-200",
  CAF: "bg-green-800 text-green-200",
  AFC: "bg-orange-800 text-orange-200",
  OFC: "bg-purple-800 text-purple-200",
  UNKNOWN: "bg-slate-700 text-slate-300",
};

interface Props {
  value: TeamInfo | null;
  onChange: (t: TeamInfo | null) => void;
  label: string;
  placeholder?: string;
  teams: TeamInfo[];
  disabledTeam?: TeamInfo | null;
}

export default function TeamCombobox({
  value,
  onChange,
  label,
  placeholder = "Search team…",
  teams,
  disabledTeam,
}: Props) {
  const [query, setQuery] = useState("");
  const inputId = `combobox-${label.toLowerCase().replace(/\s+/g, "-")}`;

  const filtered =
    query === ""
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
      <label htmlFor={inputId} className="text-sm font-semibold text-slate-300 uppercase tracking-wider">
        {label}
      </label>
      <Combobox value={value} onChange={onChange}>
        <div className="relative">
          <ComboboxInput
            id={inputId}
            className={`w-full rounded-lg bg-[#111d3c] border border-slate-600 text-white ${value ? "pl-10" : "pl-4"} py-3 pr-10 text-sm focus:outline-none focus:ring-2 focus:ring-[#d4af37] placeholder-slate-500`}
            displayValue={(t: TeamInfo | null) => t?.display_name ?? ""}
            onChange={(e) => setQuery(e.target.value)}
            placeholder={placeholder}
            aria-label={label}
          />
          {/* Show flag of selected team inside input */}
          {value && (
            <span className="absolute inset-y-0 left-3 flex items-center pointer-events-none">
              <FlagIcon team={value.display_name} className="w-5 h-4 mr-1 rounded-sm" />
            </span>
          )}
          <ComboboxButton className="absolute inset-y-0 right-0 flex items-center pr-3">
            <ChevronUpDownIcon className="h-5 w-5 text-slate-400" />
          </ComboboxButton>

          <ComboboxOptions className="absolute z-[100] mt-1 max-h-64 w-full overflow-y-auto rounded-lg bg-[#0d1428] border border-slate-700 shadow-2xl text-sm [--anchor-gap:4px]">
            {filtered.length === 0 ? (
              <div className="px-4 py-3 text-slate-400">No teams found</div>
            ) : (
              filtered.map((team) => {
                const isDisabled = disabledTeam?.canonical_name === team.canonical_name;
                return (
                  <ComboboxOption
                    key={team.canonical_name}
                    value={team}
                    disabled={isDisabled}
                    className="flex items-center gap-3 px-4 py-2.5 cursor-pointer data-[active]:bg-[#111d3c] data-[disabled]:opacity-40 data-[disabled]:cursor-not-allowed"
                  >
                    <FlagIcon team={team.display_name} className="w-5 h-4 rounded-sm shrink-0" />
                    <span className="flex-1 text-white">{team.display_name}</span>
                    <span
                      className={`text-xs px-1.5 py-0.5 rounded font-bold shrink-0 ${CONF_COLORS[team.confederation] ?? CONF_COLORS.UNKNOWN}`}
                    >
                      {team.confederation}
                    </span>
                    {team.fifa_rank && (
                      <span className="text-xs text-slate-400 w-8 text-right shrink-0">
                        #{team.fifa_rank}
                      </span>
                    )}
                    <CheckIcon className="h-4 w-4 text-[#d4af37] shrink-0 invisible group-data-[selected]:visible" />
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
