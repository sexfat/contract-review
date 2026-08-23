<script setup lang="ts">
import type { Perspective } from '../review.types'

defineProps<{ modelValue: Perspective }>()
const emit = defineEmits<{ 'update:modelValue': [value: Perspective] }>()
</script>

<template>
  <div class="perspective-toggle" role="group" aria-label="審閱視角">
    <button
      type="button"
      :class="{ 'is-active': modelValue === 'client' }"
      :aria-pressed="modelValue === 'client'"
      @click="emit('update:modelValue', 'client')"
    >
      甲方視角
    </button>
    <button
      type="button"
      :class="{ 'is-active': modelValue === 'vendor' }"
      :aria-pressed="modelValue === 'vendor'"
      @click="emit('update:modelValue', 'vendor')"
    >
      乙方視角
    </button>
  </div>
</template>
