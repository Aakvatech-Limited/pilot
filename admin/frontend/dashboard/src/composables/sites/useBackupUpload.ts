import { ref } from 'vue'
import { sitesApi } from '@/api/sites'

const MAX_RETRIES = 3

/** Send backup files in chunks. A failed chunk resumes from the bytes the server has. */
export const useBackupUpload = (siteName: () => string) => {
  const progress = ref<Record<string, number>>({})
  const isUploading = ref(false)
  let uploadId = ''
  let controller: AbortController | null = null

  const sendFile = async (part: string, file: File, chunkSize: number, signal: AbortSignal) => {
    let offset = 0
    let failures = 0
    while (offset < file.size) {
      const start = offset
      try {
        offset = await sitesApi.uploads.sendChunk(
          siteName(),
          uploadId,
          part,
          start,
          file.slice(start, start + chunkSize),
          (sent) => (progress.value[part] = (start + sent) / file.size),
          signal,
        )
        failures = 0
      } catch (error) {
        if (signal.aborted || ++failures > MAX_RETRIES) throw error
        offset = (await sitesApi.uploads.status(siteName(), uploadId)).files[part].received
      }
    }
    progress.value[part] = 1
  }

  /** Upload `files` by part and return the upload id that a restore claims. */
  const upload = async (files: Record<string, File>): Promise<string> => {
    controller = new AbortController()
    isUploading.value = true
    const described = Object.fromEntries(
      Object.entries(files).map(([part, file]) => [part, { filename: file.name, size: file.size }]),
    )
    try {
      const started = await sitesApi.uploads.start(siteName(), described)
      uploadId = started.upload_id
      // Closed while the upload was starting: the catch removes it from the server.
      if (controller.signal.aborted)
        throw new DOMException('The upload was cancelled.', 'AbortError')
      for (const [part, file] of Object.entries(files))
        await sendFile(part, file, started.chunk_size, controller.signal)
    } catch (error) {
      cancel()
      throw error
    } finally {
      isUploading.value = false
    }
    return uploadId
  }

  /** Stop sending and remove the parts already on the server. */
  const cancel = () => {
    controller?.abort()
    if (uploadId) sitesApi.uploads.cancel(siteName(), uploadId).catch(() => {})
    uploadId = ''
    progress.value = {}
  }

  return { progress, isUploading, upload, cancel }
}
