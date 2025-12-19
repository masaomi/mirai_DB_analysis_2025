import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";

const OUTPUTS_DIR = path.join(process.cwd(), "..", "survey_analysis_pipeline", "outputs");

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ slug: string }> }
) {
  const { slug } = await params;
  
  try {
    const reportDir = path.join(OUTPUTS_DIR, slug);
    
    if (!fs.existsSync(reportDir)) {
      return NextResponse.json({ error: "Report not found" }, { status: 404 });
    }

    // Read report markdown (try .md first, then generate from analysis_data)
    const mdPath = path.join(reportDir, "report.md");
    let markdown = "";
    
    if (fs.existsSync(mdPath)) {
      markdown = fs.readFileSync(mdPath, "utf-8");
    }

    // Read analysis data
    const dataPath = path.join(reportDir, "analysis_data.json");
    let analysisData: any = {};
    if (fs.existsSync(dataPath)) {
      analysisData = JSON.parse(fs.readFileSync(dataPath, "utf-8"));
    }

    // If no markdown, generate a basic one from analysis data
    if (!markdown && analysisData.survey_title) {
      markdown = generateMarkdownFromAnalysis(analysisData);
    }

    // Get chart paths
    const chartsDir = path.join(reportDir, "charts");
    const charts: string[] = [];
    if (fs.existsSync(chartsDir)) {
      const files = fs.readdirSync(chartsDir);
      for (const file of files) {
        if (file.endsWith(".png")) {
          charts.push(`/api/charts/${slug}/${file}`);
        }
      }
    }

    return NextResponse.json({
      slug,
      markdown,
      analysisData,
      charts,
    });
  } catch (error) {
    console.error("Error reading report:", error);
    return NextResponse.json({ error: "Failed to read report" }, { status: 500 });
  }
}

// Generate markdown from analysis data when report.md doesn't exist
function generateMarkdownFromAnalysis(data: any): string {
  let md = `# ${data.survey_title || "分析レポート"}\n\n`;
  md += `**回答数:** ${data.response_count || 0}件\n`;
  md += `**生成日時:** ${data.generated_at ? new Date(data.generated_at).toLocaleString("ja-JP") : "不明"}\n\n`;

  // Stance distribution
  if (data.stance_distribution) {
    md += `## 立場分布\n\n`;
    for (const [stance, info] of Object.entries(data.stance_distribution as Record<string, any>)) {
      md += `- **${stance}**: ${info.count}件 (${info.percentage?.toFixed(1)}%)\n`;
    }
    md += "\n";
  }

  // Cluster summary
  if (data.cluster_details && data.cluster_details.length > 0) {
    md += `## 主要な意見グループ\n\n`;
    const topClusters = data.cluster_details
      .filter((c: any) => c.cluster_id !== -1 && c.included_in_report)
      .slice(0, 10);
    
    for (const cluster of topClusters) {
      md += `### ${cluster.label} (${cluster.size}件)\n`;
      if (cluster.keywords && cluster.keywords.length > 0) {
        md += `キーワード: ${cluster.keywords.slice(0, 5).join(", ")}\n\n`;
      }
      if (cluster.sample_responses && cluster.sample_responses.length > 0) {
        md += `**代表的な意見:**\n`;
        for (const resp of cluster.sample_responses.slice(0, 2)) {
          md += `> ${resp}\n\n`;
        }
      }
    }
  }

  // Minority opinions
  if (data.minority_opinions && data.minority_opinions.length > 0) {
    md += `## 特徴的な少数意見\n\n`;
    for (const opinion of data.minority_opinions.slice(0, 5)) {
      md += `- **${opinion.uniqueness_reason}**: "${opinion.content}"\n`;
    }
  }

  return md;
}

