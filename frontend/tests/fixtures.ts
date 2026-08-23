import type { ReviewReport, RiskAssessment } from '@/features/contract-review/review.types'

export const clientHighRisk: RiskAssessment = {
  risk_id: 'risk-client-high',
  clause_id: 'clause-1',
  clause_type: 'liability',
  risk_for_client: 'high',
  risk_for_vendor: 'low',
  concern: '可能有疑慮，建議確認責任範圍。',
  suggestion: '可考慮協商合理的責任上限。',
  evidence: [{ clause_id: 'clause-1', quote: '乙方應負一切損害賠償責任', rationale: '責任範圍未設上限。' }],
  source_refs: ['liability-unlimited-001'],
  confidence: 0.86,
}

export const vendorHighRisk: RiskAssessment = {
  ...clientHighRisk,
  risk_id: 'risk-vendor-high',
  risk_for_client: 'low',
  risk_for_vendor: 'high',
}

export const reviewReportFixture: ReviewReport = {
  document_id: 'document-1',
  contract_title: '測試合約',
  overall_summary: '本報告含一項待確認風險。',
  disclaimer: '本服務僅提供輔助審閱與風險提示，非法律意見。',
  clauses: [{
    clause_id: 'clause-1',
    clause_type: 'liability',
    original_text: '第十條 乙方應負一切損害賠償責任。',
    location: {
      article_no: '第十條', heading: '賠償責任', source_start_index: 0, source_end_index: 0, paragraph_ids: ['p-0001'], table_refs: [],
    },
    plain_summary: '約定乙方負擔賠償責任。',
    confidence: 0.91,
  }],
  risks: [clientHighRisk, vendorHighRisk],
}
