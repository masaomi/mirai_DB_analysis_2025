"use client";

import { useChat } from "ai/react";
import { useParams, useSearchParams } from "next/navigation";
import { useState, useRef, useEffect, Suspense } from "react";
import Link from "next/link";
import { Send, ArrowLeft, Bot, User, Info, Database, FileText } from "lucide-react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

function QAContent() {
  const params = useParams();
  const searchParams = useSearchParams();
  const slug = params.slug as string;
  const mode = searchParams.get("mode") || "simple";
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const { messages, input, handleInputChange, handleSubmit, isLoading, error } = useChat({
    api: `/api/qa?mode=${mode}`,
    body: { slug },
    onError: (error) => {
      console.error("Chat error:", error);
    },
  });

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  const isRAGMode = mode === "rag";

  return (
    <div className="flex flex-col h-screen bg-gray-50">
      {/* Header */}
      <header className="bg-white border-b px-6 py-4 flex items-center justify-between shadow-sm z-10">
        <div className="flex items-center gap-4">
          <Link
            href={`/reports/${slug}`}
            className="p-2 hover:bg-gray-100 rounded-full transition-colors text-gray-600"
            title="レポートに戻る"
          >
            <ArrowLeft size={20} />
          </Link>
          <div>
            <h1 className="font-bold text-lg text-gray-800">AI アシスタント</h1>
            <p className="text-xs text-gray-500">レポートの内容について質問してください</p>
          </div>
        </div>
        
        {/* Mode Toggle */}
        <div className="flex items-center gap-2">
          <Link
            href={`/qa/${slug}?mode=simple`}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
              !isRAGMode
                ? "bg-blue-100 text-blue-700 font-medium"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            <FileText size={14} />
            シンプル
          </Link>
          <Link
            href={`/qa/${slug}?mode=rag`}
            className={`flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm transition-colors ${
              isRAGMode
                ? "bg-purple-100 text-purple-700 font-medium"
                : "bg-gray-100 text-gray-600 hover:bg-gray-200"
            }`}
          >
            <Database size={14} />
            RAG
          </Link>
        </div>
      </header>

      {/* Mode Info Banner */}
      <div className={`px-6 py-2 text-sm ${isRAGMode ? "bg-purple-50 text-purple-700" : "bg-blue-50 text-blue-700"}`}>
        {isRAGMode ? (
          <span className="flex items-center gap-2">
            <Database size={14} />
            <strong>RAGモード:</strong> 個別のアンケート回答を検索して、具体的な意見を引用できます
          </span>
        ) : (
          <span className="flex items-center gap-2">
            <FileText size={14} />
            <strong>シンプルモード:</strong> 分析レポートの要約データに基づいて回答します
          </span>
        )}
      </div>

      {/* Chat Area */}
      <main className="flex-1 overflow-y-auto p-4 md:p-6">
        <div className="max-w-3xl mx-auto space-y-6">
          {/* Welcome Message */}
          {messages.length === 0 && (
            <div className={`border rounded-lg p-6 text-center my-10 ${
              isRAGMode ? "bg-purple-50 border-purple-100" : "bg-blue-50 border-blue-100"
            }`}>
              <div className={`w-12 h-12 rounded-full flex items-center justify-center mx-auto mb-4 ${
                isRAGMode ? "bg-purple-100 text-purple-600" : "bg-blue-100 text-blue-600"
              }`}>
                <Bot size={24} />
              </div>
              <h2 className={`text-lg font-semibold mb-2 ${isRAGMode ? "text-purple-800" : "text-blue-800"}`}>
                {isRAGMode 
                  ? "個別回答を検索して回答します" 
                  : "アンケート分析について何でも聞いてください"
                }
              </h2>
              <p className={`text-sm mb-6 max-w-md mx-auto ${isRAGMode ? "text-purple-600" : "text-blue-600"}`}>
                {isRAGMode
                  ? "元のアンケート回答データを検索し、具体的な意見を引用して回答します。"
                  : "レポートの内容、特定クラスタの詳細、立場ごとの意見の違いなどについてお答えします。"
                }
              </p>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-3 text-left max-w-2xl mx-auto">
                <button
                  onClick={() => handleInputChange({ target: { value: "賛成派の主な理由は？" } } as any)}
                  className={`p-3 bg-white border rounded-md text-sm text-gray-700 transition-colors ${
                    isRAGMode ? "hover:bg-purple-50 border-purple-200" : "hover:bg-blue-50 border-blue-200"
                  }`}
                >
                  賛成派の主な理由は？
                </button>
                <button
                  onClick={() => handleInputChange({ target: { value: "どのような懸念点がありますか？" } } as any)}
                  className={`p-3 bg-white border rounded-md text-sm text-gray-700 transition-colors ${
                    isRAGMode ? "hover:bg-purple-50 border-purple-200" : "hover:bg-blue-50 border-blue-200"
                  }`}
                >
                  どのような懸念点がありますか？
                </button>
                <button
                  onClick={() => handleInputChange({ target: { value: isRAGMode ? "セキュリティについての具体的な意見は？" : "少数派の意見を教えて" } } as any)}
                  className={`p-3 bg-white border rounded-md text-sm text-gray-700 transition-colors ${
                    isRAGMode ? "hover:bg-purple-50 border-purple-200" : "hover:bg-blue-50 border-blue-200"
                  }`}
                >
                  {isRAGMode ? "セキュリティについての具体的な意見は？" : "少数派の意見を教えて"}
                </button>
                <button
                  onClick={() => handleInputChange({ target: { value: isRAGMode ? "電子化に反対する人の理由を教えて" : "最大クラスタの特徴は？" } } as any)}
                  className={`p-3 bg-white border rounded-md text-sm text-gray-700 transition-colors ${
                    isRAGMode ? "hover:bg-purple-50 border-purple-200" : "hover:bg-blue-50 border-blue-200"
                  }`}
                >
                  {isRAGMode ? "電子化に反対する人の理由を教えて" : "最大クラスタの特徴は？"}
                </button>
              </div>
            </div>
          )}

          {/* Messages */}
          {messages.map((m) => (
            <div
              key={m.id}
              className={`flex gap-4 ${m.role === "user" ? "justify-end" : "justify-start"}`}
            >
              {m.role === "assistant" && (
                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1 ${
                  isRAGMode ? "bg-purple-100 text-purple-600" : "bg-blue-100 text-blue-600"
                }`}>
                  <Bot size={16} />
                </div>
              )}
              
              <div
                className={`max-w-[85%] md:max-w-[75%] rounded-2xl px-5 py-3 shadow-sm ${
                  m.role === "user"
                    ? `${isRAGMode ? "bg-purple-600" : "bg-blue-600"} text-white rounded-tr-none`
                    : "bg-white border border-gray-100 text-gray-800 rounded-tl-none"
                }`}
              >
                {m.role === "user" ? (
                  <div className="whitespace-pre-wrap">{m.content}</div>
                ) : (
                  <div className="prose prose-sm max-w-none dark:prose-invert">
                    <ReactMarkdown remarkPlugins={[remarkGfm]}>
                      {m.content}
                    </ReactMarkdown>
                  </div>
                )}
              </div>

              {m.role === "user" && (
                <div className="w-8 h-8 rounded-full bg-gray-200 flex items-center justify-center flex-shrink-0 text-gray-500 mt-1">
                  <User size={16} />
                </div>
              )}
            </div>
          ))}

          {/* Loading Indicator */}
          {isLoading && (
            <div className="flex gap-4 justify-start">
              <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 mt-1 ${
                isRAGMode ? "bg-purple-100 text-purple-600" : "bg-blue-100 text-blue-600"
              }`}>
                <Bot size={16} />
              </div>
              <div className="bg-white border border-gray-100 rounded-2xl rounded-tl-none px-5 py-4 shadow-sm flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full animate-bounce ${isRAGMode ? "bg-purple-400" : "bg-blue-400"}`} style={{ animationDelay: "0ms" }} />
                <div className={`w-2 h-2 rounded-full animate-bounce ${isRAGMode ? "bg-purple-400" : "bg-blue-400"}`} style={{ animationDelay: "150ms" }} />
                <div className={`w-2 h-2 rounded-full animate-bounce ${isRAGMode ? "bg-purple-400" : "bg-blue-400"}`} style={{ animationDelay: "300ms" }} />
              </div>
            </div>
          )}

          {/* Error Message */}
          {error && (
            <div className="bg-red-50 border border-red-100 rounded-lg p-4 text-red-600 text-sm flex items-start gap-2">
              <Info size={16} className="mt-0.5 flex-shrink-0" />
              <div>
                <p className="font-semibold">エラーが発生しました</p>
                <p>{error.message}</p>
              </div>
            </div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </main>

      {/* Input Area */}
      <footer className="bg-white border-t p-4 md:p-6">
        <div className="max-w-3xl mx-auto">
          <form onSubmit={handleSubmit} className="relative">
            <input
              className={`w-full p-4 pr-12 rounded-xl border focus:ring-2 focus:outline-none transition-all shadow-sm ${
                isRAGMode 
                  ? "border-purple-300 focus:border-purple-500 focus:ring-purple-100" 
                  : "border-gray-300 focus:border-blue-500 focus:ring-blue-100"
              }`}
              value={input}
              onChange={handleInputChange}
              placeholder={isRAGMode ? "個別回答を検索して質問..." : "質問を入力してください..."}
              disabled={isLoading}
            />
            <button
              type="submit"
              disabled={isLoading || !input.trim()}
              className={`absolute right-3 top-1/2 -translate-y-1/2 p-2 text-white rounded-lg disabled:bg-gray-300 disabled:cursor-not-allowed transition-colors ${
                isRAGMode ? "bg-purple-600 hover:bg-purple-700" : "bg-blue-600 hover:bg-blue-700"
              }`}
            >
              <Send size={18} />
            </button>
          </form>
          <p className="text-center text-xs text-gray-400 mt-2">
            {isRAGMode 
              ? "RAGモード: 元のアンケート回答を検索して具体的な意見を引用します"
              : "AIは不正確な情報を生成する可能性があります。重要な情報は元データを確認してください。"
            }
          </p>
        </div>
      </footer>
    </div>
  );
}

export default function QAPage() {
  return (
    <Suspense fallback={
      <div className="flex items-center justify-center h-screen">
        <div className="text-gray-500">Loading...</div>
      </div>
    }>
      <QAContent />
    </Suspense>
  );
}
