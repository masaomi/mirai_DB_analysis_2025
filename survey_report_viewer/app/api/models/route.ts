import { NextRequest, NextResponse } from "next/server";

// Cache models for 5 minutes
let cachedModels: any[] = [];
let cacheTime = 0;
const CACHE_DURATION = 5 * 60 * 1000; // 5 minutes

// Recommended models to prioritize (shown at top of list)
const RECOMMENDED_MODELS = [
  // Anthropic
  { id: "anthropic/claude-opus-4.5", name: "Claude Opus 4.5", provider: "anthropic", recommended: true },
  { id: "anthropic/claude-sonnet-4.5", name: "Claude Sonnet 4.5", provider: "anthropic", recommended: true },
  { id: "anthropic/claude-opus-4", name: "Claude Opus 4", provider: "anthropic", recommended: true },
  { id: "anthropic/claude-sonnet-4", name: "Claude Sonnet 4", provider: "anthropic", recommended: true },
  { id: "anthropic/claude-3.5-sonnet", name: "Claude 3.5 Sonnet", provider: "anthropic", recommended: true },
  { id: "anthropic/claude-3-opus", name: "Claude 3 Opus", provider: "anthropic", recommended: true },
  // Google Gemini
  { id: "google/gemini-3-pro-preview", name: "Gemini 3 Pro Preview", provider: "google", recommended: true },
  { id: "google/gemini-3-flash-preview", name: "Gemini 3 Flash Preview", provider: "google", recommended: true },
  { id: "google/gemini-2.5-pro-preview", name: "Gemini 2.5 Pro", provider: "google", recommended: true },
  { id: "google/gemini-2.0-flash-001", name: "Gemini 2.0 Flash", provider: "google", recommended: true },
  // OpenAI GPT-5.2 series
  { id: "openai/gpt-5.2-pro", name: "GPT-5.2 Pro", provider: "openai", recommended: true },
  { id: "openai/gpt-5.2", name: "GPT-5.2", provider: "openai", recommended: true },
  { id: "openai/gpt-5.2-chat", name: "GPT-5.2 Chat", provider: "openai", recommended: true },
  // OpenAI others
  { id: "openai/gpt-4o", name: "GPT-4o", provider: "openai", recommended: true },
  { id: "openai/o1-preview", name: "O1 Preview", provider: "openai", recommended: true },
  { id: "openai/o3-mini", name: "O3 Mini", provider: "openai", recommended: true },
  // Meta
  { id: "meta-llama/llama-3.3-70b-instruct", name: "Llama 3.3 70B", provider: "meta-llama", recommended: true },
];

// Local Ollama models
const OLLAMA_MODELS = [
  { id: "ollama/llama3.2", name: "Llama 3.2 (Local)", provider: "Ollama", local: true },
  { id: "ollama/qwen2.5:14b", name: "Qwen 2.5 14B (Local)", provider: "Ollama", local: true },
  { id: "ollama/gemma2:9b", name: "Gemma 2 9B (Local)", provider: "Ollama", local: true },
];

export async function GET(req: NextRequest) {
  const now = Date.now();
  
  // Return cached if available
  if (cachedModels.length > 0 && (now - cacheTime) < CACHE_DURATION) {
    return NextResponse.json({ models: cachedModels });
  }

  const apiKey = process.env.OPENROUTER_API_KEY;
  
  if (!apiKey) {
    // Return fallback models if no API key (recommended + ollama)
    return NextResponse.json({
      models: [...OLLAMA_MODELS, ...RECOMMENDED_MODELS],
      source: "fallback"
    });
  }

  try {
    const response = await fetch("https://openrouter.ai/api/v1/models", {
      headers: {
        "Authorization": `Bearer ${apiKey}`,
      },
    });

    if (!response.ok) {
      throw new Error(`OpenRouter API error: ${response.status}`);
    }

    const data = await response.json();
    
    // Get all model IDs from API
    const apiModelIds = new Set(data.data.map((m: any) => m.id));
    
    // Format all models from API (no filtering - show everything)
    const apiModels = data.data
      .filter((m: any) => m.id)
      .map((m: any) => ({
        id: m.id,
        name: m.name || m.id,
        provider: m.id.split("/")[0],
        context_length: m.context_length,
        pricing: m.pricing,
        recommended: RECOMMENDED_MODELS.some(r => r.id === m.id),
      }));
    
    // Add recommended models that might not be in API response
    const missingRecommended = RECOMMENDED_MODELS.filter(r => !apiModelIds.has(r.id));
    
    // Sort: Ollama first, then recommended, then by provider
    const allModels = [...OLLAMA_MODELS, ...missingRecommended, ...apiModels];
    
    // Sort function: local first, then recommended, then alphabetically by provider
    allModels.sort((a: any, b: any) => {
      if (a.local && !b.local) return -1;
      if (!a.local && b.local) return 1;
      if (a.recommended && !b.recommended) return -1;
      if (!a.recommended && b.recommended) return 1;
      return a.provider.localeCompare(b.provider);
    });

    cachedModels = allModels;
    cacheTime = now;

    return NextResponse.json({ 
      models: cachedModels,
      source: "openrouter",
      total: cachedModels.length
    });

  } catch (error) {
    console.error("Failed to fetch OpenRouter models:", error);
    
    // Return fallback on error
    return NextResponse.json({
      models: [...OLLAMA_MODELS, ...RECOMMENDED_MODELS],
      source: "fallback",
      error: String(error)
    });
  }
}

