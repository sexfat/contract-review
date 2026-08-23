<script setup lang="ts">
import { computed } from 'vue'
import PerspectiveToggle from './PerspectiveToggle.vue'
import RiskCard from './RiskCard.vue'
import type { ExtractedClause, Perspective, RiskAssessment } from '../review.types'

const props = defineProps<{
  risks: RiskAssessment[]
  clauses: ExtractedClause[]
  perspective: Perspective
}>()
const emit = defineEmits<{
  'update:perspective': [value: Perspective]
  selectClause: [clauseId: string]
}>()

const clausesById = computed(() => new Map(props.clauses.map((clause) => [clause.clause_id, clause])))
</script>

<template>
  <section class="workbench-pane risk-panel" aria-labelledby="risk-panel-title">
    <header class="pane-header risk-panel__header">
      <div>
        <p class="eyebrow">審閱結果</p>
        <h2 id="risk-panel-title">雙視角風險</h2>
      </div>
      <PerspectiveToggle :model-value="perspective" @update:model-value="emit('update:perspective', $event)" />
    </header>
    <p class="risk-panel__hint">切換視角只會重新排列目前報告中的風險，不會重新分析文件。</p>
    <div v-if="risks.length" class="risk-list">
      <RiskCard
        v-for="risk in risks"
        :key="risk.risk_id"
        :risk="risk"
        :clause="clausesById.get(risk.clause_id)"
        :perspective="perspective"
        @select="emit('selectClause', $event)"
      />
    </div>
    <p v-else class="empty-state">尚無已驗證的風險項目。這不代表合約沒有風險，建議仍由專業人士確認。</p>
  </section>
</template>
