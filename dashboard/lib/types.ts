export interface ClusterPoint {
  paper_id: number;
  cluster_id: number;
  cluster_label: string | null;
  x: number;
  y: number;
  title: string;
  year: number | null;
  citations: number;
  is_classical: boolean;
  pattern: string | null;
  grounding: string | null;
}

export interface ClusterMeta {
  cluster_id: number;
  label: string;
  description: string | null;
  paper_count: number;
  top_concepts: string[] | null;
  top_patterns: string[] | null;
}

export interface ChatSource {
  id: number;
  title: string;
  year: number | null;
  citations: number;
  pattern: string;
  summary: string;
  classical: boolean;
  link: string;
  score: number;
}

export interface ChatMessage {
  id?: number;
  question: string;
  answer: string;
  sources?: ChatSource[];
  total?: number;
  timestamp?: string;
}

export interface Insight {
  type: string;
  title: string;
  content?: string;
  data: Record<string, unknown>[];
  count: number;
  error?: string;
  synthesis?: {
    title: string;
    content: string;
    significance: string;
    questions: string[];
  };
}

export interface PatternSummary {
  pattern: string;
  total: number;
  classical: number;
  modern: number;
  avg_cites: number;
  grounding_types: string[];
}
