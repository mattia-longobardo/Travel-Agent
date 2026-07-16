export type AgentName = "intake" | "scout" | "flight" | "hotel" | "package" | "optimizer" | "presenter";

export type SearchMode = "hotel_only" | "flight_only" | "flight_hotel";
export type AccommodationType = "hotel" | "home" | "both";
export type AccommodationKind = "hotel" | "home";

export interface AgentStep {
  type: "agent_step";
  agent: AgentName;
  status: "running" | "done" | "error";
  label: string;
}

export interface QuestionOption {
  label: string;
  value: string | number;
  description?: string;
}

export interface QuestionEvent {
  type: "question";
  id: string;
  text: string;
  options: QuestionOption[];
  allow_free_text: boolean;
  // When true the user may pick more than one option (e.g. the destination choice). The UI
  // collects the picks and submits them as a single comma-separated answer.
  multi_select?: boolean;
}

export interface PackageCardData {
  id: string;
  // package = combined flight+hotel checkout; separate = flight+hotel estimate with two
  // bookings; hotel_only / flight_only = single-service results (search mode / overland trip).
  kind: "package" | "separate" | "hotel_only" | "flight_only";
  badge: "best_value" | "cheapest" | "upgrade" | null;
  destination: string;
  // Location grouping keys (one card belongs to one location). Used to group results by
  // location for the selector and the Excel "Località" column.
  dest_iata?: string | null;
  dest_name?: string | null;
  price_per_person: number;
  price_total: number;
  currency: string;
  nights: number;
  // Separate-card price breakdown (null for combined "package" cards).
  flight_pp?: number | null;
  hotel_pp?: number | null;
  // Separate-card booking links: a minted hotel checkout and the flight deeplink.
  flight_url?: string | null;
  hotel_url?: string | null;
  // The kind and stable provider detail page are deliberately separate from checkout URLs.
  // `property_url` backs "Vedi Hotel/Casa" and must never be a booking/checkout fallback.
  accommodation_kind?: AccommodationKind | null;
  property_url?: string | null;
  date_from?: string | null;
  date_to?: string | null;
  departure_iata?: string | null;
  hotel_name?: string;
  hotel_stars?: number;
  hotel_rating?: number;
  hotel_reviews?: number | null;
  hotel_distance_km?: number | null;
  hotel_facilities?: string[] | null;
  hotel_cancellable?: boolean | null;
  flight_summary?: string;
  image_url?: string | null;
  unmet?: string[];
  reason?: string;
  booking_url?: string | null;
  // Lazy lastminute hotel-detail link target used by the "Vedi hotel" action.
  review_url?: string | null;
}

/**
 * One ranked result set produced by an assistant turn. Batches are kept in
 * chronological order so a later refinement never overwrites earlier offers.
 */
export interface ResultBatch {
  id: string;
  packages: PackageCardData[];
  created_at?: string;
}

export interface PackageEvent {
  type: "package";
  data: PackageCardData;
}

export interface MessageEvent {
  type: "message";
  content: string;
}

export interface DoneEvent {
  type: "done";
}

export interface ErrorEvent {
  type: "error";
  message: string;
}

export interface StoppedEvent {
  type: "stopped";
}

export interface ChatTitleEvent {
  type: "chat_title";
  chat_id: number;
  title: string;
}

export interface BriefData {
  search_mode?: SearchMode;
  accommodation_type?: AccommodationType;
  accommodation_area?: string | null;
  destination_hint: string | null;
  date_from: string | null;
  date_to: string | null;
  window_from: string | null;
  window_to: string | null;
  trip_nights: number | null;
  dates_flexible: boolean;
  adults: number | null;
  children_ages: number[];
  budget_per_person: number | null;
  currency: string;
  min_stars: number | null;
  origin_iata: string[];
}

export interface BriefEvent {
  type: "brief";
  data: BriefData;
}

export interface Me {
  id: number;
  username: string;
  email: string;
  is_admin: boolean;
}

export interface ChatSummary {
  id: number;
  title: string;
  params_json: Partial<BriefData> & { pending_question?: QuestionEvent | null; run_active?: boolean } & Record<string, unknown>;
  owner_id: number;
  permission: string;
  status: string;
  chat_group_id: number | null;
}

export interface ChatGroup {
  id: number;
  name: string;
}

export type AnalyticsOutcome = "success" | "error" | "cancelled";
export type AnalyticsDay = {
  day: string; runs: number; successes: number; errors: number; cancelled: number;
  tokens: number; avg_latency_ms: number; estimated_cost_usd: number; has_unpriced: boolean;
};
export type AnalyticsOverview = {
  total_chats: number; total_users: number; total_messages: number; total_runs: number;
  total_prompt_tokens: number; total_completion_tokens: number; total_tokens: number;
  avg_latency_ms: number; total_successes: number; total_errors: number; total_cancelled: number;
  success_rate: number; error_rate: number; estimated_cost_usd: number; has_unpriced: boolean;
  by_day: AnalyticsDay[];
};
export type AnalyticsPath = { path: string[]; count: number; avg_latency_ms: number; avg_tokens: number };
export type AnalyticsChatRow = {
  chat_id: number; title: string; owner_id: number; owner_username: string;
  created_at: string; last_message_at: string | null;
  message_count: number; run_count: number; total_tokens: number; avg_latency_ms: number;
  estimated_cost_usd: number; has_unpriced: boolean;
  success_count: number; error_count: number; cancelled_count: number; success_rate: number;
};
export type AnalyticsChatsPage = { items: AnalyticsChatRow[]; total: number; page: number; page_size: number };
export type AnalyticsModelRow = {
  model: string | null; runs: number; prompt_tokens: number; completion_tokens: number;
  total_tokens: number; avg_latency_ms: number; successes: number; errors: number; cancelled: number;
  success_rate: number; cost_usd: number | null; cost_per_run_usd: number | null;
};
export type ModelsResult = { items: AnalyticsModelRow[]; total_cost_usd: number; has_unpriced: boolean };
export type AnalyticsErrorRow = {
  created_at: string; chat_id: number; chat_title: string; owner_username: string;
  model: string | null; error: string | null; latency_ms: number;
};
export type ErrorsResult = { items: AnalyticsErrorRow[]; total: number; page: number; page_size: number };
export type AnalyticsOwner = { id: number; username: string };
export type AnalyticsChatDetail = {
  range: string;
  chat: { id: number; title: string; owner_username: string; created_at: string };
  messages: { role: "user" | "assistant"; content: string; created_at: string; tool_calls: unknown | null }[];
  runs: {
    created_at: string; node_path: string[]; total_tokens: number; latency_ms: number;
    model: string | null; cost_usd: number | null; ok: boolean; error: string | null;
    outcome: AnalyticsOutcome;
  }[];
  stats: {
    message_count: number; run_count: number; total_tokens: number; avg_latency_ms: number;
    prompt_tokens: number; completion_tokens: number; estimated_cost_usd: number; has_unpriced: boolean;
    success_count: number; error_count: number; cancelled_count: number; success_rate: number;
  };
};

export interface StoredMessage {
  id: number;
  role: string;
  content: string;
  tool_calls_json: { events?: ChatEvent[]; ranked?: PackageCardData[] } | null;
  created_at: string;
}

export type ChatEvent =
  | AgentStep
  | QuestionEvent
  | PackageEvent
  | MessageEvent
  | BriefEvent
  | DoneEvent
  | ErrorEvent
  | StoppedEvent
  | ChatTitleEvent;

export type View = "active" | "archived" | "trashed";
export type Tab = "brief" | "risultati";

export interface ChatActions {
  onSelect: (id: number) => void;
  onArchive: (id: number) => void;
  onTrash: (id: number) => void;
  onRestore: (id: number) => void;
  onDeleteForever: (id: number) => void;
  onShare: (id: number) => void;
  onMove: (id: number, gid: number | null) => void;
  onRename: (id: number) => void;
}
