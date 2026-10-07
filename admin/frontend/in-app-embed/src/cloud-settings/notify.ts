import { toast } from 'frappe-ui'

const TOASTS = { green: toast.success, orange: toast.warning, red: toast.error }

/** A toast inside the dialog's shadow root, so it looks the same in every app. */
export const notify = (message: string, indicator: keyof typeof TOASTS = 'green') =>
  TOASTS[indicator](message)
