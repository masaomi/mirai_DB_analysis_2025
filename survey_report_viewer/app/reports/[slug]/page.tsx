"use client";

import { useState, useEffect, use } from "react";
import Link from "next/link";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { ArrowLeft, MessageSquare, Download, Share2 } from "lucide-react";

interface ReportData {
  slug: string;
  markdown: string;
  analysisData: {
    survey_title?: string;
    response_count?: number;
    stance_distribution?: Record<string, { count: number; percentage: number }>;
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
    <main className="min-h-screen">
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
        <div className="bg-slate-50 border-b border-slate-200">
          <div className="max-w-4xl mx-auto px-6 py-6">
            <h2 className="text-lg font-semibold text-slate-700 mb-4">📊 チャート</h2>
            <div className="grid gap-4 md:grid-cols-2">
              {report.charts.map((chart, i) => (
                <div
                  key={i}
                  className="bg-white rounded-lg shadow-sm p-4 border border-slate-200"
                >
                  <img
                    src={chart}
                    alt={`Chart ${i + 1}`}
                    className="w-full h-auto"
                  />
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Report Content */}
      <div className="max-w-4xl mx-auto px-6 py-8">
        <article className="bg-white rounded-xl shadow-sm border border-slate-200 p-8">
          <div className="prose max-w-none">
            <ReactMarkdown remarkPlugins={[remarkGfm]}>
              {report.markdown}
            </ReactMarkdown>
          </div>
        </article>
      </div>
    </main>
  );
}

