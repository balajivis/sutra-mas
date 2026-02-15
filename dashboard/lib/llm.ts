import OpenAI from "openai";

function getClient(model: string): OpenAI {
  const endpoint = process.env.AZURE_OPENAI_ENDPOINT!;
  const apiKey = process.env.AZURE_OPENAI_API_KEY!;

  return new OpenAI({
    apiKey,
    baseURL: `${endpoint}/openai/deployments/${model}`,
    defaultQuery: { "api-version": "2025-01-01-preview" },
    defaultHeaders: { "api-key": apiKey },
  });
}

export async function chatCompletion(
  system: string,
  user: string,
  options?: { model?: string; maxTokens?: number; temperature?: number }
): Promise<string> {
  const model =
    options?.model || process.env.AZURE_OPENAI_CHAT_MODEL || "gpt-5-mini";
  const client = getClient(model);

  const response = await client.chat.completions.create({
    model,
    messages: [
      { role: "system", content: system },
      { role: "user", content: user },
    ],
    max_completion_tokens: options?.maxTokens || 2048,
    temperature: options?.temperature ?? 1,
  });

  return response.choices[0]?.message?.content || "";
}

export async function chatJSON<T = Record<string, unknown>>(
  system: string,
  user: string,
  options?: { model?: string; maxTokens?: number }
): Promise<T> {
  const text = await chatCompletion(system, user, options);

  let jsonStr = text;
  if (text.includes("```json")) {
    const start = text.indexOf("```json") + 7;
    const end = text.indexOf("```", start);
    jsonStr = text.substring(start, end).trim();
  } else if (text.includes("```")) {
    const start = text.indexOf("```") + 3;
    const end = text.indexOf("```", start);
    jsonStr = text.substring(start, end).trim();
  }

  return JSON.parse(jsonStr);
}

export async function embed(texts: string[]): Promise<number[][]> {
  const model =
    process.env.AZURE_OPENAI_EMBED_MODEL || "text-embedding-3-small";
  const client = getClient(model);

  const response = await client.embeddings.create({ model, input: texts });
  return response.data.map((d) => d.embedding);
}
