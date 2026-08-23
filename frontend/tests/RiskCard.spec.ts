import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'
import RiskCard from '@/features/contract-review/components/RiskCard.vue'
import { clientHighRisk, reviewReportFixture } from './fixtures'

describe('RiskCard', () => {
  it('renders article, current risk level, quote, explanation, suggestion, and source', () => {
    const wrapper = mount(RiskCard, {
      props: { risk: clientHighRisk, clause: reviewReportFixture.clauses[0], perspective: 'client' },
    })

    expect(wrapper.text()).toContain('第十條')
    expect(wrapper.text()).toContain('甲方：高風險')
    expect(wrapper.text()).toContain('乙方應負一切損害賠償責任')
    expect(wrapper.text()).toContain('可能有疑慮，建議確認責任範圍。')
    expect(wrapper.text()).toContain('可考慮協商合理的責任上限。')
    expect(wrapper.text()).toContain('liability-unlimited-001')
  })
})
