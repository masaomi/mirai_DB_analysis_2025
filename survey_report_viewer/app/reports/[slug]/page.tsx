"use client";

import { NextRequest } from "next/server";
import { useState, useEffect, use } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ArrowLeft, MessageSquare, Download, Share2, ArrowRight } from "lucide-react";

interface ReportData {
  slug: string;
  markdown: string;
  analysisData: {
    survey_title?: string;
    response_count?: number;
    stance_distribution?: Record<string, { count: number; percentage: number }>;
    cluster_details?: Array<{
      cluster_id: number;
      label: string;
      size: number;
      keywords: string[];
      sample_responses: string[];
    }>;
    minority_opinions?: Array<{
      content: string;
      outlier_score: number;
      uniqueness_reason: string;
    }>;
  };
  charts: string[];
}

export default function ReportPage({
  params,
}: {
  params: Promise<{ slug: string }>;
}) {
  const { slug } = use(params);
  const [report, setReport] = useState<ReportData | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetch(`/api/reports/${slug}`)
      .then((res) => {
        if (!res.ok) throw new Error("Report not found");
        return res.json();
      })
      .then((data) => {
        setReport(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, [slug]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <div className="flex justify-center gap-1">
            <div className="w-3 h-3 bg-primary-500 rounded-full loading-dot"></div>
            <div className="w-3 h-3 bg-primary-500 rounded-full loading-dot"></div>
            <div className="w-3 h-3 bg-primary-500 rounded-full loading-dot"></div>
          </div>
          <p className="text-slate-500 mt-4">レポートを読み込み中...</p>
        </div>
      </div>
    );
  }

  if (error || !report) {
    return (
      <div className="min-h-screen flex items-center justify-center">
        <div className="text-center">
          <h2 className="text-xl font-semibold text-red-600 mb-2">エラー</h2>
          <p className="text-slate-600">{error || "レポートが見つかりません"}</p>
          <Link
            href="/"
            className="mt-4 inline-flex items-center gap-2 text-primary-500 hover:text-primary-600"
          >
            <ArrowLeft className="w-4 h-4" />
            ホームに戻る
          </Link>
        </div>
      </div>
    );
  }

  return (
    <main className="min-h-screen bg-slate-50">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-slate-200 sticky top-0 z-10">
        <div className="max-w-4xl mx-auto px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-4">
              <Link
                href="/"
                className="text-slate-500 hover:text-slate-700 transition-colors"
              >
                <ArrowLeft className="w-5 h-5" />
              </Link>
              <div>
                <h1 className="text-lg font-semibold text-slate-800 line-clamp-1">
                  {report.analysisData.survey_title || slug}
                </h1>
                <p className="text-sm text-slate-500">
                  {report.analysisData.response_count}件の回答
                </p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              <Link
                href={`/qa/${slug}`}
                className="flex items-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
              >
                <MessageSquare className="w-4 h-4" />
                Q&A
              </Link>
            </div>
          </div>
        </div>
      </header>

      {/* Charts */}
      {report.charts.length > 0 && (
        <div className="bg-white border-b border-slate-200">
          <div className="max-w-4xl mx-auto px-6 py-8">
            <h2 className="text-lg font-semibold text-slate-700 mb-4">📊 チャート</h2>
            <div className="grid gap-6 md:grid-cols-2">
              {report.charts.map((chart, i) => (
                <div
                  key={i}
                  className="bg-slate-50 rounded-xl shadow-sm p-4 border border-slate-200"
                >
                  <img
                    src={chart}
                    alt={`Chart ${i + 1}`}
                    className="w-full h-auto rounded-lg"
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Report Content */}
      <div className="max-w-4xl mx-auto px-6 py-8">
        <article className="bg-white rounded-xl shadow-sm border border-slate-200 p-8 mb-8">
          <div className="prose max-w-none prose-headings:text-slate-800 prose-p:text-slate-600 prose-li:text-slate-600">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {report.markdown}
            </ReactMarkdown>
          </div>
        </article>

        {/* Cluster Drill-down Section */}
        {report.analysisData.cluster_details && report.analysisData.cluster_details.length > 0 && (
          <div className="mb-8">
            <h2 className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
              🔍 意見グループごとの深掘り
            </h2>
            <div className="grid gap-4 md:grid-cols-2">
              {report.analysisData.cluster_details
                .filter(c => c.cluster_id !== -1)
                .slice(0, 6)
                .map(cluster => (
                  <div key={cluster.cluster_id} className="bg-white p-5 rounded-xl shadow-sm border border-slate-200 hover:border-primary-300 transition-colors">
                    <div className="flex justify-between items-start mb-2">
                      <h3 className="font-bold text-md text-slate-800 line-clamp-1">{cluster.label}</h3>
                      <span className="bg-slate-100 text-slate-600 text-xs px-2 py-1 rounded-full flex-shrink-0">
                        {cluster.size}件
                      </span>
                    </div>
                    <p className="text-xs text-slate-500 mb-4 line-clamp-2">
                      キーワード: {cluster.keywords.slice(0, 5).join(", ")}
                    </p>
                    <Link
                      href={`/qa/${slug}?mode=rag&q=${encodeURIComponent(`「${cluster.label}」という意見グループについて、どのような意見が含まれているか具体的に教えてください`)}`}
                      className="inline-flex items-center gap-1.5 text-sm text-primary-600 hover:text-primary-700 font-medium group"
                    >
                      <MessageSquare size={14} />
                      このグループを深掘り
                      <ArrowRight size={14} className="group-hover:translate-x-0.5 transition-transform" />
                    </Link>
                  </div>
                ))}
            </div>
          </div>
        )}

        {/* Minority Opinions Section */}
        {report.analysisData.minority_opinions && report.analysisData.minority_opinions.length > 0 && (
          <div>
            <h2 className="text-xl font-bold text-slate-800 mb-4 flex items-center gap-2">
              💎 特徴的な少数意見
            </h2>
            <div className="space-y-4">
              {report.analysisData.minority_opinions.slice(0, 3).map((opinion, i) => (
                <div key={i} className="bg-white p-5 rounded-xl shadow-sm border border-slate-200 hover:border-purple-300 transition-colors border-l-4 border-l-purple-400">
                  <div className="mb-2 flex items-center gap-2">
                    <span className="text-sm font-bold text-slate-700">{opinion.uniqueness_reason}</span>
                  </div>
                  <p className="text-slate-600 mb-3 italic text-sm border-l-2 border-slate-200 pl-3 ml-1">
                    "{opinion.content.length > 120 ? opinion.content.substring(0, 120) + "..." : opinion.content}"
                  </p>
                  <Link
                    href={`/qa/${slug}?mode=rag&q=${encodeURIComponent(`以下の少数意見について、具体的な背景や詳細を教えてください:\n\n「${opinion.content.substring(0, 100)}...」`)}`}
                    className="inline-flex items-center gap-1.5 text-sm text-purple-600 hover:text-purple-700 font-medium group"
                  >
                    <MessageSquare size={14} />
                    詳細を聞く
                    <ArrowRight size={14} className="group-hover:translate-x-0.5 transition-transform" />
                  </Link>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </main>
  );
}


