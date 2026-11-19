export type ProvenanceClass =
  | "DIRECTLY_SCRAPED"
  | "PUBLICLY_VERIFIED_FALLBACK"
  | "MANUALLY_CURATED"
  | "UNVERIFIED";

export interface ToolExecutionTrace {
  step: number;
  tool_name: string;
  arguments: Record<string, unknown>;
  execution_time_ms: number;
  status: "SUCCESS" | "ERROR" | "TIMEOUT" | "SKIPPED";
  result_summary: string;
  output?: Record<string, unknown> | null;
  error?: string | null;
}

export interface Citation {
  citation_id: number;
  title: string;
  url: string;
  source: "DarGlobal" | "Wasalt" | string;
  snippet: string;
  provenance_class?: ProvenanceClass;
  extraction_method?: string;
  extraction_timestamp?: string;
  is_directly_scraped?: boolean;
  alternative_source?: string | null;
  origin_notes?: string;
  metadata?: Record<string, unknown>;
}

export interface ActiveFilters {
  location?: string | null;
  currency?: string | null;
  budget_max?: number | null;
  property_type?: string | null;
  bedrooms?: number | null;
  data_sources?: string[];
  filter_summary?: string;
}

export interface ChatMessage {
  id: string;
  role: "user" | "assistant" | "system";
  content: string;
  citations?: Citation[];
  execution_trace?: ToolExecutionTrace[];
  model_used?: string;
  timestamp: string;
  active_filters?: ActiveFilters | null;
  intent?: string | null;
}

export interface ChatSession {
  id: string;
  title: string;
  createdAt: string;
  updatedAt: string;
  messages: ChatMessage[];
}

export interface ChatRequest {
  message: string;
  history?: Array<{ role: string; content: string }>;
  conversation_id?: string | null;
  stream?: boolean;
  source_filter?: string | null;
  top_k?: number;
}

export interface ChatResponse {
  answer: string;
  citations: Citation[];
  execution_trace?: ToolExecutionTrace[];
  model_used: string;
  retrieval_count: number;
  provenance_summary?: Record<string, number>;
  execution_time_ms: number;
  intent?: string;
  conversation_id?: string;
  active_filters?: ActiveFilters | null;
}

export interface PropertyItem {
  id: string;
  title: string;
  source: "DarGlobal" | "Wasalt" | string;
  url: string;
  location: string;
  country: string;
  city: string;
  property_type: string;
  price?: string | null;
  currency?: string | null;
  developer_or_broker?: string | null;
  brand_partner?: string | null;
  handover_date?: string | null;
  amenities: string[];
  description: string;
  image_url?: string | null;
  provenance_class?: ProvenanceClass;
  extraction_method?: string;
  extraction_timestamp?: string;
  is_directly_scraped?: boolean;
  alternative_source?: string | null;
  origin_notes?: string;
  metadata: Record<string, unknown>;
}

export interface HealthStatus {
  status: string;
  project: string;
  version: string;
  vector_db_connected: boolean;
  bm25_index_ready: boolean;
  total_indexed_chunks: number;
  openrouter_configured: boolean;
  active_model: string;
  available_free_models: string[];
  provenance_distribution?: Record<string, number>;
  agentic_tools_ready?: boolean;
  registered_tools?: string[];
}
