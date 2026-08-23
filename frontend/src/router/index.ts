import { createRouter, createWebHistory } from 'vue-router'
import ReviewPage from '@/features/contract-review/ReviewPage.vue'

export default createRouter({
  history: createWebHistory(),
  routes: [{ path: '/', name: 'review-workbench', component: ReviewPage }],
})
