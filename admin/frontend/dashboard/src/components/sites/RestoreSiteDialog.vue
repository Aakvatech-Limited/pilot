<script setup lang="ts">
import { Button, Checkbox, Select, TabButtons, TextInput } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { apiErrorMessage } from '@/api/client'
import { sitesApi } from '@/api/sites'
import ActionDialog from '@/components/common/ActionDialog.vue'
import { useSites } from '@/composables/sites/useSites'
import type { RemoteBackup } from '@/types/siteBackups'
import type { TaskPayload } from '@/types/tasks'
import { errorMessage } from '@/utils/error'
import { fmtDateTime } from '@/utils/taskFormat'
import { openTaskDetailPage } from '@/utils/taskRoute'

interface Props {
  siteName: string
}

const props = defineProps<Props>()
const open = defineModel<boolean>('open')

const router = useRouter()
const { names: siteNames, load: loadSites } = useSites()

type Source = 'upload' | 'site' | 'remote'

const SOURCES = [
  { value: 'upload', label: 'Upload files' },
  { value: 'site', label: 'Another site' },
  { value: 'remote', label: 'Remote site' },
]
const PARTS = [
  { part: 'database', label: 'Database', hint: 'Usually ends in .sql.gz or .sql', accept: '.sql,.gz' },
  { part: 'public', label: 'Public files', hint: 'Usually ends in -files.tar', accept: '.tar,.tgz' },
  {
    part: 'private',
    label: 'Private files',
    hint: 'Usually ends in -private-files.tar',
    accept: '.tar,.tgz',
  },
]
const CONFIG = {
  part: 'config',
  label: 'Site config',
  hint: 'Needed when the backup is encrypted. Usually ends in -site_config_backup.json',
  accept: '.json',
}

const source = ref<Source>('upload')
const sourceSite = ref('')
const remoteSite = ref('')
const password = ref('')
const remoteBackups = ref<RemoteBackup[] | null>(null)
const remoteBackup = ref('')
const fetchingBackups = ref(false)
const chosen = ref<Record<string, boolean>>({})
const uploads = ref<Record<string, File | null>>({})
const inputs: Record<string, HTMLInputElement | null> = {}
const restoring = ref(false)
const error = ref('')

const sourceOptions = computed(() =>
  siteNames.value.filter((name) => name !== props.siteName).map((name) => ({ label: name, value: name })),
)
const remoteBackupOptions = computed(() => [
  ...(remoteBackups.value ?? []).map((backup) => ({
    label: fmtDateTime(backup.created_at),
    value: backup.timestamp,
  })),
  { label: 'New backup', value: '' },
])
const availableParts = computed(() => {
  const backup = remoteBackups.value?.find(({ timestamp }) => timestamp === remoteBackup.value)
  return source.value === 'remote' && backup ? backup.parts : PARTS.map(({ part }) => part)
})
const uploadRows = computed(() => (uploads.value.database ? [...PARTS, CONFIG] : PARTS))
const parts = computed(() =>
  PARTS.map(({ part }) => part).filter((part) =>
    source.value === 'upload'
      ? uploads.value[part]
      : chosen.value[part] && availableParts.value.includes(part),
  ),
)
const isReady = computed(() => {
  if (!parts.value.length) return false
  if (source.value === 'site') return Boolean(sourceSite.value)
  if (source.value === 'remote') return remoteBackups.value !== null
  return true
})

watch(open, (isOpen) => {
  if (!isOpen) return
  source.value = 'upload'
  sourceSite.value = ''
  remoteSite.value = ''
  password.value = ''
  chosen.value = { database: true, public: true, private: true }
  uploads.value = {}
  error.value = ''
  loadSites()
})

watch([remoteSite, password], () => {
  remoteBackups.value = null
  remoteBackup.value = ''
})

const getBackups = async () => {
  fetchingBackups.value = true
  error.value = ''
  try {
    const data = await sitesApi.remoteBackups(props.siteName, remoteSite.value.trim(), password.value)
    remoteBackups.value = data.backups
    remoteBackup.value = data.backups[0]?.timestamp ?? ''
  } catch (e) {
    error.value = errorMessage(e, 'Could not get the backups of this site.')
  } finally {
    fetchingBackups.value = false
  }
}

const pickFile = (part: string, event: Event) => {
  const input = event.target as HTMLInputElement
  uploads.value[part] = input.files?.[0] ?? null
  input.value = ''
}

const removeFile = (part: string) => {
  uploads.value[part] = null
  if (part === 'database') uploads.value.config = null
}

const submit = (): Promise<TaskPayload> => {
  if (source.value === 'upload') {
    const form = new FormData()
    for (const part of parts.value) form.append('parts', part)
    for (const { part } of uploadRows.value) {
      const file = uploads.value[part]
      if (file) form.append(part, file)
    }
    return sitesApi.restoreUpload(props.siteName, form)
  }
  if (source.value === 'remote')
    return sitesApi.restore(props.siteName, {
      parts: parts.value,
      remote_site: remoteSite.value.trim(),
      password: password.value,
      backup_timestamp: remoteBackup.value,
    })
  return sitesApi.restore(props.siteName, { parts: parts.value, source_site: sourceSite.value })
}

const restore = async () => {
  restoring.value = true
  error.value = ''
  try {
    const data = await submit()
    if (data.task_id) {
      open.value = false
      openTaskDetailPage(router, data.task_id)
    } else error.value = apiErrorMessage(data, 'Could not start the restore.')
  } catch (e) {
    error.value = errorMessage(e, 'Could not start the restore.')
  } finally {
    restoring.value = false
  }
}
</script>

<template>
  <ActionDialog
    v-model:open="open"
    title="Restore Site"
    :error="error"
    confirm-label="Restore"
    confirm-theme="red"
    :loading="restoring"
    :disabled="!isReady"
    @confirm="restore"
  >
    <div class="space-y-4">
      <TabButtons v-model="source" :options="SOURCES" class="w-full" />

      <div v-if="source === 'upload'" class="divide-y divide-outline-gray-1">
        <div
          v-for="item in uploadRows"
          :key="item.part"
          class="flex justify-between items-center gap-4 py-2.5"
        >
          <div class="min-w-0">
            <p class="font-medium text-ink-gray-8 text-sm">{{ item.label }}</p>
            <p class="text-ink-gray-5 text-p-sm truncate">
              {{ uploads[item.part]?.name || item.hint }}
            </p>
          </div>
          <input
            :ref="(el) => (inputs[item.part] = el as HTMLInputElement | null)"
            type="file"
            :accept="item.accept"
            class="hidden"
            @change="pickFile(item.part, $event)"
          />
          <Button
            v-if="uploads[item.part]"
            variant="ghost"
            icon="lucide-x"
            :aria-label="`Remove ${item.label}`"
            @click="removeFile(item.part)"
          />
          <Button v-else class="shrink-0" @click="inputs[item.part]?.click()">Choose</Button>
        </div>
      </div>

      <template v-else>
        <Select
          v-if="source === 'site'"
          v-model="sourceSite"
          label="Site"
          :options="sourceOptions"
          placeholder="Choose a site"
        />

        <div v-else class="space-y-3">
          <TextInput v-model="remoteSite" label="Site" placeholder="erp.example.com" />
          <TextInput v-model="password" label="Administrator password" type="password" />
          <div class="flex items-end gap-2">
            <Select
              v-if="remoteBackups"
              v-model="remoteBackup"
              label="Backup"
              :options="remoteBackupOptions"
              class="flex-1"
            />
            <Button
              :loading="fetchingBackups"
              :disabled="!remoteSite.trim() || !password"
              @click="getBackups"
            >
              Get backups
            </Button>
          </div>
          <p v-if="remoteBackups && !remoteBackups.length" class="text-ink-gray-5 text-p-sm">
            No backup found. Take a backup on that site, then get backups again.
          </p>
        </div>

        <div v-if="source !== 'remote' || remoteBackups" class="flex flex-wrap gap-1">
          <Checkbox
            v-for="item in PARTS"
            :key="item.part"
            v-model="chosen[item.part]"
            :label="item.label"
            :disabled="!availableParts.includes(item.part)"
            padded
          />
        </div>
      </template>
    </div>
  </ActionDialog>
</template>
