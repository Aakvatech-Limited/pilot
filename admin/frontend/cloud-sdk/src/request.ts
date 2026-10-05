const methodPrefix = 'frappe.integrations.frappe_providers.cloud_settings'

type ErrorBody = {
  exc_type?: string
  _server_messages?: string
}

const parseServerMessages = (raw?: string): string[] => {
  if (!raw) return []

  try {
    return JSON.parse(raw)
      .map((item: string) => JSON.parse(item).message)
      .filter(Boolean)
      .map((message: string) => message.replace(/<[^>]*>/g, ''))
  } catch {
    return []
  }
}

const fallbackMessage = (status: number, excType?: string) => {
  if (status === 403) return "You don't have permission to do this."
  if (excType) return `${excType}. Please try again.`

  return 'Something went wrong. Please try again.'
}

export class CloudSettingsError extends Error {
  status: number
  excType: string
  serverMessages: string[]

  constructor(status: number, body: ErrorBody) {
    const serverMessages = parseServerMessages(body._server_messages)

    super(serverMessages.join('. ') || fallbackMessage(status, body.exc_type))

    this.name = 'CloudSettingsError'
    this.status = status
    this.excType = body.exc_type || ''
    this.serverMessages = serverMessages
  }
}

export const isMigrationConflict = (exception: unknown) =>
  exception instanceof CloudSettingsError && exception.excType === 'CloudMigrationConflictError'

// encode sameas desk frappe.call
const encodeValue = (value: unknown) => {
  if (value == null) return ''

  return typeof value === 'object' ? JSON.stringify(value) : String(value)
}

const csrfToken = () => {
  const page = globalThis as { csrf_token?: string; frappe?: { csrf_token?: string } }

  return page.frappe?.csrf_token || page.csrf_token || ''
}

export const call = async <T = any>(
  method: string,
  args: Record<string, unknown> = {},
  type: 'GET' | 'POST' = 'POST',
): Promise<T> => {
  const url = `/api/method/${methodPrefix}.${method}`
  const params = new URLSearchParams()

  for (const [key, value] of Object.entries(args)) params.append(key, encodeValue(value))

  const response = await fetch(type === 'GET' ? `${url}?${params}` : url, {
    method: type,
    body: type === 'POST' ? params : undefined,
    headers: { Accept: 'application/json', 'X-Frappe-CSRF-Token': csrfToken() },
  })

  const body = await response.json().catch(() => ({}))

  if (!response.ok) throw new CloudSettingsError(response.status, body)

  return body.message
}
