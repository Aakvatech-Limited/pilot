<script setup lang="ts">
import { Alert, Button, Checkbox, ErrorMessage, Select, TextInput } from 'frappe-ui'
import { computed, onMounted, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { apiErrorMessage } from '@/api/client'
import { sitesApi } from '@/api/sites'
import { useSites } from '@/composables/sites/useSites'
import type { TaskPayload } from '@/types/tasks'
import { errorMessage } from '@/utils/error'
import { openTaskDetailPage } from '@/utils/taskRoute'

const router = useRouter()
const { names: siteNames, load: loadSites } = useSites()

const SOURCES = [
  { label: 'Another site on this bench', value: 'site' },
  { label: 'Upload backup files', value: 'upload' },
  { label: 'A remote Frappe site', value: 'remote' },
]
const PARTS = [
  { part: 'database', label: 'Database', accept: '.sql,.gz' },
  { part: 'public', label: 'Public files', accept: '.tar,.tgz' },
  { part: 'private', label: 'Private files', accept: '.tar,.tgz' },
]

const target = ref('')
const source = ref('site')
const sourceSite = ref('')
const remoteSite = ref('')
const password = ref('')
const chosen = ref<Record<string, boolean>>({ database: true, public: true, private: true })
const uploads = ref<Record<string, File | null>>({})
const restoring = ref(false)
const error = ref('')

const siteOptions = computed(() => siteNames.value.map((name) => ({ label: name, value: name })))
const sourceOptions = computed(() =>
  siteOptions.value.filter((option) => option.value !== target.value),
)
const parts = computed(() => PARTS.filter(({ part }) => chosen.value[part]).map(({ part }) => part))

const isReady = computed(() => {
  if (!target.value || !parts.value.length) return false
  if (source.value === 'site') return Boolean(sourceSite.value)
  if (source.value === 'remote') return Boolean(remoteSite.value.trim() && password.value)
  return parts.value.every((part) => uploads.value[part])
})

// The file inputs are recreated empty when the source changes, so forget their files too.
watch(source, () => {
  uploads.value = {}
})

const pickFile = (key: string, event: Event) => {
  const input = event.target as HTMLInputElement
  uploads.value[key] = input.files?.[0] ?? null
}

const submit = (): Promise<TaskPayload> => {
  if (source.value === 'upload') {
    const form = new FormData()
    const keys = chosen.value.database ? [...parts.value, 'config'] : parts.value
    for (const part of parts.value) form.append('parts', part)
    for (const key of keys) {
      const file = uploads.value[key]
      if (file) form.append(key, file)
    }
    return sitesApi.restoreUpload(target.value, form)
  }
  if (source.value === 'remote')
    return sitesApi.restore(target.value, {
      parts: parts.value,
      remote_site: remoteSite.value.trim(),
      password: password.value,
    })
  return sitesApi.restore(target.value, { parts: parts.value, source_site: sourceSite.value })
}

const restore = async () => {
  restoring.value = true
  error.value = ''
  try {
    const data = await submit()
    if (data.task_id) openTaskDetailPage(router, data.task_id)
    else error.value = apiErrorMessage(data, 'Could not start the restore.')
  } catch (e) {
    error.value = errorMessage(e, 'Could not start the restore.')
  } finally {
    restoring.value = false
  }
}

onMounted(loadSites)
</script>

<template>
  <div class="space-y-6">
    <Alert
      class="border border-outline-gray-2"
      theme="blue"
      title="Restoring replaces the data you select"
      :dismissible="false"
    >
      <template #description>
        <p class="text-ink-gray-6 text-p-sm">
          The site is backed up first and migrated after the restore. Restoring from another site
          uses a new backup of it. A remote site emails its Administrator about that backup.
        </p>
      </template>
    </Alert>

    <div class="space-y-4">
      <div class="flex sm:flex-row flex-col gap-4">
        <Select v-model="target" label="Restore into" :options="siteOptions" class="w-full" />
        <Select v-model="source" label="From" :options="SOURCES" class="w-full" />
      </div>

      <Select
        v-if="source === 'site'"
        v-model="sourceSite"
        label="Site"
        :options="sourceOptions"
        placeholder="Choose a site"
      />

      <div v-else-if="source === 'remote'" class="flex sm:flex-row flex-col gap-4">
        <TextInput v-model="remoteSite" label="Site" placeholder="erp.example.com" class="w-full" />
        <TextInput
          v-model="password"
          label="Administrator password"
          type="password"
          class="w-full"
        />
      </div>

      <div class="flex flex-col gap-2">
        <p class="text-ink-gray-5 text-xs">What to restore</p>
        <div v-for="item in PARTS" :key="item.part" class="flex items-center gap-4">
          <Checkbox v-model="chosen[item.part]" :label="item.label" class="w-32 shrink-0" />
          <input
            v-if="source === 'upload' && chosen[item.part]"
            type="file"
            :accept="item.accept"
            class="text-ink-gray-7 text-sm"
            @change="pickFile(item.part, $event)"
          />
        </div>
        <div v-if="source === 'upload' && chosen.database" class="flex items-center gap-4">
          <span class="w-32 shrink-0 text-ink-gray-7 text-sm">Site config (optional)</span>
          <input
            type="file"
            accept=".json"
            class="text-ink-gray-7 text-sm"
            @change="pickFile('config', $event)"
          />
        </div>
      </div>

      <ErrorMessage v-if="error" :message="error" />
      <div class="flex justify-end">
        <Button
          variant="solid"
          theme="red"
          :loading="restoring"
          :disabled="!isReady"
          @click="restore"
        >
          Restore
        </Button>
      </div>
    </div>
  </div>
</template>
