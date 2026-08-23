import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { reviewApi } from '@/features/contract-review/review.api'
import { sortRisksForPerspective, useReviewStore } from '@/features/contract-review/review.store'
import { clientHighRisk, reviewReportFixture, vendorHighRisk } from './fixtures'

describe('review store perspective behavior', () => {
  beforeEach(() => setActivePinia(createPinia()))

  it('sorts existing risks by the selected party risk level', () => {
    expect(sortRisksForPerspective([clientHighRisk, vendorHighRisk], 'client').map((risk) => risk.risk_id))
      .toEqual(['risk-client-high', 'risk-vendor-high'])
    expect(sortRisksForPerspective([clientHighRisk, vendorHighRisk], 'vendor').map((risk) => risk.risk_id))
      .toEqual(['risk-vendor-high', 'risk-client-high'])
  })

  it('changes only local UI state and never re-fetches or re-calls review services', () => {
    const store = useReviewStore()
    store.report = reviewReportFixture
    const originalReport = store.report
    const apiCalls = vi.spyOn(reviewApi, 'getReviewReport')
    const reviewCalls = vi.spyOn(reviewApi, 'reviewDocument')

    store.setPerspective('client')

    expect(store.selectedPerspective).toBe('client')
    expect(store.visibleRisks.map((risk) => risk.risk_id)).toEqual(['risk-client-high', 'risk-vendor-high'])
    expect(store.report).toBe(originalReport)
    expect(apiCalls).not.toHaveBeenCalled()
    expect(reviewCalls).not.toHaveBeenCalled()
  })
})
