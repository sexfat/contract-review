export class ApiError extends Error {
  constructor(
    public readonly status: number,
    public readonly errorCode: string | null,
    message: string,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

type ErrorBody = { error_code?: string; message?: string }

export async function requestJson<T>(input: RequestInfo | URL, init?: RequestInit): Promise<T> {
  let response: Response

  try {
    response = await fetch(input, init)
  } catch {
    throw new ApiError(0, null, '無法連線至審閱服務，請確認網路後再試。')
  }

  if (!response.ok) {
    const body = (await response.json().catch(() => ({}))) as ErrorBody
    throw new ApiError(
      response.status,
      body.error_code ?? null,
      body.message ?? `請求失敗（HTTP ${response.status}）。`,
    )
  }

  return response.json() as Promise<T>
}
