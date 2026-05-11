"use client";

import { useState } from "react";
import { useRouter } from "next/navigation";
import { WC2026_GROUPS, WCGroup, WCMatch } from "@/lib/wc2026Groups";
import GroupBracket from "@/components/GroupBracket";
import GroupView from "@/components/GroupView";

const GROUP_IDS = WC2026_GROUPS.map((g) => g.id);

export default function GroupsPage() {
  const router = useRouter();
  const [selectedGroup, setSelectedGroup] = useState<WCGroup | null>(null);

  function handleMatchPredict(match: WCMatch) {
    const params = new URLSearchParams({
      home: match.home,
      away: match.away,
      date: match.date,
      stage: "Group Stage",
    });
    router.push(`/predict?${params.toString()}`);
  }

  return (
    <main className="min-h-screen bg-navy-900">
      <div className="max-w-4xl mx-auto px-4 py-10 flex flex-col gap-6">
        {/* Page header */}
        <div>
          <h1 className="text-2xl font-bold text-white">Group Stage</h1>
          <p className="text-slate-400 text-sm mt-1">
            Browse all 12 groups · June 11 – July 2, 2026
          </p>
        </div>

        {/* Quick-jump pills */}
        <div className="flex flex-wrap gap-1.5 items-center">
          {GROUP_IDS.map((id) => (
            <button
              key={id}
              onClick={() => setSelectedGroup(WC2026_GROUPS.find((g) => g.id === id) ?? null)}
              className={`w-9 h-9 rounded-lg text-sm font-bold transition-colors ${
                selectedGroup?.id === id
                  ? "bg-fifa-blue text-white"
                  : "bg-navy-800 border border-navy-600 text-slate-400 hover:text-white hover:border-fifa-blue"
              }`}
            >
              {id}
            </button>
          ))}
          {selectedGroup && (
            <button
              onClick={() => setSelectedGroup(null)}
              className="px-3 h-9 rounded-lg text-sm text-slate-500 border border-navy-600 hover:text-white hover:border-slate-500 transition-colors ml-1"
            >
              All groups
            </button>
          )}
        </div>

        {selectedGroup ? (
          <GroupView
            group={selectedGroup}
            onBack={() => setSelectedGroup(null)}
            onPredict={handleMatchPredict}
          />
        ) : (
          <GroupBracket onSelectGroup={setSelectedGroup} showHeader={false} />
        )}
      </div>
    </main>
  );
}
