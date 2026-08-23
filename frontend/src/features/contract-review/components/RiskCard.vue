<script setup lang="ts">
import { computed } from 'vue'
import { riskLevelForPerspective } from '../review.store'
import type { ExtractedClause, Perspective, RiskAssessment, RiskLevel } from '../review.types'

const props = defineProps<{
  risk: RiskAssessment
  clause?: ExtractedClause
  perspective: Perspective
}>()

const emit = defineEmits<{ select: [clauseId: string] }>()

const currentLevel = computed(() => riskLevelForPerspective(props.risk, props.perspective))
const levelLabel: Record<RiskLevel, string> = { high: '高風險', medium: '中風險', low: '低風險', none: '未突出風險' }
const partyLabel = computed(() => props.perspective === 'client' ? '甲方' : '乙方')
const articleNumber = computed(() => props.clause?.location.article_no ?? '未標示條號')
</script>

<template>
  <article
    class="risk-card"
    :class="`risk-card--${currentLevel}`"
    tabindex="0"
    :aria-label="`${articleNumber}，${partyLabel}${levelLabel[currentLevel]}`"
    @click="emit('select', risk.clause_id)"
    @keydown.enter="emit('select', risk.clause_id)"
  >
    <div class="risk-card__heading">
      <p class="risk-card__article">{{ articleNumber }}</p>
      <span class="risk-card__level">{{ partyLabel }}：{{ levelLabel[currentLevel] }}</span>
    </div>
    <p class="risk-card__other-party">另一方：{{ perspective === 'client' ? levelLabel[risk.risk_for_vendor] : levelLabel[risk.risk_for_client] }}</p>
    <dl class="risk-card__details">
      <div>
        <dt>原文引用</dt>
        <dd>
          <blockquote v-for="evidence in risk.evidence" :key="`${risk.risk_id}-${evidence.quote}`">「{{ evidence.quote }}」</blockquote>
        </dd>
      </div>
      <div><dt>說明</dt><dd>{{ risk.concern }}</dd></div>
      <div><dt>建議</dt><dd>{{ risk.suggestion }}</dd></div>
      <div><dt>來源</dt><dd>{{ risk.source_refs.length ? risk.source_refs.join('、') : '未提供來源' }}</dd></div>
    </dl>
  </article>
</template>
