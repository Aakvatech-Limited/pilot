<script setup>
import { Button, ErrorMessage, SettingsBody, SettingsHeader } from 'frappe-ui'
import { computed, ref } from 'vue'
import { openExternal } from '../external'

const props = defineProps({ store: { type: Object, required: true } })

const context = computed(() => props.store.state.context || {})
const openingBilling = ref(false)
const billingError = ref('')

const links = computed(() => [
  {
    title: __('Open your server'),
    description: __('Deploys, scaling, SSH, backups, sites — the full server controls.'),
    label: __('Open server'),
    url: context.value.server_url,
  },
])

const openBilling = async () => {
  if (openingBilling.value) return
  openingBilling.value = true
  billingError.value = ''
  try {
    const response = context.value.account_url
      ? { url: context.value.account_url }
      : await props.store.api.getAccountUrl()
    if (!response?.url) throw new Error(__('Central is not configured.'))
    openExternal(response.url)
  } catch (exception) {
    billingError.value = props.store.api.getErrorMessage(exception)
  } finally {
    openingBilling.value = false
  }
}
</script>

<template>
  <SettingsHeader :title="__('Advanced')" :description="__('Deeper controls for your server.')" />

  <SettingsBody>
    <div class="divide-y divide-outline-gray-1 pt-4">
      <div
        v-for="link in links"
        :key="link.title"
        class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 py-5"
      >
        <p class="text-base font-semibold text-ink-gray-9">
          {{ link.title }}
        </p>

        <p class="mt-1 text-p-sm text-ink-gray-5">{{ link.description }}</p>

        <Button
          v-if="link.url"
          class="col-start-2 row-span-2 row-start-1"
          icon-right="arrow-up-right"
          @click="openExternal(link.url)"
        >
          {{ link.label }}
        </Button>

        <p v-else class="col-start-2 row-span-2 row-start-1 text-p-sm text-ink-gray-4">
          {{ __("Not configured") }}
        </p>
      </div>

      <div class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 py-5">
        <p class="text-base font-semibold text-ink-gray-9">
          {{ __("Account & billing") }}
        </p>

        <p class="mt-1 text-p-sm text-ink-gray-5">
          {{ __("Payment methods, invoices, billing email and account settings.") }}
        </p>

        <Button
          class="col-start-2 row-span-2 row-start-1"
          icon-right="arrow-up-right"
          :disabled="openingBilling"
          @click="openBilling"
        >
          {{ openingBilling ? __("Opening billing") : __("Manage billing") }}
        </Button>
        <ErrorMessage :message="billingError" class="col-span-2 mt-2" />
      </div>
    </div>
  </SettingsBody>
</template>
