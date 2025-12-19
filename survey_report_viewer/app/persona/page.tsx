"use client";

import { useState, useEffect, Suspense } from "react";
import { useRouter, useSearchParams } from "next/navigation";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import PersonaSettings, { DiscussionSettings } from "../components/PersonaSettings";

function PersonaPageContent() {
  const router = useRouter();
  const searchParams = useSearchParams();
  const [isLoading, setIsLoading] = useState(false);
  const [reportContext, setReportContext] = useState<{ 
    slug: string; 
    title: string; 
    summary: string;
    topic: string;
  } | null>(null);

  // Load report context if slug is provided
  useEffect(() => {
    const slug = searchParams.get("slug");
    const title = searchParams.get("title");
    
    if (slug) {
      fetch(`/api/reports/${slug}`)
        .then(res => res.json())
        .then(data => {
          const surveyTitle = title || data.analysisData?.survey_title || slug;
          const summary = data.markdown?.substring(0, 2000) || "";
          
          setReportContext({
            slug,
            title: surveyTitle,
            summary,
            topic: `「${surveyTitle}」に関する法案提出に向けた議論`
          });
        })
        .catch(err => console.error("Failed to load report context", err));
    }
  }, [searchParams]);

  const handleStart = async (settings: DiscussionSettings) => {
    setIsLoading(true);
    try {
      const res = await fetch("/api/persona/start", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(settings),
      });
      
      const data = await res.json();
      if (data.session_id) {
        localStorage.setItem(`persona_session_${data.session_id}`, JSON.stringify(settings.personas));
        router.push(`/persona/${data.session_id}`);
      } else {
        alert("セッション開始に失敗しました: " + (data.error || "Unknown error"));
      }
    } catch (e) {
      alert("エラーが発生しました: " + e);
    } finally {
      setIsLoading(false);
    }
  };

  return (
    <main className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-slate-200">
        <div className="max-w-4xl mx-auto px-6 py-4 flex items-center gap-4">
          <Link
            href={reportContext ? `/reports/${reportContext.slug}` : "/"}
            className="p-2 hover:bg-slate-100 rounded-full transition-colors text-slate-600"
          >
            <ArrowLeft size={20} />
          </Link>
          <div>
            <h1 className="text-xl font-bold text-slate-800">Persona Assembly</h1>
            <p className="text-sm text-slate-600">
              {reportContext 
                ? `「${reportContext.title}」に関するディスカッション`
                : "複数のAIペルソナによる合意形成ディスカッション"
              }
            </p>
          </div>
        </div>
      </header>

      {/* Report Context Banner */}
      {reportContext && (
        <div className="bg-purple-50 border-b border-purple-100">
          <div className="max-w-4xl mx-auto px-6 py-3">
            <p className="text-sm text-purple-700">
              📊 レポート「<strong>{reportContext.title}</strong>」のコンテキストとRAGデータがディスカッションに反映されます
            </p>
          </div>
        </div>
      )}

      <div className="max-w-4xl mx-auto p-6">
        <PersonaSettings 
          onStart={handleStart} 
          isLoading={isLoading}
          initialTopic={reportContext?.topic}
          initialContext={reportContext?.summary}
        />
      </div>
    </main>
  );
}

export default function PersonaPage() {
  return (
    <Suspense fallback={
      <div className="min-h-screen flex items-center justify-center">
        <p className="text-slate-500">読み込み中...</p>
      </div>
    }>
      <PersonaPageContent />
    </Suspense>
  );
}

