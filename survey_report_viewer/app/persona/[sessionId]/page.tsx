"use client";

import { useEffect, useState } from "react";
import { useParams, useRouter } from "next/navigation";
import Link from "next/link";
import PersonaChat from "../../components/PersonaChat";
import { PersonaConfig } from "../../components/PersonaSettings";
import { ArrowLeft } from "lucide-react";

export default function SessionPage() {
  const params = useParams();
  const router = useRouter();
  const sessionId = params.sessionId as string;
  const [initialPersonas, setInitialPersonas] = useState<PersonaConfig[]>([]);

  useEffect(() => {
    // Load initial personas from localStorage (backup)
    // Primary source is 'start' event in PersonaChat
    const stored = localStorage.getItem(`persona_session_${sessionId}`);
    if (stored) {
      try {
        setInitialPersonas(JSON.parse(stored));
      } catch (e) {
        console.error("Failed to parse stored personas", e);
      }
    }
  }, [sessionId]);

  return (
    <main className="min-h-screen bg-slate-100">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-slate-200">
        <div className="max-w-7xl mx-auto px-6 py-3 flex items-center gap-4">
          <Link
            href="/persona"
            className="p-2 hover:bg-slate-100 rounded-full transition-colors text-slate-600"
          >
            <ArrowLeft size={20} />
          </Link>
          <div>
            <h1 className="text-lg font-bold text-slate-800">ディスカッション会場</h1>
            <p className="text-xs text-slate-500">Session: {sessionId.substring(0, 8)}...</p>
          </div>
        </div>
      </header>

      <div className="max-w-7xl mx-auto p-6">
        <PersonaChat 
          sessionId={sessionId} 
          initialPersonas={initialPersonas}
          onEnd={() => router.push("/persona")} 
        />
      </div>
    </main>
  );
}

