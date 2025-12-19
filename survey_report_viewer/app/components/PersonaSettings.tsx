"use client";

import { useState, useEffect } from "react";
import { Users, Play, Settings, Plus, Trash2, ChevronDown, ChevronUp, Copy } from "lucide-react";

export interface PersonaConfig {
  id: string;
  name: string;
  description: string;
  model: string;
  system_prompt: string;
  avatar?: string;
  color?: string;
  enabled: boolean;
}

export interface DiscussionSettings {
  personas: PersonaConfig[];
  facilitator_id: string;
  topic: string;
  context: string;
  slug?: string;
  max_rounds: number;
  max_time_minutes: number;
  max_tokens: number;
}

interface ModelInfo {
  id: string;
  name: string;
  provider: string;
  context_length?: number;
}

// Predefined persona templates
const PERSONA_TEMPLATES: Omit<PersonaConfig, "model" | "enabled">[] = [
  {
    id: "policy_maker",
    name: "政策立案者",
    description: "政策の実現可能性と予算・制度の観点から分析",
    system_prompt: "あなたは政策立案者です。予算、法的整合性、実現までのロードマップを重視します。具体的な実装案や制度設計について提案してください。",
    color: "bg-blue-50 text-blue-700 border-blue-200",
  },
  {
    id: "citizen",
    name: "一般市民代表",
    description: "生活者の視点、分かりやすさ、公平性を重視",
    system_prompt: "あなたは一般市民の代表です。生活への影響、分かりやすさ、公平性を重視します。専門用語を避け、市民目線で意見を述べてください。",
    color: "bg-green-50 text-green-700 border-green-200",
  },
  {
    id: "expert",
    name: "技術専門家",
    description: "技術的実現性、セキュリティ、運用課題を指摘",
    system_prompt: "あなたは技術専門家です。技術的な実現可能性、セキュリティリスク、運用上の課題を指摘します。具体的な技術的根拠を示してください。",
    color: "bg-purple-50 text-purple-700 border-purple-200",
  },
  {
    id: "minority",
    name: "少数派の代弁者",
    description: "見落とされがちな意見や特定のグループへの配慮を主張",
    system_prompt: "あなたは少数派の代弁者です。多数決では埋もれてしまう意見や、特定のグループへの配慮を強く主張します。多様性と包摂性の観点から意見を述べてください。",
    color: "bg-orange-50 text-orange-700 border-orange-200",
  },
  {
    id: "critic",
    name: "批判的研究者",
    description: "潜在的なリスク、長期的な副作用、データのバイアスを指摘",
    system_prompt: "あなたは批判的な研究者です。安易な合意に流されず、リスクや長期的な副作用、データのバイアスを鋭く指摘します。エビデンスに基づいた批判を行ってください。",
    color: "bg-red-50 text-red-700 border-red-200",
  },
  {
    id: "economist",
    name: "経済専門家",
    description: "費用対効果、経済波及効果、市場原理を重視",
    system_prompt: "あなたは経済専門家です。費用対効果（ROI）、経済波及効果、市場へのインパクトを重視します。数値やデータに基づいた分析を行ってください。",
    color: "bg-yellow-50 text-yellow-700 border-yellow-200",
  },
];

interface Props {
  onStart: (settings: DiscussionSettings) => void;
  isLoading: boolean;
  initialTopic?: string;
  initialContext?: string;
  initialSlug?: string;
}

export default function PersonaSettings({ onStart, isLoading, initialTopic, initialContext, initialSlug }: Props) {
  // Model list from API
  const [availableModels, setAvailableModels] = useState<ModelInfo[]>([]);
  const [modelsLoading, setModelsLoading] = useState(true);

  // Active personas (can have multiple of same template with different models)
  const [activePersonas, setActivePersonas] = useState<PersonaConfig[]>([]);
  
  // Settings
  const [facilitatorId, setFacilitatorId] = useState("");
  const [topic, setTopic] = useState(initialTopic || "");
  const [context, setContext] = useState(initialContext || "");
  const [maxRounds, setMaxRounds] = useState(5);
  const [maxTimeMinutes, setMaxTimeMinutes] = useState(30);
  const [maxTokens, setMaxTokens] = useState(50000);
  
  // UI state
  const [showTemplates, setShowTemplates] = useState(true);
  const [showCustomForm, setShowCustomForm] = useState(false);
  const [customPersona, setCustomPersona] = useState({
    name: "",
    description: "",
    system_prompt: "",
  });

  // Fetch available models
  useEffect(() => {
    fetch("/api/models")
      .then(res => res.json())
      .then(data => {
        setAvailableModels(data.models || []);
        setModelsLoading(false);
      })
      .catch(err => {
        console.error("Failed to load models:", err);
        setModelsLoading(false);
      });
  }, []);

  // Update topic when initialTopic changes
  useEffect(() => {
    if (initialTopic) {
      setTopic(initialTopic);
    }
  }, [initialTopic]);

  // Update context when initialContext changes
  useEffect(() => {
    if (initialContext) {
      setContext(initialContext);
    }
  }, [initialContext]);

  // Add persona from template
  const addPersonaFromTemplate = (template: Omit<PersonaConfig, "model" | "enabled">) => {
    const defaultModel = availableModels[0]?.id || "anthropic/claude-3.5-sonnet";
    const instanceId = `${template.id}_${Date.now()}`;
    
    const newPersona: PersonaConfig = {
      ...template,
      id: instanceId,
      model: defaultModel,
      enabled: true,
    };
    
    setActivePersonas(prev => [...prev, newPersona]);
    
    // Set as facilitator if first persona
    if (activePersonas.length === 0) {
      setFacilitatorId(instanceId);
    }
  };

  // Add custom persona
  const addCustomPersona = () => {
    if (!customPersona.name || !customPersona.system_prompt) {
      alert("名前とシステムプロンプトは必須です");
      return;
    }

    const defaultModel = availableModels[0]?.id || "anthropic/claude-3.5-sonnet";
    const instanceId = `custom_${Date.now()}`;
    
    const newPersona: PersonaConfig = {
      id: instanceId,
      name: customPersona.name,
      description: customPersona.description,
      system_prompt: customPersona.system_prompt,
      model: defaultModel,
      color: "bg-slate-50 text-slate-700 border-slate-200",
      enabled: true,
    };
    
    setActivePersonas(prev => [...prev, newPersona]);
    setShowCustomForm(false);
    setCustomPersona({ name: "", description: "", system_prompt: "" });

    if (activePersonas.length === 0) {
      setFacilitatorId(instanceId);
    }
  };

  // Remove persona
  const removePersona = (id: string) => {
    setActivePersonas(prev => prev.filter(p => p.id !== id));
    if (facilitatorId === id) {
      const remaining = activePersonas.filter(p => p.id !== id);
      setFacilitatorId(remaining[0]?.id || "");
    }
  };

  // Update persona model
  const updatePersonaModel = (id: string, model: string) => {
    setActivePersonas(prev => prev.map(p => p.id === id ? { ...p, model } : p));
  };

  // Duplicate persona (same template, different model)
  const duplicatePersona = (persona: PersonaConfig) => {
    const instanceId = `${persona.id.split("_")[0]}_${Date.now()}`;
    const newPersona: PersonaConfig = {
      ...persona,
      id: instanceId,
    };
    setActivePersonas(prev => [...prev, newPersona]);
  };

  // Group models by provider
  const modelsByProvider = availableModels.reduce((acc, model) => {
    if (!acc[model.provider]) acc[model.provider] = [];
    acc[model.provider].push(model);
    return acc;
  }, {} as Record<string, ModelInfo[]>);

  const handleStart = () => {
    if (activePersonas.length < 2) {
      alert("少なくとも2人のペルソナを追加してください");
      return;
    }
    
    if (!facilitatorId || !activePersonas.find(p => p.id === facilitatorId)) {
      alert("ファシリテーターを選択してください");
      return;
    }

    if (!topic.trim()) {
      alert("議論のテーマを入力してください");
      return;
    }

    onStart({
      personas: activePersonas,
      facilitator_id: facilitatorId,
      topic,
      context,
      slug: initialSlug,
      max_rounds: maxRounds,
      max_time_minutes: maxTimeMinutes,
      max_tokens: maxTokens,
    });
  };

  return (
    <div className="space-y-6">
      {/* Topic Section */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-bold text-slate-800 mb-4 flex items-center gap-2">
          <Settings className="w-5 h-5" />
          議論のテーマ
        </h2>
        <input
          type="text"
          className="w-full p-3 border border-slate-300 rounded-lg focus:ring-2 focus:ring-primary-500 focus:outline-none"
          value={topic}
          onChange={(e) => setTopic(e.target.value)}
          placeholder="議論したいテーマを入力してください"
        />
        {initialTopic && (
          <p className="text-xs text-slate-500 mt-2">
            ※ レポートのタイトルから自動設定されています
          </p>
        )}
      </div>

      {/* Persona Templates */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 overflow-hidden">
        <button
          onClick={() => setShowTemplates(!showTemplates)}
          className="w-full p-4 flex justify-between items-center bg-slate-50 hover:bg-slate-100 transition-colors"
        >
          <h2 className="text-lg font-bold text-slate-800 flex items-center gap-2">
            <Users className="w-5 h-5" />
            ペルソナテンプレート
          </h2>
          {showTemplates ? <ChevronUp size={20} /> : <ChevronDown size={20} />}
        </button>
        
        {showTemplates && (
          <div className="p-4 grid gap-3 md:grid-cols-2 lg:grid-cols-3">
            {PERSONA_TEMPLATES.map((template) => (
              <button
                key={template.id}
                onClick={() => addPersonaFromTemplate(template)}
                className={`p-4 rounded-lg border-2 border-dashed text-left hover:border-solid hover:shadow-sm transition-all ${template.color}`}
              >
                <div className="font-semibold mb-1">{template.name}</div>
                <div className="text-xs opacity-80">{template.description}</div>
                <div className="mt-2 text-xs flex items-center gap-1">
                  <Plus size={12} /> クリックで追加
                </div>
              </button>
            ))}
            
            {/* Custom Persona Button */}
            <button
              onClick={() => setShowCustomForm(true)}
              className="p-4 rounded-lg border-2 border-dashed border-slate-300 text-left hover:border-solid hover:border-slate-400 hover:bg-slate-50 transition-all"
            >
              <div className="font-semibold mb-1 text-slate-700">+ オリジナルペルソナ</div>
              <div className="text-xs text-slate-500">カスタムペルソナを作成</div>
            </button>
          </div>
        )}
      </div>

      {/* Custom Persona Form */}
      {showCustomForm && (
        <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
          <h3 className="font-bold text-slate-800 mb-4">オリジナルペルソナを作成</h3>
          <div className="space-y-4">
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">名前 *</label>
              <input
                type="text"
                className="w-full p-2 border rounded"
                value={customPersona.name}
                onChange={(e) => setCustomPersona(prev => ({ ...prev, name: e.target.value }))}
                placeholder="例: 法律専門家"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">説明</label>
              <input
                type="text"
                className="w-full p-2 border rounded"
                value={customPersona.description}
                onChange={(e) => setCustomPersona(prev => ({ ...prev, description: e.target.value }))}
                placeholder="例: 法的観点から議論を分析"
              />
            </div>
            <div>
              <label className="block text-sm font-medium text-slate-700 mb-1">システムプロンプト *</label>
              <textarea
                className="w-full p-2 border rounded h-24"
                value={customPersona.system_prompt}
                onChange={(e) => setCustomPersona(prev => ({ ...prev, system_prompt: e.target.value }))}
                placeholder="このペルソナの役割や視点を説明してください..."
              />
            </div>
            <div className="flex gap-2">
              <button
                onClick={addCustomPersona}
                className="px-4 py-2 bg-primary-600 text-white rounded hover:bg-primary-700"
              >
                追加
              </button>
              <button
                onClick={() => setShowCustomForm(false)}
                className="px-4 py-2 bg-slate-200 text-slate-700 rounded hover:bg-slate-300"
              >
                キャンセル
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Active Personas */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <div className="flex justify-between items-center mb-4">
          <h2 className="text-lg font-bold text-slate-800">
            参加ペルソナ ({activePersonas.length}名)
          </h2>
        </div>
        
        {activePersonas.length === 0 ? (
          <div className="text-center py-8 text-slate-500">
            上のテンプレートからペルソナを追加してください
          </div>
        ) : (
          <div className="space-y-4">
            {activePersonas.map((persona) => (
              <div 
                key={persona.id}
                className={`border rounded-lg p-4 ${persona.color || "border-slate-200"}`}
              >
                <div className="flex items-start justify-between gap-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-2 mb-2">
                      <span className="font-semibold">{persona.name}</span>
                      {persona.id.startsWith("custom_") && (
                        <span className="text-[10px] bg-slate-200 px-2 py-0.5 rounded-full">カスタム</span>
                      )}
                    </div>
                    <p className="text-sm text-slate-600 mb-3">{persona.description}</p>
                    
                    {/* Model Selection */}
                    <div className="flex flex-wrap items-center gap-2">
                      <label className="text-xs text-slate-500">LLM:</label>
                      <select
                        value={persona.model}
                        onChange={(e) => updatePersonaModel(persona.id, e.target.value)}
                        className="text-sm p-1.5 border rounded bg-white min-w-[200px]"
                        disabled={modelsLoading}
                      >
                        {Object.entries(modelsByProvider).map(([provider, models]) => (
                          <optgroup key={provider} label={provider}>
                            {models.map(m => (
                              <option key={m.id} value={m.id}>{m.name}</option>
                            ))}
                          </optgroup>
                        ))}
                      </select>
                      
                      {/* Facilitator Selection */}
                      <label className="flex items-center gap-1 text-xs ml-2 cursor-pointer">
                        <input
                          type="radio"
                          name="facilitator"
                          checked={facilitatorId === persona.id}
                          onChange={() => setFacilitatorId(persona.id)}
                          className="text-primary-600"
                        />
                        <span className={facilitatorId === persona.id ? "font-semibold text-primary-600" : ""}>
                          ファシリテーター
                        </span>
                      </label>
                    </div>
                  </div>
                  
                  {/* Actions */}
                  <div className="flex gap-1">
                    <button
                      onClick={() => duplicatePersona(persona)}
                      className="p-1.5 text-slate-400 hover:text-slate-600 hover:bg-slate-100 rounded"
                      title="複製"
                    >
                      <Copy size={16} />
                    </button>
                    <button
                      onClick={() => removePersona(persona.id)}
                      className="p-1.5 text-red-400 hover:text-red-600 hover:bg-red-50 rounded"
                      title="削除"
                    >
                      <Trash2 size={16} />
                    </button>
                  </div>
                </div>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* End Conditions */}
      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6">
        <h2 className="text-lg font-bold text-slate-800 mb-4">終了条件</h2>
        <p className="text-sm text-slate-500 mb-4">いずれかの条件に達した時点でディスカッションが終了します</p>
        
        <div className="grid gap-4 md:grid-cols-3">
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              最大ラウンド数
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={1}
                max={50}
                value={maxRounds}
                onChange={(e) => setMaxRounds(parseInt(e.target.value) || 5)}
                className="w-full p-2 border rounded"
              />
              <span className="text-sm text-slate-500">ラウンド</span>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              最大時間
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={1}
                max={120}
                value={maxTimeMinutes}
                onChange={(e) => setMaxTimeMinutes(parseInt(e.target.value) || 30)}
                className="w-full p-2 border rounded"
              />
              <span className="text-sm text-slate-500">分</span>
            </div>
          </div>
          
          <div>
            <label className="block text-sm font-medium text-slate-700 mb-1">
              最大トークン数
            </label>
            <div className="flex items-center gap-2">
              <input
                type="number"
                min={1000}
                max={500000}
                step={1000}
                value={maxTokens}
                onChange={(e) => setMaxTokens(parseInt(e.target.value) || 50000)}
                className="w-full p-2 border rounded"
              />
              <span className="text-sm text-slate-500">tokens</span>
            </div>
          </div>
        </div>
      </div>

      {/* Context (collapsible) */}
      <details className="bg-white rounded-xl shadow-sm border border-slate-200">
        <summary className="p-4 cursor-pointer font-semibold text-slate-700 hover:bg-slate-50">
          背景コンテキスト（詳細設定）
        </summary>
        <div className="p-4 pt-0">
          <textarea
            value={context}
            onChange={(e) => setContext(e.target.value)}
            placeholder="レポートの内容や前提条件など..."
            className="w-full p-3 border rounded-lg h-32"
          />
          {initialContext && (
            <p className="text-xs text-slate-500 mt-2">
              ※ レポートの内容が自動設定されています
            </p>
          )}
        </div>
      </details>

      {/* Start Button */}
      <div className="flex justify-end">
        <button
          onClick={handleStart}
          disabled={isLoading || activePersonas.length < 2}
          className="flex items-center gap-2 px-8 py-3 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:bg-slate-400 disabled:cursor-not-allowed transition-colors font-medium shadow-sm"
        >
          {isLoading ? (
            <>
              <div className="w-5 h-5 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
              準備中...
            </>
          ) : (
            <>
              <Play className="w-5 h-5" />
              ディスカッションを開始 ({activePersonas.length}名)
            </>
          )}
        </button>
      </div>
    </div>
  );
}


