<script setup lang="ts">
import { Button, ErrorMessage } from 'frappe-ui'
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { apiErrorMessage } from '@/api/client'
import { tasksApi } from '@/api/tasks'
import SettingsRow from '@/components/settings/SettingsRow.vue'
import { errorMessage } from '@/utils/error'
import { openTaskDetailPage } from '@/utils/taskRoute'

const router = useRouter()
const running = ref('')
const error = ref('')

const run = async (command: 'build' | 'clear-cache') => {
  error.value = ''
  running.value = command
  try {
    const data = await tasksApi.run(command)
    if (data.task_id) openTaskDetailPage(router, data.task_id)
    else error.value = apiErrorMessage(data, 'Could not start the task.')
  } catch (e) {
    error.value = errorMessage(e, 'Could not start the task.')
  } finally {
    running.value = ''
  }
}
</script>

<template>
  <SettingsRow label="Build assets" description="Rebuild JS and CSS for every app.">
    <Button :loading="running === 'build'" @click="run('build')">Build</Button>
  </SettingsRow>

  <SettingsRow label="Clear cache" description="Clear the cache of every site.">
    <Button :loading="running === 'clear-cache'" @click="run('clear-cache')">Clear</Button>
  </SettingsRow>

  <ErrorMessage v-if="error" :message="error" class="px-2.5 py-2" />
</template>
