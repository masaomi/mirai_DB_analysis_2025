"use client";

import { useState, useEffect } from "react";
import { DollarSign, RefreshCw, AlertCircle } from "lucide-react";

interface CreditData {
  usage: number;
  limit: number | null;
  remaining: number | null;
  is_free_tier: boolean;
  label?: string;
  configured: boolean;
  error?: string;
}

interface Props {
  mode?: "compact" | "full";
  className?: string;
}

export default function OpenRouterCredits({ mode = "full", className = "" }: Props) {
  const [credits, setCredits] = useState<CreditData | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchCredits = async () => {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("/api/credits");
      const data = await res.json();
      
      if (!res.ok) {
        // If not configured (400) or other error, handle gracefully
        if (data.configured === false) {
          // Silent fail for unconfigured (don't show component)
          setCredits(null);
          return;
        }
        throw new Error(data.error || "Failed to fetch credits");
      }
      
      setCredits(data);
    } catch (e) {
      console.error("Error fetching credits:", e);
      setError(String(e));
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchCredits();
    // Auto-refresh every 5 minutes
    const interval = setInterval(fetchCredits, 5 * 60 * 1000);
    return () => clearInterval(interval);
  }, []);

  if (error || !credits) return null;

  // Format currency
  const formatUSD = (val: number) => `$${val.toFixed(4)}`;

  if (mode === "compact") {
    return (
      <div className={`flex items-center gap-2 text-xs bg-slate-100 px-3 py-1.5 rounded-full border border-slate-200 ${className}`}>
        <div className="flex items-center gap-1 text-slate-600" title="OpenRouter 使用量">
          <DollarSign className="w-3 h-3 text-green-600" />
          <span className="font-medium font-mono">{formatUSD(credits.usage)}</span>
        </div>
        
        {credits.limit && (
          <>
            <span className="text-slate-300">/</span>
            <span className="text-slate-400 font-mono" title="上限">{formatUSD(credits.limit)}</span>
          </>
        )}

        <button 
          onClick={(e) => { e.preventDefault(); fetchCredits(); }} 
          disabled={loading}
          className="ml-1 text-slate-400 hover:text-slate-600 transition-colors"
          title="更新"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>
    );
  }

  // Full mode
  return (
    <div className={`bg-white p-4 rounded-xl shadow-sm border border-slate-200 ${className}`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className="font-semibold text-slate-700 flex items-center gap-2 text-sm">
          <div className="bg-green-100 p-1 rounded-full">
            <DollarSign className="w-3 h-3 text-green-600" />
          </div>
          OpenRouter Credits
        </h3>
        <button 
          onClick={fetchCredits} 
          disabled={loading} 
          className="text-slate-400 hover:text-slate-600 transition-colors p-1 hover:bg-slate-50 rounded"
          title="更新"
        >
          <RefreshCw className={`w-3 h-3 ${loading ? 'animate-spin' : ''}`} />
        </button>
      </div>
      
      <div className="space-y-3">
        <div className="flex justify-between text-xs">
          <span className="text-slate-500">使用量</span>
          <span className="font-medium font-mono text-slate-700">{formatUSD(credits.usage)}</span>
        </div>

        {credits.limit ? (
          <>
            <div className="flex justify-between text-xs">
              <span className="text-slate-500">残り</span>
              <span className={`font-medium font-mono ${
                (credits.remaining || 0) < 1.0 ? 'text-red-500' : 'text-green-600'
              }`}>
                {formatUSD(credits.remaining || 0)}
              </span>
            </div>
            
            <div className="space-y-1">
              <div className="h-2 w-full bg-slate-100 rounded-full overflow-hidden">
                <div 
                  className={`h-full transition-all duration-500 ${
                    (credits.usage / credits.limit) > 0.9 ? 'bg-red-500' : 
                    (credits.usage / credits.limit) > 0.7 ? 'bg-yellow-500' : 'bg-green-500'
                  }`}
                  style={{ width: `${Math.min(100, (credits.usage / credits.limit) * 100)}%` }}
                />
              </div>
              <div className="flex justify-between text-[10px] text-slate-400">
                <span>0</span>
                <span>Limit: {formatUSD(credits.limit)}</span>
              </div>
            </div>
          </>
        ) : (
          <div className="flex items-start gap-2 text-xs text-slate-500 bg-slate-50 p-2 rounded">
            <AlertCircle className="w-3 h-3 mt-0.5 flex-shrink-0" />
            <span>上限設定なし (Pay-as-you-go)</span>
          </div>
        )}
      </div>
    </div>
  );
}

