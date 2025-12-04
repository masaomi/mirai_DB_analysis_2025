import { NextRequest } from "next/server";
import fs from "fs";
import path from "path";
import { createOpenAI } from "@ai-sdk/openai";
import { createAmazonBedrock } from "@ai-sdk/amazon-bedrock";
import { streamText, Message } from "ai";

// Configure response timeout (5 minutes)
export const maxDuration = 300;

const OUTPUTS_DIR = path.join(process.cwd(), "..", "survey_analysis_pipeline", "outputs");

// Interface for analysis data
interface AnalysisData {
  survey_slug: string;
  survey_title: string;
  response_count: number;
  stance_distribution: Record<string, { count: number; percentage: number }>;
  cluster_details: Array<{
    cluster_id: number;
    label: string;
    size: number;
    keywords: string[];
    sample_responses: string[];
  }>;
  minority_opinions: Array<{
    content: string;
    outlier_score: number;
    uniqueness_reason: string;
  }>;
}

// Helper to load analysis data
function loadAnalysisData(slug: string): AnalysisData | null {
  try {
    const dataPath = path.join(OUTPUTS_DIR, slug, "analysis_data.json");
    if (!fs.existsSync(dataPath)) return null;
    const data = fs.readFileSync(dataPath, "utf-8");
    return JSON.parse(data);
  } catch (error) {
    console.error("Error loading analysis data:", error);
    return null;
  }
}

// Helper to load report content
function loadReportContent(slug: string): string {
  try {
    const reportPath = path.join(OUTPUTS_DIR, slug, "report.md");
    if (!fs.existsSync(reportPath)) return "";
    return fs.readFileSync(reportPath, "utf-8");
  } catch (error) {
    console.error("Error loading report:", error);
    return "";
  }
}

// Helper to create structured context
function createStructuredContext(data: AnalysisData, report: string, query: string): string {
  // 1. Basic Info
  let context = `## アンケート概要
タイトル: ${data.survey_title}
回答数: ${data.response_count}件

## 立場分布
`;

  // 2. Stance Distribution
  Object.entries(data.stance_distribution).forEach(([stance, info]) => {
    context += `- ${stance}: ${info.count}件 (${info.percentage.toFixed(1)}%)\n`;
  });

  // 3. Top Clusters (Limit to top 10 to save tokens)
  context += `\n## 主要な意見グループ (トップ10)\n`;
  data.cluster_details
    .filter(c => c.cluster_id !== -1) // Exclude noise
    .slice(0, 10)
    .forEach(c => {
      context += `- ${c.label} (${c.size}件): ${c.keywords.slice(0, 3).join(", ")}\n`;
    });

  // 4. Minority Opinions (Limit to top 3)
  context += `\n## 特徴的な少数意見\n`;
  data.minority_opinions.slice(0, 3).forEach((m, i) => {
    context += `${i + 1}. ${m.uniqueness_reason}: 「${m.content.substring(0, 50)}...」\n`;
  });

  // 5. Relevant Report Sections (Simple keyword matching)
  const keywords = query.split(/\s+/).filter(k => k.length > 1);
  if (keywords.length > 0) {
    const sections = report.split(/^## /m);
    const relevantSections = sections.filter(s => 
      keywords.some(k => s.includes(k))
    );
    
    if (relevantSections.length > 0) {
      context += `\n## 関連するレポート記述\n`;
      context += relevantSections.slice(0, 2).join("\n").substring(0, 1000);
    }
  }

  return context;
}

export async function POST(req: NextRequest) {
  try {
    const { messages, slug } = await req.json();
    const lastMessage = messages[messages.length - 1];
    const query = lastMessage.content;

    // 1. Load Data
    const analysisData = loadAnalysisData(slug);
    if (!analysisData) {
      return new Response("Analysis data not found", { status: 404 });
    }
    const reportContent = loadReportContent(slug);

    // 2. Create Context
    const context = createStructuredContext(analysisData, reportContent, query);

    // 3. Initialize LLM Provider
    const provider = process.env.LLM_PROVIDER || "ollama";
    let model;

    if (provider === "ollama") {
      const openai = createOpenAI({
        baseURL: process.env.OLLAMA_BASE_URL || "http://localhost:11434/v1",
        apiKey: "ollama", // required but unused
      });
      model = openai(process.env.OLLAMA_MODEL || "gpt-oss:20b");
    } else if (provider === "bedrock") {
      const bedrock = createAmazonBedrock({
        region: process.env.AWS_REGION || "us-east-1",
        accessKeyId: process.env.AWS_ACCESS_KEY_ID,
        secretAccessKey: process.env.AWS_SECRET_ACCESS_KEY,
      });
      model = bedrock(process.env.BEDROCK_MODEL_ID || "anthropic.claude-3-5-sonnet-20241022-v2:0");
    } else if (provider === "openrouter") {
      const openai = createOpenAI({
        baseURL: "https://openrouter.ai/api/v1",
        apiKey: process.env.OPENROUTER_API_KEY,
      });
      model = openai(process.env.OPENROUTER_MODEL || "anthropic/claude-3.5-sonnet");
    } else {
      throw new Error(`Unsupported provider: ${provider}`);
    }

    // 4. Create System Prompt
    const systemPrompt = `あなたはアンケート分析アシスタントです。
以下の分析データに基づいて、ユーザーの質問に答えてください。

制約事項:
- 提供されたデータに基づいて事実のみを答えてください。
- データにないことは「データに含まれていません」と答えてください。
- 簡潔かつ客観的に答えてください。
- 日本語で答えてください。

=== 分析データ ===
${context}
==================
`;

    // 5. Stream Response
    const result = await streamText({
      model,
      messages: [
        { role: "system", content: systemPrompt },
        ...messages,
      ],
    });

    return result.toDataStreamResponse();

  } catch (error) {
    console.error("Error in Q&A:", error);
    return new Response(
      JSON.stringify({ error: "Failed to process request", details: String(error) }), 
      { status: 500, headers: { "Content-Type": "application/json" } }
    );
  }
}
