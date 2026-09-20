<script setup>
import { Button, Dropdown, Tooltip } from 'frappe-ui'
import { computed, inject, ref } from 'vue'

const props = defineProps({
  app: { type: Object, required: true },
  pending: { type: String, default: '' },
  error: { type: String, default: '' },
})
const emit = defineEmits(['install', 'uninstall', 'update'])

const busy = computed(() => Boolean(props.pending))
const imageFailed = ref(false)
const overlayTarget = inject('overlayTarget', 'body')

const logoUrl = computed(() => {
  const url = String(props.app.logo_url || '').trim()
  return /^https?:\/\//i.test(url) && !imageFailed.value ? url : ''
})

const requiredVersion = computed(() => String(props.app.required_version || '').match(/\d+/)?.[0])
const incompatibleLabel = computed(() =>
  requiredVersion.value ? __('Needs Version {0}', [requiredVersion.value]) : __('Incompatible'),
)
const incompatibleReason = computed(() =>
  requiredVersion.value
    ? __("Needs Version {0} — change your server's version to install it", [requiredVersion.value])
    : __('Not available for this version of Frappe'),
)
</script>

<template>
  <div
    class="grid grid-cols-[auto_minmax(0,1fr)_auto_auto] items-center gap-x-1.5 border-b border-outline-gray-1 py-3.5"
  >
    <img
      v-if="logoUrl"
      class="row-span-2 mr-1.5 size-8 rounded-5 object-cover"
      :src="logoUrl"
      :alt="app.title"
      loading="lazy"
      decoding="async"
      @error="imageFailed = true"
    />

    <div
      v-else
      class="row-span-2 mr-1.5 grid size-8 place-items-center rounded-5 bg-surface-gray-2 text-sm-medium uppercase text-ink-gray-6"
    >
      {{ (app.title || "?").charAt(0) }}
    </div>

    <span class="truncate text-base-medium text-ink-gray-8" :title="app.title">
      {{ app.title }}
    </span>

    <span class="whitespace-nowrap text-p-sm tabular-nums text-ink-gray-5">
      <template v-if="app.installed && app.has_update">
        v{{ app.installed_version }}
        <span class="text-ink-green-7">→ v{{ app.latest_version }}</span>
      </template>

      <template v-else-if="app.installed && app.installed_version">
        v{{ app.installed_version }}
      </template>

      <template v-else-if="app.latest_version">v{{ app.latest_version }}</template>
    </span>

    <p
      class="col-span-2 col-start-2 mt-0.5 truncate text-p-sm text-ink-gray-5"
      :title="app.description"
    >
      {{ app.description }}
    </p>

    <div class="col-start-4 row-span-2 row-start-1 flex items-center gap-1">
      <Tooltip v-if="error && !busy" :text="error">
        <span
          class="lucide-triangle-alert size-3.5 text-ink-red-8"
          role="img"
          tabindex="0"
          :aria-label="error"
        />
      </Tooltip>

      <Tooltip v-if="!app.installed && !app.installable" :text="incompatibleReason">
        <span
          class="rounded-full bg-surface-gray-3 px-2.5 py-1 text-p-xs text-ink-gray-5"
          tabindex="0"
        >
          {{ incompatibleLabel }}
        </span>
      </Tooltip>

      <Button
        v-else-if="!app.installed"
        :disabled="busy"
        :loading="pending === 'install'"
        :label="pending === 'install' ? __('Installing') : __('Install')"
        @click="emit('install', app)"
      />

      <template v-else-if="app.has_update">
        <Button
          variant="solid"
          :disabled="busy"
          :loading="pending === 'update'"
          :label="pending === 'update' ? __('Updating') : __('Update')"
          @click="emit('update', app)"
        />

        <Dropdown
          align="end"
          :portal-to="overlayTarget"
          :options="[{ label: __('Uninstall'), onClick: () => emit('uninstall', app) }]"
        >
          <Button
            variant="ghost"
            icon="more-vertical"
            :disabled="busy"
            :label="__('More actions for {0}', [app.title])"
          />
        </Dropdown>
      </template>

      <Button
        v-else
        :disabled="busy"
        :loading="pending === 'uninstall'"
        :label="pending === 'uninstall' ? __('Uninstalling') : __('Uninstall')"
        @click="emit('uninstall', app)"
      />
    </div>
  </div>
</template>
