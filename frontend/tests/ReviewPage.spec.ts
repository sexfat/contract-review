import { beforeEach, describe, expect, it, vi } from 'vitest'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import ReviewPage from '@/features/contract-review/ReviewPage.vue'
import { useReviewStore } from '@/features/contract-review/review.store'
import { reviewReportFixture } from './fixtures'

describe('ReviewPage', () => {
  let pinia: ReturnType<typeof createPinia>

  beforeEach(() => {
    pinia = createPinia()
    setActivePinia(pinia)
  })

  it('always shows the permanent disclaimer and changes perspective locally', async () => {
    const store = useReviewStore()
    store.report = reviewReportFixture
    const setPerspective = vi.spyOn(store, 'setPerspective')
    const wrapper = mount(ReviewPage, { global: { plugins: [pinia] } })

    expect(wrapper.text()).toContain('本服務僅提供輔助審閱與風險提示，非法律意見。')
    await wrapper.get('button[aria-pressed="false"]').trigger('click')
    expect(setPerspective).toHaveBeenCalled()
  })
})
