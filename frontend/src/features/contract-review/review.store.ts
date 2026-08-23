import { defineStore } from 'pinia'
import { computed, ref } from 'vue'
import { ApiError } from '@/shared/api/http'
import { reviewApi } from './review.api'
import type { Perspective, ReviewReport, RiskAssessment, RiskLevel } from './review.types'

export type ReviewStage = 'idle' | 'uploading' | 'parsing' | 'classifying' | 'reviewing' | 'loading-report' | 'ready' | 'error'

const RISK_PRIORITY: Record<RiskLevel, number> = { high: 3, medium: 2, low: 1, none: 0 }

export function riskLevelForPerspective(risk: RiskAssessment, perspective: Perspective): RiskLevel {
  return perspective === 'client' ? risk.risk_for_client : risk.risk_for_vendor
}

export function sortRisksForPerspective(risks: RiskAssessment[], perspective: Perspective): RiskAssessment[] {
  return [...risks].sort((left, right) => {
    const priorityDifference = RISK_PRIORITY[riskLevelForPerspective(right, perspective)] - RISK_PRIORITY[riskLevelForPerspective(left, perspective)]
    return priorityDifference || left.risk_id.localeCompare(right.risk_id)
  })
}

export const useReviewStore = defineStore('contract-review', () => {
  const documentId = ref<string | null>(null)
  const report = ref<ReviewReport | null>(null)
  const stage = ref<ReviewStage>('idle')
  const errorMessage = ref<string | null>(null)
  const selectedPerspective = ref<Perspective>('vendor')
  const selectedClauseId = ref<string | null>(null)

  const isBusy = computed(() => ['uploading', 'parsing', 'classifying', 'reviewing', 'loading-report'].includes(stage.value))
  const visibleRisks = computed(() => report.value ? sortRisksForPerspective(report.value.risks, selectedPerspective.value) : [])

  function setPerspective(perspective: Perspective) {
    selectedPerspective.value = perspective
  }

  function selectClause(clauseId: string) {
    selectedClauseId.value = clauseId
  }

  async function startReview(file: File) {
    errorMessage.value = null
    report.value = null
    selectedClauseId.value = null

    try {
      stage.value = 'uploading'
      const upload = await reviewApi.uploadDocument(file)
      documentId.value = upload.document_id

      stage.value = 'parsing'
      await reviewApi.parseDocument(upload.document_id)
      stage.value = 'classifying'
      await reviewApi.classifyDocument(upload.document_id)
      stage.value = 'reviewing'
      await reviewApi.reviewDocument(upload.document_id)
      stage.value = 'loading-report'
      report.value = await reviewApi.getReviewReport(upload.document_id)
      stage.value = 'ready'
    } catch (error) {
      stage.value = 'error'
      errorMessage.value = error instanceof ApiError ? error.message : '審閱流程發生未預期錯誤，請稍後再試。'
    }
  }

  return {
    documentId,
    report,
    stage,
    errorMessage,
    selectedPerspective,
    selectedClauseId,
    isBusy,
    visibleRisks,
    setPerspective,
    selectClause,
    startReview,
  }
})
