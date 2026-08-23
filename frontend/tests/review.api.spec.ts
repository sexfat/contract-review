import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError } from '@/shared/api/http'
import { reviewApi } from '@/features/contract-review/review.api'

describe('review API client', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('uploads the document as multipart form data to the existing documents route', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ document_id: 'doc-1', status: 'uploaded' }), { status: 201 }))
    vi.stubGlobal('fetch', fetchMock)

    await reviewApi.uploadDocument(new File(['document'], 'contract.docx', { type: 'application/vnd.openxmlformats-officedocument.wordprocessingml.document' }))

    expect(fetchMock).toHaveBeenCalledTimes(1)
    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/documents')
    const init = fetchMock.mock.calls[0]?.[1] as RequestInit
    expect(init.method).toBe('POST')
    expect(init.body).toBeInstanceOf(FormData)
    expect((init.body as FormData).get('file')).toBeInstanceOf(File)
    expect(init.headers).toBeUndefined()
  })

  it('uses the actual nested report route and maps server errors', async () => {
    const fetchMock = vi.fn().mockResolvedValue(new Response(JSON.stringify({ error_code: 'DOCUMENT_NOT_READY', message: '文件尚未完成分類，請稍後再試。' }), { status: 409 }))
    vi.stubGlobal('fetch', fetchMock)

    await expect(reviewApi.getReviewReport('doc / 1')).rejects.toEqual(expect.objectContaining({
      name: 'ApiError', status: 409, errorCode: 'DOCUMENT_NOT_READY', message: '文件尚未完成分類，請稍後再試。',
    }))
    expect(fetchMock.mock.calls[0]?.[0]).toBe('/api/documents/doc%20%2F%201/report')
  })
})
