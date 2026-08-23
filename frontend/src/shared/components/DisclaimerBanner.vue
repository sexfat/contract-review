<script setup lang="ts">
defineProps<{ reportDisclaimer?: string }>()

const permanentDisclaimer = '本服務僅提供輔助審閱與風險提示，非法律意見。'
</script>

<template>
  <aside class="disclaimer" role="note" aria-label="法律免責聲明">
    <strong>使用提醒：</strong>{{ reportDisclaimer || permanentDisclaimer }}
  </aside>
</template>
