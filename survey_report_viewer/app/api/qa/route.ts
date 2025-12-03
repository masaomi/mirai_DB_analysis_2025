import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";

const OUTPUTS_DIR = path.join(process.cwd(), "..", "survey_analysis_pipeline", "outputs");

// Simple in-memory search for now (can be replaced with ChromaDB)
async function searchRelevantContent(slug: string, query: string): Promise<string[]> {
  const reportDir = path.join(OUTPUTS_DIR, slug);
  const mdPath = path.join(reportDir, "report.md");
  
  if (!fs.existsSync(mdPath)) {
    return [];
  }
  
  const content = fs.readFileSync(mdPath, "utf-8");
  
  // Split into sections
  const sections = content.split(/(?=^## )/m);
  
  // Simple keyword matching
  const queryKeywords = query.toLowerCase().split(/\s+/);
  
  const scoredSections = sections.map(section => {
    const sectionLower = section.toLowerCase();
    let score = 0;
    for (const keyword of queryKeywords) {
      if (sectionLower.includes(keyword)) {
        score++;
      }
    }
    return { section, score };
  });
  
  // Sort by score and return top 3
  scoredSections.sort((a, b) => b.score - a.score);
  
  return scoredSections
    .filter(s => s.score > 0)
    .slice(0, 3)
    .map(s => s.section);
}

export async function POST(request: NextRequest) {
  try {
    const { slug, question } = await request.json();
    
    if (!slug || !question) {
      return NextResponse.json(
        { error: "Missing slug or question" },
        { status: 400 }
      );
    }
    
    // Search for relevant content
    const relevantContent = await searchRelevantContent(slug, question);
    
    if (relevantContent.length === 0) {
      return NextResponse.json({
        answer: "関連する情報が見つかりませんでした。別の質問をお試しください。",
        sources: [],
      });
    }
    
    // For now, return the most relevant section as context
    // In production, this would call an LLM with the context
    const context = relevantContent.join("\n\n---\n\n");
    
    // Simple response (replace with actual LLM call in production)
    const answer = `関連する情報：\n\n${relevantContent[0].substring(0, 500)}...`;
    
    return NextResponse.json({
      answer,
      sources: relevantContent.map((_, i) => `セクション ${i + 1}`),
      context: context.substring(0, 1000),
    });
  } catch (error) {
    console.error("Error in Q&A:", error);
    return NextResponse.json(
      { error: "Failed to process question" },
      { status: 500 }
    );
  }
}

