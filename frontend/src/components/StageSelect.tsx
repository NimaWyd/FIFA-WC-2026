"use client";
import { Listbox, ListboxButton, ListboxOption, ListboxOptions } from "@headlessui/react";
import { ChevronUpDownIcon, CheckIcon } from "@heroicons/react/20/solid";
import clsx from "clsx";

const STAGES = ["Group Stage", "Round of 16", "Quarter-Final", "Semi-Final", "Final"];

interface Props {
  value: string;
  onChange: (s: string) => void;
}

export default function StageSelect({ value, onChange }: Props) {
  return (
    <div className="flex flex-col gap-1">
      <label className="text-sm font-semibold text-slate-300 uppercase tracking-wider">Stage</label>
      <Listbox value={value} onChange={onChange}>
        <div className="relative">
          <ListboxButton className="w-full rounded-lg bg-navy-700 border border-slate-600 text-white px-4 py-3 pr-10 text-sm text-left focus:outline-none focus:ring-2 focus:ring-gold-500">
            {value}
            <span className="absolute inset-y-0 right-0 flex items-center pr-3">
              <ChevronUpDownIcon className="h-5 w-5 text-slate-400" />
            </span>
          </ListboxButton>
          <ListboxOptions className="absolute z-50 mt-1 w-full rounded-lg bg-navy-800 border border-slate-600 shadow-xl text-sm overflow-hidden">
            {STAGES.map((s) => (
              <ListboxOption
                key={s}
                value={s}
                className={({ active }) =>
                  clsx("flex items-center gap-3 px-4 py-2.5 cursor-pointer text-white", active && "bg-navy-600")
                }
              >
                {({ selected }) => (
                  <>
                    <span className="flex-1">{s}</span>
                    {selected && <CheckIcon className="h-4 w-4 text-gold-400" />}
                  </>
                )}
              </ListboxOption>
            ))}
          </ListboxOptions>
        </div>
      </Listbox>
    </div>
  );
}
