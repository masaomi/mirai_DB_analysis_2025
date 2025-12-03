"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { FileText, MessageSquare, BarChart3 } from "lucide-react";

interface SurveyReport {
  slug: string;
  title: string;
  generated_at: string;
  response_count: number;
}

export default function Home() {
  const [reports, setReports] = useState<SurveyReport[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/reports")
      .then((res) => res.json())
      .then((data) => {
        setReports(data.reports || []);
        setLoading(false);
      })
      .catch(() => setLoading(false));
  }, []);

  return (
    <main className="min-h-screen">
      {/* Header */}
      <header className="bg-white shadow-sm border-b border-slate-200">
        <div className="max-w-6xl mx-auto px-6 py-4">
          <h1 className="text-2xl font-bold text-slate-800">
            📊 Survey Report Viewer
          </h1>
          <p className="text-slate-600 mt-1">
            アンケート分析レポートの閲覧・Q&Aシステム
          </p>
        </div>
      </header>

      {/* Main Content */}
      <div className="max-w-6xl mx-auto px-6 py-8">
        {loading ? (
          <div className="text-center py-12">
            <div className="flex justify-center gap-1">
              <div className="w-3 h-3 bg-primary-500 rounded-full loading-dot"></div>
              <div className="w-3 h-3 bg-primary-500 rounded-full loading-dot"></div>
              <div className="w-3 h-3 bg-primary-500 rounded-full loading-dot"></div>
            </div>
            <p className="text-slate-500 mt-4">レポートを読み込み中...</p>
          </div>
        ) : reports.length === 0 ? (
          <div className="text-center py-12 bg-white rounded-xl shadow-sm">
            <FileText className="w-16 h-16 text-slate-300 mx-auto mb-4" />
            <h2 className="text-xl font-semibold text-slate-700 mb-2">
              レポートがありません
            </h2>
            <p className="text-slate-500">
              survey_analysis_pipeline でレポートを生成してください
            </p>
          </div>
        ) : (
          <div className="grid gap-6 md:grid-cols-2 lg:grid-cols-3">
            {reports.map((report) => (
              <div
                key={report.slug}
                className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden hover:shadow-md transition-shadow"
              >
                <div className="p-6">
                  <h3 className="text-lg font-semibold text-slate-800 mb-2 line-clamp-2">
                    {report.title}
                  </h3>
                  <div className="flex items-center gap-4 text-sm text-slate-500 mb-4">
                    <span>📅 {report.generated_at}</span>
                    <span>📝 {report.response_count}件</span>
                  </div>
                  <div className="flex gap-2">
                    <Link
                      href={`/reports/${report.slug}`}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-primary-500 text-white rounded-lg hover:bg-primary-600 transition-colors"
                    >
                      <FileText className="w-4 h-4" />
                      レポート
                    </Link>
                    <Link
                      href={`/qa/${report.slug}`}
                      className="flex-1 flex items-center justify-center gap-2 px-4 py-2 bg-slate-100 text-slate-700 rounded-lg hover:bg-slate-200 transition-colors"
                    >
                      <MessageSquare className="w-4 h-4" />
                      Q&A
                    </Link>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}

        {/* Quick Links */}
        <div className="mt-12 grid gap-4 md:grid-cols-3">
          <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <BarChart3 className="w-8 h-8 text-primary-500 mb-3" />
            <h3 className="font-semibold text-slate-800 mb-2">分析機能</h3>
            <p className="text-sm text-slate-600">
              立場検出、クラスタリング、マイノリティ意見の自動抽出
            </p>
          </div>
          <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <FileText className="w-8 h-8 text-primary-500 mb-3" />
            <h3 className="font-semibold text-slate-800 mb-2">レポート生成</h3>
            <p className="text-sm text-slate-600">
              LLMによる自動要約、Markdown/HTML形式のレポート
            </p>
          </div>
          <div className="bg-white p-6 rounded-xl shadow-sm border border-slate-200">
            <MessageSquare className="w-8 h-8 text-primary-500 mb-3" />
            <h3 className="font-semibold text-slate-800 mb-2">Q&A機能</h3>
            <p className="text-sm text-slate-600">
              RAGベースのチャットでレポートについて質問
            </p>
          </div>
        </div>
      </div>
    </main>
  );
}

