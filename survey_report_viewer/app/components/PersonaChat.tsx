"use client";

import { useState, useEffect, useRef } from "react";
import { Send, User, Bot, StopCircle, Download, FileText, AlertCircle, ClipboardCopy, FileDown } from "lucide-react";
import { PersonaConfig } from "./PersonaSettings";
import TokenUsageDisplay from "./TokenUsageDisplay";

interface ChatMessage {
  id: string;
  role: "system" | "user" | "assistant" | "report";
  content: string;
  name?: string;
  personaId?: string;
  timestamp: string;
  isReport?: boolean;
}

interface TokenStats {
  [personaId: string]: number;
}

interface Props {
  sessionId: string;
  initialPersonas: PersonaConfig[];
  onEnd: () => void;
}

export default function PersonaChat({ sessionId, initialPersonas, onEnd }: Props) {
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const [typingPersonaId, setTypingPersonaId] = useState<string | null>(null);
  const [typingContent, setTypingContent] = useState("");
  const [status, setStatus] = useState<"connecting" | "active" | "completed" | "error">("connecting");
  const [errorMsg, setErrorMsg] = useState("");
  const [tokenStats, setTokenStats] = useState<TokenStats>({});
  const [currentRound, setCurrentRound] = useState(0);
  const [finalReport, setFinalReport] = useState<string>("");
  const [isGeneratingReport, setIsGeneratingReport] = useState(false);
  const [reportContent, setReportContent] = useState("");
  
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const eventSourceRef = useRef<EventSource | null>(null);

  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, typingContent]);

  // SSE Connection
  useEffect(() => {
    if (!sessionId) return;

    const es = new EventSource(`/api/persona/stream?session_id=${sessionId}`);
    eventSourceRef.current = es;

    es.onopen = () => {
      setStatus("active");
    };

    es.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        handleEvent(data);
      } catch (e) {
        console.error("Failed to parse event", e);
      }
    };

    es.onerror = () => {
      // This is normal when the discussion ends - SSE connection closes
      // Only log in development, not as error
      if (process.env.NODE_ENV === "development") {
        console.log("EventSource closed (normal after discussion ends)");
      }
      es.close();
    };

    return () => {
      es.close();
    };
  }, [sessionId]);

  const handleEvent = (event: any) => {
    switch (event.type) {
      case "start":
        setMessages([{
          id: "sys-start",
          role: "system",
          content: `ディスカッションを開始します (トピック: ${event.data.topic})`,
          timestamp: new Date().toISOString()
        }]);
        // Update personas from server if provided
        if (event.data.personas && event.data.personas.length > 0) {
          // Could update initialPersonas here if needed
        }
        break;

      case "rag_search":
        setMessages(prev => [...prev, {
          id: "sys-rag",
          role: "system",
          content: `📚 RAG検索: ${event.data.count}件の関連回答をコンテキストに追加しました`,
          timestamp: new Date().toISOString()
        }]);
        break;
        
      case "round_start":
        setCurrentRound(event.data.round);
        const roundInfo = event.data.elapsed_minutes 
          ? ` (経過: ${event.data.elapsed_minutes}分, ${event.data.total_tokens?.toLocaleString() || 0} tokens)`
          : "";
        setMessages(prev => [...prev, {
          id: `sys-round-${event.data.round}`,
          role: "system",
          content: `--- ラウンド ${event.data.round}${roundInfo} ---`,
          timestamp: new Date().toISOString()
        }]);
        break;

      case "typing_start":
        setIsTyping(true);
        setTypingPersonaId(event.data.persona_id);
        setTypingContent("");
        break;

      case "token":
        if (event.data.persona_id === typingPersonaId) {
           setTypingContent(prev => prev + event.data.content);
        }
        break;

      case "typing_end":
        setIsTyping(false);
        setTypingPersonaId(null);
        setTypingContent("");
        
        // Add full message
        const persona = initialPersonas.find(p => p.id === event.data.persona_id);
        setMessages(prev => [...prev, {
          id: `msg-${Date.now()}`,
          role: "assistant",
          name: persona?.name || event.data.persona_id,
          personaId: event.data.persona_id,
          content: event.data.content,
          timestamp: new Date().toISOString()
        }]);
        
        // Update accurate token count if provided
        if (event.data.tokens) {
             setTokenStats(prev => ({
                ...prev,
                [event.data.persona_id]: event.data.tokens
            }));
        }
        break;

      case "user_message":
        setMessages(prev => [...prev, {
            id: `usr-${Date.now()}`,
            role: "user",
            content: event.data.content,
            timestamp: new Date().toISOString()
        }]);
        break;

      case "end":
        setStatus("completed");
        const endReasons: Record<string, string> = {
          "max_rounds_reached": "最大ラウンド数に到達",
          "time_limit_reached": "時間制限に到達",
          "token_limit_reached": "トークン上限に到達",
          "user_stopped": "ユーザーによる中止",
        };
        const reasonText = endReasons[event.data.reason] || event.data.reason;
        setMessages(prev => [...prev, {
            id: "sys-end",
            role: "system",
            content: `ディスカッションが終了しました (${reasonText})`,
            timestamp: new Date().toISOString()
        }]);
        if (eventSourceRef.current) {
            eventSourceRef.current.close();
        }
        break;

      case "error":
        setErrorMsg(event.data);
        setStatus("error");
        break;

      case "approaching_end":
        setMessages(prev => [...prev, {
          id: `sys-approaching-${Date.now()}`,
          role: "system",
          content: `⚠️ ${event.data.warning} - まもなくレポート作成を開始します`,
          timestamp: new Date().toISOString()
        }]);
        break;

      case "report_start":
        setIsGeneratingReport(true);
        setReportContent("");
        setMessages(prev => [...prev, {
          id: `sys-report-start`,
          role: "system",
          content: `📝 ${event.data.message}`,
          timestamp: new Date().toISOString()
        }]);
        break;

      case "report_token":
        setReportContent(prev => prev + event.data.content);
        break;

      case "report_end":
        setIsGeneratingReport(false);
        setFinalReport(event.data.content);
        setMessages(prev => [...prev, {
          id: `report-${Date.now()}`,
          role: "report",
          name: event.data.name,
          personaId: event.data.persona_id,
          content: event.data.content,
          timestamp: new Date().toISOString(),
          isReport: true
        }]);
        break;

      case "report_error":
        setIsGeneratingReport(false);
        setMessages(prev => [...prev, {
          id: `sys-report-error`,
          role: "system",
          content: `❌ レポート生成エラー: ${event.data.error}`,
          timestamp: new Date().toISOString()
        }]);
        break;
    }
  };

  const handleInterrupt = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!input.trim()) return;

    const content = input;
    setInput(""); // Optimistic clear

    try {
      await fetch("/api/persona/interrupt", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
            session_id: sessionId,
            content: content
        }),
      });
      // Message will be added via SSE 'user_message' event
    } catch (e) {
      console.error("Failed to interrupt", e);
      setInput(content); // Restore on error
    }
  };

  const handleSaveLog = async () => {
    try {
        // Also save to server
        await fetch("/api/persona/save", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId }),
        });
        
        // Download as text file
        const logContent = messages.map(m => {
          const time = new Date(m.timestamp).toLocaleTimeString("ja-JP");
          if (m.role === "system") return `[${time}] --- ${m.content} ---`;
          if (m.role === "user") return `[${time}] ユーザー: ${m.content}`;
          if (m.role === "report") return `[${time}] 📝 ${m.name} (レポート):\n${m.content}`;
          return `[${time}] ${m.name}: ${m.content}`;
        }).join("\n\n");
        
        const blob = new Blob([logContent], { type: "text/plain;charset=utf-8" });
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = `persona_discussion_${sessionId.slice(0,8)}_${new Date().toISOString().slice(0,10)}.txt`;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        URL.revokeObjectURL(url);
    } catch (e) {
        alert("保存に失敗しました");
    }
  };

  const handleDownloadReport = () => {
    if (!finalReport) return;
    
    const blob = new Blob([finalReport], { type: "text/markdown;charset=utf-8" });
    const url = URL.createObjectURL(blob);
    const a = document.createElement("a");
    a.href = url;
    a.download = `persona_report_${sessionId.slice(0,8)}_${new Date().toISOString().slice(0,10)}.md`;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  };

  const handleCopyReport = () => {
    if (!finalReport) return;
    navigator.clipboard.writeText(finalReport);
    alert("レポートをクリップボードにコピーしました");
  };

  const handleStopDiscussion = async () => {
    if (status !== "active") return;
    
    if (!confirm("ディスカッションを中止しますか？")) return;
    
    try {
      await fetch("/api/persona/stop", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ session_id: sessionId }),
      });
      // The end event will be received via SSE
    } catch (e) {
      console.error("Failed to stop discussion", e);
      alert("中止に失敗しました");
    }
  };

  return (
    <div className="flex h-[calc(100vh-100px)] gap-6">
      {/* Main Chat Area */}
      <div className="flex-1 flex flex-col bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        {/* Header */}
        <div className="p-4 border-b border-slate-200 bg-slate-50 flex justify-between items-center">
            <div className="flex items-center gap-3">
                <div className={`w-3 h-3 rounded-full ${
                    status === 'active' ? 'bg-green-500 animate-pulse' : 
                    status === 'completed' ? 'bg-slate-500' : 'bg-yellow-500'
                }`} />
                <span className="font-semibold text-slate-700">
                    {status === 'active' ? 'ディスカッション進行中' : 
                     status === 'completed' ? '終了' : '接続中...'}
                </span>
                {currentRound > 0 && (
                    <span className="text-xs px-2 py-1 bg-slate-200 rounded text-slate-600">
                        Round {currentRound}
                    </span>
                )}
            </div>
            <div className="flex gap-2">
                {status === "active" && (
                    <button 
                        onClick={handleStopDiscussion}
                        className="flex items-center gap-1 px-3 py-1.5 text-sm bg-red-100 text-red-700 hover:bg-red-200 rounded-lg transition-colors"
                        title="ディスカッションを中止"
                    >
                        <StopCircle className="w-4 h-4" />
                        <span className="hidden sm:inline">中止</span>
                    </button>
                )}
                <button 
                    onClick={handleSaveLog}
                    className="flex items-center gap-1 px-3 py-1.5 text-sm text-slate-600 hover:bg-slate-200 rounded-lg transition-colors"
                    title="会話ログをダウンロード"
                >
                    <Download className="w-4 h-4" />
                    <span className="hidden sm:inline">ログ</span>
                </button>
                {finalReport && (
                    <>
                        <button 
                            onClick={handleDownloadReport}
                            className="flex items-center gap-1 px-3 py-1.5 text-sm bg-purple-100 text-purple-700 hover:bg-purple-200 rounded-lg transition-colors"
                            title="レポートをダウンロード"
                        >
                            <FileDown className="w-4 h-4" />
                            <span className="hidden sm:inline">レポート</span>
                        </button>
                        <button 
                            onClick={handleCopyReport}
                            className="p-2 text-slate-600 hover:bg-slate-200 rounded-lg transition-colors"
                            title="レポートをコピー"
                        >
                            <ClipboardCopy className="w-4 h-4" />
                        </button>
                    </>
                )}
            </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto p-6 space-y-6 bg-slate-50/50">
            {messages.map((m) => {
                const isSystem = m.role === "system";
                const isUser = m.role === "user";
                const isReport = m.role === "report" || m.isReport;
                const persona = initialPersonas.find(p => p.id === m.personaId);
                
                if (isSystem) {
                    return (
                        <div key={m.id} className="flex justify-center my-4">
                            <span className="text-xs text-slate-500 bg-slate-100 px-3 py-1 rounded-full border border-slate-200">
                                {m.content}
                            </span>
                        </div>
                    );
                }

                // Special styling for final report
                if (isReport) {
                    return (
                        <div key={m.id} className="my-6">
                            <div className="bg-gradient-to-r from-purple-50 to-pink-50 border-2 border-purple-200 rounded-xl p-6 shadow-lg">
                                <div className="flex items-center gap-2 mb-4 pb-3 border-b border-purple-200">
                                    <FileText className="w-5 h-5 text-purple-600" />
                                    <span className="font-bold text-purple-800">📋 最終レポート</span>
                                    <span className="text-sm text-purple-600">by {m.name}</span>
                                </div>
                                <div className="prose prose-sm max-w-none text-slate-700 whitespace-pre-wrap">
                                    {m.content}
                                </div>
                            </div>
                        </div>
                    );
                }

                return (
                    <div key={m.id} className={`flex gap-4 ${isUser ? "justify-end" : ""}`}>
                        {!isUser && (
                            <div className={`w-10 h-10 rounded-full flex items-center justify-center flex-shrink-0 text-lg shadow-sm ${
                                persona?.color?.split(' ')[0] || 'bg-slate-200'
                            }`}>
                                {persona?.avatar || <Bot size={20} className={persona?.color?.split(' ')[1]} />}
                            </div>
                        )}
                        
                        <div className={`max-w-[80%] space-y-1 ${isUser ? "items-end flex flex-col" : ""}`}>
                            {!isUser && (
                                <div className="text-xs text-slate-500 font-medium ml-1">
                                    {m.name}
                                </div>
                            )}
                            <div className={`p-4 rounded-2xl shadow-sm whitespace-pre-wrap ${
                                isUser 
                                    ? "bg-primary-600 text-white rounded-tr-none" 
                                    : "bg-white border border-slate-200 text-slate-800 rounded-tl-none"
                            }`}>
                                {m.content}
                            </div>
                        </div>

                        {isUser && (
                            <div className="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center flex-shrink-0 shadow-sm text-slate-500">
                                <User size={20} />
                            </div>
                        )}
                    </div>
                );
            })}

            {/* Typing Indicator */}
            {isTyping && typingPersonaId && (
                <div className="flex gap-4">
                    <div className="w-10 h-10 rounded-full bg-slate-200 flex items-center justify-center flex-shrink-0 animate-pulse">
                       <Bot size={20} className="text-slate-400" />
                    </div>
                    <div className="max-w-[80%] space-y-1">
                        <div className="text-xs text-slate-400 font-medium ml-1">
                            {initialPersonas.find(p => p.id === typingPersonaId)?.name} is typing...
                        </div>
                        <div className="p-4 rounded-2xl bg-white border border-slate-200 text-slate-800 rounded-tl-none shadow-sm">
                            {typingContent}
                            <span className="inline-block w-2 h-4 ml-1 bg-slate-400 animate-pulse align-middle" />
                        </div>
                    </div>
                </div>
            )}

            {/* Report Generation Indicator */}
            {isGeneratingReport && (
                <div className="my-6">
                    <div className="bg-gradient-to-r from-purple-50 to-pink-50 border-2 border-purple-200 rounded-xl p-6 shadow-lg animate-pulse">
                        <div className="flex items-center gap-2 mb-4 pb-3 border-b border-purple-200">
                            <FileText className="w-5 h-5 text-purple-600 animate-spin" />
                            <span className="font-bold text-purple-800">📝 レポート生成中...</span>
                        </div>
                        <div className="prose prose-sm max-w-none text-slate-700 whitespace-pre-wrap">
                            {reportContent}
                            <span className="inline-block w-2 h-4 ml-1 bg-purple-400 animate-pulse align-middle" />
                        </div>
                    </div>
                </div>
            )}
            
            <div ref={messagesEndRef} />
        </div>

        {/* Input Area */}
        <div className="p-4 bg-white border-t border-slate-200">
            <form onSubmit={handleInterrupt} className="relative">
                <input
                    type="text"
                    value={input}
                    onChange={(e) => setInput(e.target.value)}
                    placeholder="議論に割り込む..."
                    className="w-full p-4 pr-12 rounded-xl border border-slate-300 focus:ring-2 focus:ring-primary-500 focus:outline-none shadow-sm"
                    disabled={status !== "active"}
                />
                <button
                    type="submit"
                    disabled={status !== "active" || !input.trim()}
                    className="absolute right-3 top-1/2 -translate-y-1/2 p-2 text-primary-600 hover:bg-primary-50 rounded-lg disabled:text-slate-300 transition-colors"
                >
                    <Send size={20} />
                </button>
            </form>
            <p className="text-xs text-center text-slate-400 mt-2">
                いつでも発言して議論に介入できます
            </p>
        </div>
      </div>

      {/* Right Sidebar: Stats */}
      <div className="w-80 flex flex-col gap-6">
        <TokenUsageDisplay stats={tokenStats} personas={initialPersonas} />
        
        {/* Session Info */}
        <div className="bg-white p-4 rounded-xl shadow-sm border border-slate-200">
            <h3 className="font-semibold text-slate-700 mb-3 flex items-center gap-2">
                <AlertCircle className="w-4 h-4" />
                ステータス
            </h3>
            <div className="text-sm space-y-2 text-slate-600">
                <div className="flex justify-between">
                    <span>状態</span>
                    <span className={`font-medium ${status === 'active' ? 'text-green-600' : ''}`}>
                        {status}
                    </span>
                </div>
                <div className="flex justify-between">
                    <span>参加人数</span>
                    <span>{initialPersonas.length}名</span>
                </div>
                {errorMsg && (
                    <div className="p-2 bg-red-50 text-red-600 rounded text-xs mt-2">
                        {errorMsg}
                    </div>
                )}
            </div>
        </div>
      </div>
    </div>
  );
}

