<script setup lang="ts">
import { computed, ref } from 'vue'
import ContractDocumentPane from './components/ContractDocumentPane.vue'
import RiskPanel from './components/RiskPanel.vue'
import { useReviewStore } from './review.store'
import DisclaimerBanner from '@/shared/components/DisclaimerBanner.vue'

const store = useReviewStore()
const selectedFile = ref<File | null>(null)

const actionLabel = computed(() => ({
  idle: '開始審閱',
  uploading: '正在上傳…',
  parsing: '正在解析條款…',
  classifying: '正在分類條款…',
  reviewing: '正在產生審閱…',
  'loading-report': '正在載入報告…',
  ready: '重新審閱',
  error: '重新嘗試',
}[store.stage]))

function onFileChange(event: Event) {
  selectedFile.value = (event.target as HTMLInputElement).files?.[0] ?? null
}

function submitReview() {
  if (selectedFile.value) void store.startReview(selectedFile.value)
}
</script>

<template>
  <main class="review-page">
    <header class="app-header">
      <div>
        <p class="eyebrow">Contract Review</p>
        <h1>合約審閱工作台</h1>
      </div>
      <form class="upload-form" @submit.prevent="submitReview">
        <label class="file-input">
          <span>選擇 DOCX</span>
          <input type="file" accept=".docx,application/vnd.openxmlformats-officedocument.wordprocessingml.document" @change="onFileChange" />
        </label>
        <span v-if="selectedFile" class="file-name">{{ selectedFile.name }}</span>
        <button type="submit" :disabled="!selectedFile || store.isBusy">{{ actionLabel }}</button>
      </form>
    </header>

    <p v-if="store.errorMessage" class="error-message" role="alert">{{ store.errorMessage }}</p>
    <section v-if="store.report" class="report-summary" aria-live="polite">
      <p class="eyebrow">{{ store.report.contract_title }}</p>
      <p>{{ store.report.overall_summary }}</p>
    </section>

    <section class="workbench" aria-label="合約審閱工作區">
      <ContractDocumentPane :clauses="store.report?.clauses ?? []" :selected-clause-id="store.selectedClauseId" />
      <RiskPanel
        :risks="store.visibleRisks"
        :clauses="store.report?.clauses ?? []"
        :perspective="store.selectedPerspective"
        @update:perspective="store.setPerspective"
        @select-clause="store.selectClause"
      />
    </section>

    <DisclaimerBanner :report-disclaimer="store.report?.disclaimer" />
  </main>
</template>
