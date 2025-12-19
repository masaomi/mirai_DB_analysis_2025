import { NextRequest } from "next/server";

export async function GET(req: NextRequest) {
  const sessionId = req.nextUrl.searchParams.get("session_id");
  const RAG_SERVER_URL = process.env.RAG_SERVER_URL || "http://localhost:8001";

  if (!sessionId) {
    return new Response("Missing session_id", { status: 400 });
  }

  try {
    const response = await fetch(`${RAG_SERVER_URL}/persona/stream?session_id=${sessionId}`, {
      headers: {
        Accept: "text/event-stream",
      },
    });

    if (!response.ok) {
      return new Response(`Backend Error: ${response.statusText}`, { status: response.status });
    }

    return new Response(response.body, {
      headers: {
        "Content-Type": "text/event-stream",
        "Cache-Control": "no-cache",
        "Connection": "keep-alive",
      },
    });
  } catch (error) {
    return new Response(String(error), { status: 500 });
  }
}

