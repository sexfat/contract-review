export type DocumentStatus =
  | 'uploaded'
  | 'parsing'
  | 'parsed'
  | 'classifying'
  | 'classified'
  | 'reviewing'
  | 'completed'
  | 'failed'

export type ClauseType =
  | 'scope'
  | 'acceptance'
  | 'payment'
  | 'ip'
  | 'warranty'
  | 'liability'
  | 'termination'
  | 'penalty'
  | 'confidentiality'
  | 'other'

export type RiskLevel = 'high' | 'medium' | 'low' | 'none'
export type Perspective = 'client' | 'vendor'

export interface DocumentStatusResponse {
  document_id: string
  status: DocumentStatus
}

export interface ClauseLocation {
  article_no: string | null
  heading: string | null
  source_start_index: number
  source_end_index: number
  paragraph_ids: string[]
  table_refs: string[]
}

export interface ExtractedClause {
  clause_id: string
  clause_type: ClauseType
  original_text: string
  location: ClauseLocation
  plain_summary: string
  confidence: number
  requires_human_review?: boolean
  model_id?: string | null
}

export interface EvidenceRef {
  clause_id: string
  quote: string
  rationale: string
}

export interface RiskAssessment {
  risk_id: string
  clause_id: string
  clause_type: ClauseType
  risk_for_client: RiskLevel
  risk_for_vendor: RiskLevel
  concern: string
  suggestion: string
  evidence: EvidenceRef[]
  source_refs: string[]
  confidence: number
  requires_human_review?: boolean
}

export interface ReviewReport {
  document_id: string
  contract_title: string
  overall_summary: string
  disclaimer: string
  clauses: ExtractedClause[]
  risks: RiskAssessment[]
}
