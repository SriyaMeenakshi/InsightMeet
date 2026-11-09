export type Label = "ACTION" | "DECISION" | "ISSUE" | "SUGGESTION" | "INFORMATION" | "QUESTION";

export interface Evidence {
  sentence_id: number;
  speaker: string | null;
  text: string;
  start: number;
  end: number;
}

export interface DeadlineInfo {
  raw: string;
  kind: string;
  resolved: boolean;
  date: string | null;
  precision: string;
  normalized: string;
  note: string | null;
}

export interface DeadlineVersion {
  role: "original" | "revised" | "single";
  deadline: DeadlineInfo;
  evidence: Evidence;
}

export interface ActionItem {
  id: string;
  task: string;
  owner: string | null;
  owners: string[];
  owner_basis: string | null;
  said_by: string | null;
  commitment: "definite" | "tentative" | "requested" | "unassigned";
  deadline: DeadlineInfo | null;
  original_deadline: DeadlineInfo | null;
  deadline_history: DeadlineVersion[];
  status: "open" | "done";
  blocked: boolean;
  blocked_by: string[];
  components: string[];
  confidence: number;
  needs_review: boolean;
  review_reasons: string[];
  mentions: number;
  context: string | null;
  evidence: Evidence[];
}

export interface Decision {
  id: string;
  text: string;
  status: "confirmed" | "superseded";
  basis: string;
  decided_by: string | null;
  components: string[];
  supersedes: string | null;
  superseded_by: string | null;
  confidence: number;
  needs_review: boolean;
  review_reasons: string[];
  evidence: Evidence[];
}

export interface Issue {
  id: string;
  problem: string;
  component: string | null;
  impact: string | null;
  blocked_activity: string | null;
  status: "open" | "resolved";
  raised_by: string | null;
  confidence: number;
  needs_review: boolean;
  review_reasons: string[];
  evidence: Evidence[];
}

export interface Suggestion {
  id: string;
  text: string;
  proposer: string | null;
  status: "unconfirmed" | "accepted" | "rejected";
  tentative: boolean;
  components: string[];
  evidence: Evidence[];
  response: Evidence | null;
}

export interface DeadlineEntry {
  id: string;
  task_id: string | null;
  task: string | null;
  owner: string | null;
  deadline: DeadlineInfo;
  role: "original" | "revised" | "single" | "standalone";
  is_latest: boolean;
  superseded: boolean;
  evidence: Evidence;
  needs_review: boolean;
  review_reasons: string[];
}

export interface RelNode {
  kind: "person" | "action" | "issue" | "decision" | "component" | "text";
  id: string | null;
  text: string;
}

export interface Relationship {
  id: string;
  type: "ASSIGNED_TO" | "DEPENDS_ON" | "BLOCKS" | "AFFECTS";
  source: RelNode;
  target: RelNode;
  explicit: boolean;
  basis: string;
  confidence: number;
  evidence: Evidence[];
}

export interface Entity {
  text: string;
  label: string;
  count: number;
  sentence_ids: number[];
  source: string;
}

export interface Participant {
  name: string;
  sentences: number;
  turns: number;
  words: number;
  share: number;
  actions_owned: number;
}

export interface Keyphrase {
  phrase: string;
  score: number;
  mentions: number;
  sentence_ids: number[];
}

export interface Topic {
  topic: string;
  mentions: number;
  share: number;
  first_sentence_id: number;
  sentence_ids: number[];
}

export interface SentenceOut {
  id: number;
  index: number;
  turn_index: number;
  speaker: string | null;
  speaker_inherited: boolean;
  text: string;
  original: string;
  start: number;
  end: number;
  label: Label;
  confidence: number;
  label_source: "rules" | "model";
  model_label: string;
  model_confidence: number;
}

export interface ReviewItem {
  item_type: string;
  item_id: string;
  text: string;
  reasons: string[];
}

export interface Overview {
  title: string;
  meeting_date: string | null;
  sentences: number;
  words: number;
  participants: number;
  action_items: number;
  decisions: number;
  issues_open: number;
  issues_total: number;
  suggestions: number;
  needs_review: number;
  unresolved_deadlines: number;
}

export interface Analysis {
  meeting_id: string | null;
  created_at: string | null;
  title: string;
  meeting_date: string | null;
  transcript: string;
  overview: Overview;
  summary: { overview: string; highlights: Evidence[]; method: string };
  topics: Topic[];
  keyphrases: Keyphrase[];
  participants: Participant[];
  entities: Entity[];
  action_items: ActionItem[];
  decisions: Decision[];
  issues: Issue[];
  suggestions: Suggestion[];
  deadlines: DeadlineEntry[];
  relationships: Relationship[];
  distribution: Record<Label, number>;
  review_queue: ReviewItem[];
  sentences: SentenceOut[];
  representation: {
    available: boolean;
    sentences?: number;
    vocabulary_size?: number;
    bag_of_words?: { shape: number[]; non_zero_cells: number; density: number };
    tfidf?: {
      shape: number[];
      non_zero_cells: number;
      density: number;
      top_terms: { term: string; weight: number; count: number }[];
    };
    lsa?: { dimensions: number; explained_variance: number; cell_density: number } | null;
    note?: string;
  };
  warnings: string[];
  nlp_info: Record<string, string | null>;
}

export interface MeetingSummary {
  id: string;
  title: string;
  created_at: string;
  meeting_date: string | null;
  snippet: string;
  counts: Record<string, number>;
}

export interface AskResponse {
  question: string;
  found: boolean;
  answer: string;
  method: string;
  confidence: number;
  evidence: Evidence[];
  related: Record<string, string>[];
}

export interface SearchHit {
  score: number;
  evidence: Evidence;
  label: Label;
}

export interface ModelScores {
  n: number;
  accuracy: number;
  macro_precision: number;
  macro_recall: number;
  macro_f1: number;
  per_class: Record<string, { precision: number; recall: number; "f1-score": number; support: number }>;
  confusion_matrix: number[][];
}

export interface ModelMetrics {
  labels: Label[];
  dataset: { type: string; sizes: Record<string, number> };
  split_policy: string;
  results: Record<string, Record<string, ModelScores>>;
  caveat: string;
}
