import { NextResponse } from "next/server";

// Cache for 1 minute to avoid hitting rate limits
let cachedData: any = null;
let lastFetchTime = 0;
const CACHE_DURATION = 60 * 1000; // 1 minute

export async function GET() {
  const apiKey = process.env.OPENROUTER_API_KEY;
  
  if (!apiKey) {
    return NextResponse.json({ 
      error: "OpenRouter API key not configured",
      configured: false 
    }, { status: 400 });
  }

  const now = Date.now();
  if (cachedData && (now - lastFetchTime) < CACHE_DURATION) {
    return NextResponse.json({ ...cachedData, cached: true });
  }

  try {
    const response = await fetch("https://openrouter.ai/api/v1/auth/key", {
      headers: {
        "Authorization": `Bearer ${apiKey}`,
      },
      next: { revalidate: 0 } // No caching from Next.js side
    });

    if (!response.ok) {
      if (response.status === 401) {
         return NextResponse.json({ error: "Invalid API key" }, { status: 401 });
      }
      throw new Error(`OpenRouter API error: ${response.status}`);
    }

    const data = await response.json();
    
    // data.data structure:
    // {
    //   label: string
    //   usage: number (credits used)
    //   limit: number | null (credit limit, null if unlimited)
    //   is_free_tier: boolean
    //   rate_limit: { requests: number, interval: string }
    // }
    
    const result = {
      usage: data.data?.usage || 0,
      limit: data.data?.limit || null,
      // If limit exists, remaining is limit - usage. If no limit (prepaid/postpaid), it might be tricky.
      // For prepaid credits, typically 'limit' shows the total credits purchased? 
      // Actually OpenRouter API docs say:
      // "limit": Credit limit for the key. null if unlimited.
      // "usage": Credits used by the key.
      
      // For display purposes:
      remaining: data.data?.limit ? Math.max(0, data.data.limit - data.data.usage) : null,
      is_free_tier: data.data?.is_free_tier || false,
      label: data.data?.label,
      configured: true
    };

    cachedData = result;
    lastFetchTime = now;
    
    return NextResponse.json(result);
    
  } catch (error) {
    console.error("Failed to fetch OpenRouter credits:", error);
    return NextResponse.json({ error: String(error) }, { status: 500 });
  }
}

