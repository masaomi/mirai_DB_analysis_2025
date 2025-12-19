import { NextRequest, NextResponse } from "next/server";

export async function POST(req: NextRequest) {
  const RAG_SERVER_URL = process.env.RAG_SERVER_URL || "http://localhost:8001";

  try {
    const { session_id } = await req.json();

    const response = await fetch(`${RAG_SERVER_URL}/persona/stop?session_id=${session_id}`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
    });

    const data = await response.json();
    return NextResponse.json(data);
  } catch (error) {
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}
