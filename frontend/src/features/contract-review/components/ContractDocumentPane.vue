<script setup lang="ts">
import { nextTick, watch } from 'vue'
import type { ExtractedClause } from '../review.types'

const props = defineProps<{
  clauses: ExtractedClause[]
  selectedClauseId: string | null
}>()

watch(
  () => props.selectedClauseId,
  async (clauseId) => {
    if (!clauseId) return
    await nextTick()
    document.getElementById(`clause-${clauseId}`)?.scrollIntoView({ behavior: 'smooth', block: 'center' })
  },
)
</script>

<template>
  <section class="workbench-pane document-pane" aria-labelledby="document-pane-title">
    <header class="pane-header">
      <div>
        <p class="eyebrow">合約原文</p>
        <h2 id="document-pane-title">條款內容</h2>
      </div>
      <span>{{ clauses.length }} 條</span>
    </header>
    <div v-if="clauses.length" class="clause-list">
      <article
        v-for="clause in clauses"
        :id="`clause-${clause.clause_id}`"
        :key="clause.clause_id"
        class="clause"
        :class="{ 'clause--selected': selectedClauseId === clause.clause_id }"
        :aria-current="selectedClauseId === clause.clause_id ? 'true' : undefined"
      >
        <p class="clause__article">{{ clause.location.article_no ?? '未標示條號' }}</p>
        <h3 v-if="clause.location.heading">{{ clause.location.heading }}</h3>
        <p class="clause__text">{{ clause.original_text }}</p>
      </article>
    </div>
    <p v-else class="empty-state">完成審閱後，合約原文會顯示於此。</p>
  </section>
</template>
