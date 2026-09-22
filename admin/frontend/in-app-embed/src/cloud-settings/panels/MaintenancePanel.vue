<script setup lang="ts">
import { Button, ErrorMessage, SettingsRow } from 'frappe-ui'
import { onBeforeUnmount, ref } from 'vue'
import Panel from '../components/Panel.vue'
import { type Store, waitForTask } from '../store'

interface Props {
  store: Store
}

const props = defineProps<Props>()
const store = props.store

const actions = [
  {
    key: 'clear-cache',
    title: __('Clear cache'),
    description: __('Drops cached pages and settings. Safe to run any time something looks stale.'),
    label: __('Clear cache'),
    done: __('Cache cleared.'),
    run: () => store.api.clearCache(),
  },
  {
    key: 'migrate',
    title: __('Run migrations'),
    description: __(
      'Applies pending database changes from your apps. The site can be slow while it runs.',
    ),
    label: __('Migrate'),
    done: __('Migrations finished.'),
    run: () => store.api.migrate(),
  },
]

const running = ref('')
const error = ref('')

let gone = false

onBeforeUnmount(() => (gone = true))

const run = async (action) => {
  running.value = action.key
  error.value = ''

  try {
    const { task_id } = await action.run()
    const outcome = await waitForTask(task_id, () => gone)

    if (outcome === 'failed' || outcome === 'error') {
      throw new Error(__("Couldn't finish: {0}.", [action.title]))
    }

    frappe.show_alert({ message: action.done, indicator: 'green' })
  } catch (exception) {
    error.value = store.api.getErrorMessage(exception)
  } finally {
    running.value = ''
  }
}
</script>

<template>
  <Panel :title="__('Maintenance')" :description="__('Housekeeping tasks for your site.')">
    <div class="divide-y divide-outline-gray-1 border-t border-outline-gray-1">
      <SettingsRow
        v-for="action in actions"
        :key="action.key"
        label-for=""
        :title="action.title"
        :description="action.description"
      >
        <Button
          :loading="running === action.key"
          :disabled="Boolean(running) && running !== action.key"
          :label="action.label"
          @click="run(action)"
        />
      </SettingsRow>
    </div>

    <ErrorMessage :message="error" class="mt-2" />
  </Panel>
</template>
