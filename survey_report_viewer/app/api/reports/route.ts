import { NextResponse } from "next/server";
import fs from "fs";
import path from "path";

const OUTPUTS_DIR = path.join(process.cwd(), "..", "survey_analysis_pipeline", "outputs");

export async function GET() {
  try {
    // Check if outputs directory exists
    console.log("OUTPUTS_DIR:", OUTPUTS_DIR);
    console.log("exists:", fs.existsSync(OUTPUTS_DIR));
    
    if (!fs.existsSync(OUTPUTS_DIR)) {
      return NextResponse.json({ reports: [] });
    }

    const dirs = fs.readdirSync(OUTPUTS_DIR, { withFileTypes: true })
      .filter(dirent => dirent.isDirectory())
      .map(dirent => dirent.name);

    console.log("Found directories:", dirs);

    const reports = [];

    for (const dir of dirs) {
      const dataPath = path.join(OUTPUTS_DIR, dir, "analysis_data.json");
      
      if (fs.existsSync(dataPath)) {
        try {
          const data = JSON.parse(fs.readFileSync(dataPath, "utf-8"));
          reports.push({
            slug: dir,
            title: data.survey_title || dir,
            generated_at: data.generated_at 
              ? new Date(data.generated_at).toLocaleDateString("ja-JP")
              : "Unknown",
            response_count: data.response_count || 0,
          });
          console.log("Added report:", dir);
        } catch (e) {
          console.error("Error parsing", dir, e);
        }
      }
    }

    // Sort by generated_at (newest first) and prioritize non-backup
    reports.sort((a, b) => {
      // Prioritize non-backup reports
      const aIsBackup = a.slug.includes("backup");
      const bIsBackup = b.slug.includes("backup");
      if (!aIsBackup && bIsBackup) return -1;
      if (aIsBackup && !bIsBackup) return 1;
      return 0;
    });

    console.log("Total reports:", reports.length);
    return NextResponse.json({ reports });
  } catch (error) {
    console.error("Error reading reports:", error);
    return NextResponse.json({ reports: [], error: "Failed to read reports" }, { status: 500 });
  }
}

