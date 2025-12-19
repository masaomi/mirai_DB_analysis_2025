"use client";

import { BarChart3, Zap } from "lucide-react";
import { PersonaConfig } from "./PersonaSettings";

interface Props {
  stats: { [personaId: string]: number };
  personas: PersonaConfig[];
}

export default function TokenUsageDisplay({ stats, personas }: Props) {
  const totalTokens = Object.values(stats).reduce((a, b) => a + b, 0);

  return (
    <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200">
      <h3 className="font-semibold text-slate-700 mb-4 flex items-center gap-2">
        <Zap className="w-4 h-4 text-yellow-500" />
        トークン使用量 (推定)
      </h3>
      
      <div className="space-y-4">
        {personas.map((persona) => {
          const count = stats[persona.id] || 0;
          const percent = totalTokens > 0 ? (count / totalTokens) * 100 : 0;
          
          return (
            <div key={persona.id}>
              <div className="flex justify-between text-xs mb-1">
                <span className="font-medium text-slate-700">{persona.name}</span>
                <span className="text-slate-500">{count.toLocaleString()} tokens</span>
              </div>
              <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                <div 
                  className={`h-full ${persona.color?.split(' ')[0] || 'bg-slate-400'} transition-all duration-500`}
                  style={{ width: `${percent}%` }}
                />
              </div>
            </div>
          );
        })}

        <div className="pt-4 border-t border-slate-100 mt-2">
            <div className="flex justify-between text-sm font-bold text-slate-800">
                <span>合計</span>
                <span>{totalTokens.toLocaleString()} tokens</span>
            </div>
        </div>
      </div>
    </div>
  );
}

