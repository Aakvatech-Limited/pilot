<script setup>
import { Button, ErrorMessage, SettingsBody, SettingsHeader, SettingsRow } from 'frappe-ui'
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
  <SettingsHeader class="!px-4 !pt-6 sm:!px-10 sm:!pt-9 relative z-10 pb-6 bg-surface-elevation-1">
    <h2 class="text-lg-semibold text-ink-gray-8">{{ __('Advanced') }}</h2>

    <p class="mt-1 text-base leading-5 text-ink-gray-6">{{ __('Deeper controls for your server.') }}</p>
  </SettingsHeader>

  <SettingsBody viewport-class="px-4 pb-10 sm:px-10 sm:pb-16">
    <div class="divide-y divide-outline-gray-1 border-t border-outline-gray-1">
      <SettingsRow
        v-for="link in links"
        :key="link.title"
        label-for=""
        :title="link.title"
        :description="link.description"
      >
        <Button
          v-if="link.url"
          icon-right="arrow-up-right"
          :label="link.label"
          @click="openExternal(link.url)"
        />

        <span v-else class="text-p-sm text-ink-gray-5">{{ __("Not configured") }}</span>
      </SettingsRow>

      <SettingsRow
        label-for=""
        :title="__('Account & billing')"
        :description="
          __('Payment methods, invoices, billing email and account settings.')
        "
      >
        <Button
          icon-right="arrow-up-right"
          :disabled="openingBilling"
          :label="openingBilling ? __('Opening billing') : __('Manage billing')"
          @click="openBilling"
        />
      </SettingsRow>
    </div>

    <ErrorMessage :message="billingError" class="mt-2" />
  </SettingsBody>
</template>
