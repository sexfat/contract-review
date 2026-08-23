import { requestJson } from '@/shared/api/http'
import type { DocumentStatusResponse, ReviewReport } from './review.types'

const apiBaseUrl = import.meta.env.VITE_API_BASE_URL ?? ''
const endpoint = (path: string) => `${apiBaseUrl}/api${path}`

export const reviewApi = {
  uploadDocument(file: File): Promise<DocumentStatusResponse> {
    const formData = new FormData()
    formData.append('file', file)
    return requestJson(endpoint('/documents'), { method: 'POST', body: formData })
  },

  parseDocument(documentId: string): Promise<DocumentStatusResponse> {
    return requestJson(endpoint(`/documents/${encodeURIComponent(documentId)}/parse`), { method: 'POST' })
  },

  classifyDocument(documentId: string): Promise<DocumentStatusResponse> {
    return requestJson(endpoint(`/documents/${encodeURIComponent(documentId)}/classify`), { method: 'POST' })
  },

  reviewDocument(documentId: string): Promise<DocumentStatusResponse> {
    return requestJson(endpoint(`/documents/${encodeURIComponent(documentId)}/review`), { method: 'POST' })
  },

  getReviewReport(documentId: string): Promise<ReviewReport> {
    return requestJson(endpoint(`/documents/${encodeURIComponent(documentId)}/report`))
  },
}
