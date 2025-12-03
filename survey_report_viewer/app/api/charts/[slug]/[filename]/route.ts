import { NextRequest, NextResponse } from "next/server";
import fs from "fs";
import path from "path";

const OUTPUTS_DIR = path.join(process.cwd(), "..", "survey_analysis_pipeline", "outputs");

export async function GET(
  request: NextRequest,
  { params }: { params: Promise<{ slug: string; filename: string }> }
) {
  const { slug, filename } = await params;
  
  try {
    const chartPath = path.join(OUTPUTS_DIR, slug, "charts", filename);
    
    if (!fs.existsSync(chartPath)) {
      return NextResponse.json({ error: "Chart not found" }, { status: 404 });
    }

    const imageBuffer = fs.readFileSync(chartPath);
    
    return new NextResponse(imageBuffer, {
      headers: {
        "Content-Type": "image/png",
        "Cache-Control": "public, max-age=31536000",
      },
    });
  } catch (error) {
    console.error("Error reading chart:", error);
    return NextResponse.json({ error: "Failed to read chart" }, { status: 500 });
  }
}

