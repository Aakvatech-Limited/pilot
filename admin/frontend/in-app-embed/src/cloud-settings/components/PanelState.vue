<script setup>
import { Button, Skeleton } from 'frappe-ui'

defineProps({
  loading: { type: Boolean, default: false },
  error: { type: String, default: '' },
  title: { type: String, default: '' },
})
defineEmits(['retry'])
</script>

<template>
  <div v-if="loading" class="mt-6 space-y-3" role="status" :aria-label="__('Loading')">
    <Skeleton v-for="n in 3" :key="n" class="h-24 rounded-6" />
  </div>

  <div
    v-else-if="error"
    class="mt-6 flex min-h-64 flex-col items-center justify-center rounded-6 border border-dashed border-outline-gray-3 px-6 py-12 text-center"
  >
    <div
      class="flex size-10 items-center justify-center rounded-6 bg-surface-gray-2 text-ink-gray-5"
    >
      <span class="lucide-triangle-alert size-4" aria-hidden="true" />
    </div>

    <p class="mt-4 text-base-medium text-ink-gray-8">
      {{ title || __("Couldn't load this section") }}
    </p>

    <p class="mt-1 max-w-sm text-p-sm text-ink-gray-5">{{ error }}</p>

    <Button class="mt-5" :label="__('Try again')" @click="$emit('retry')" />
  </div>

  <slot v-else />
</template>
