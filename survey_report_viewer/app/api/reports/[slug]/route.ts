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

    // Read report markdown
    const mdPath = path.join(reportDir, "report.md");
    let markdown = "";
    if (fs.existsSync(mdPath)) {
      markdown = fs.readFileSync(mdPath, "utf-8");
    }

    // Read analysis data
    const dataPath = path.join(reportDir, "analysis_data.json");
    let analysisData = {};
    if (fs.existsSync(dataPath)) {
      analysisData = JSON.parse(fs.readFileSync(dataPath, "utf-8"));
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

