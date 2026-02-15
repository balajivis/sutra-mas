import { Pool, type QueryResultRow } from "pg";

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: { rejectUnauthorized: false },
  max: 5,
});

export async function query<T extends QueryResultRow = QueryResultRow>(
  sql: string,
  params?: unknown[]
): Promise<T[]> {
  const client = await pool.connect();
  try {
    const result = await client.query<T>(sql, params);
    return result.rows;
  } finally {
    client.release();
  }
}

export async function queryOne<T extends QueryResultRow = QueryResultRow>(
  sql: string,
  params?: unknown[]
): Promise<T | null> {
  const rows = await query<T>(sql, params);
  return rows[0] || null;
}

/** Run a read-only SQL query with safety checks. Returns rows or throws. */
export async function safeReadQuery(
  sql: string,
  params?: unknown[],
  timeoutMs = 5000
): Promise<QueryResultRow[]> {
  const trimmed = sql.trim().replace(/;+$/, "");
  const firstWord = trimmed.split(/\s/)[0]?.toUpperCase();
  if (firstWord !== "SELECT" && firstWord !== "WITH") {
    throw new Error("Only SELECT/WITH queries allowed");
  }
  const forbidden = [
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "CREATE",
    "TRUNCATE",
    "GRANT",
  ];
  const upper = trimmed.toUpperCase();
  for (const kw of forbidden) {
    if (new RegExp(`\\b${kw}\\b`).test(upper)) {
      throw new Error(`Query contains forbidden keyword: ${kw}`);
    }
  }

  const client = await pool.connect();
  try {
    await client.query(`SET statement_timeout = ${timeoutMs}`);
    const result = await client.query(trimmed);
    return result.rows;
  } finally {
    await client.query("RESET statement_timeout").catch(() => {});
    client.release();
  }
}

/** Ensure research desk tables exist (idempotent). */
let _tablesReady = false;
export async function ensureTables(): Promise<void> {
  if (_tablesReady) return;
  await query(`
    CREATE TABLE IF NOT EXISTS paper_clusters (
      paper_id INTEGER PRIMARY KEY,
      cluster_id INTEGER NOT NULL,
      cluster_label TEXT,
      x FLOAT NOT NULL,
      y FLOAT NOT NULL,
      updated_at TIMESTAMP DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS cluster_meta (
      cluster_id INTEGER PRIMARY KEY,
      label TEXT,
      description TEXT,
      paper_count INTEGER,
      top_concepts JSONB,
      top_patterns JSONB,
      updated_at TIMESTAMP DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS research_chat (
      id SERIAL PRIMARY KEY,
      question TEXT NOT NULL,
      answer TEXT NOT NULL,
      sql_used TEXT,
      sources JSONB,
      created_at TIMESTAMP DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS research_insights (
      id SERIAL PRIMARY KEY,
      type TEXT NOT NULL,
      title TEXT NOT NULL,
      content TEXT NOT NULL,
      evidence JSONB,
      paper_count INTEGER DEFAULT 0,
      status TEXT DEFAULT 'active',
      created_at TIMESTAMP DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS cluster_insights (
      cluster_id INTEGER PRIMARY KEY,
      insight TEXT NOT NULL,
      top_papers JSONB,
      created_at TIMESTAMP DEFAULT NOW()
    );
    CREATE TABLE IF NOT EXISTS citation_edges (
      citing_id INTEGER NOT NULL,
      cited_id INTEGER NOT NULL,
      PRIMARY KEY (citing_id, cited_id)
    );
    CREATE INDEX IF NOT EXISTS idx_citation_edges_cited ON citation_edges (cited_id);
    CREATE TABLE IF NOT EXISTS reinvention_edges (
      modern_id INTEGER NOT NULL,
      classical_id INTEGER NOT NULL,
      overlap_concepts JSONB,
      has_citation BOOLEAN DEFAULT FALSE,
      overlap_score FLOAT DEFAULT 0,
      PRIMARY KEY (modern_id, classical_id)
    );
  `);
  _tablesReady = true;
}

export { pool };
