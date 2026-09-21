<script setup>
import { Badge, Button, ErrorMessage, SettingsBody, SettingsHeader, TextInput } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import PanelState from '../components/PanelState.vue'

const props = defineProps({
  store: { type: Object, required: true },
  active: { type: Boolean, default: false },
})
const store = props.store

const input = ref('')
const pendingDomain = ref('')
const dnsRecords = ref([])
const working = ref(false)

watch(
  () => props.active,
  (active) => {
    if (active) store.loadDomains()
  },
  { immediate: true },
)

const domains = computed(() => {
  const rows = store.state.domains?.domains
  const routes = rows
    ?.filter((row) => typeof row.domain === 'object')
    .map(({ domain }) => ({ ...domain, is_default: domain.is_site }))

  return routes?.length ? routes : rows
})
const error = computed(() => store.state.domainsError)
const loadFailed = computed(() => Boolean(error.value) && !domains.value)
const domainPattern = /^(?=.{1,253}$)(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,63}$/

const normalizedDomain = computed(() =>
  input.value
    .trim()
    .toLowerCase()
    .replace(/^https?:\/\//, '')
    .replace(/[/?#].*$/, '')
    .replace(/\.$/, ''),
)

const domainError = computed(() => {
  const domain = normalizedDomain.value
  if (!domain) return ''
  if (!domainPattern.test(domain)) return __('Enter a valid domain, like shop.example.com.')
  if ((domains.value || []).some((row) => row.domain === domain)) {
    return __('{0} is already added.', [domain])
  }
  return ''
})

const canAdd = computed(
  () => Boolean(normalizedDomain.value) && !domainError.value && !working.value,
)

const previewDomain = async () => {
  const domain = normalizedDomain.value
  if (!canAdd.value) return
  await run(async () => {
    const response = await store.api.getDomainDnsRecords(domain)
    dnsRecords.value = response.records || []
    pendingDomain.value = domain
    if (!dnsRecords.value.length) await confirmAdd()
  })
}

const confirmAdd = async () => {
  const domain = pendingDomain.value || normalizedDomain.value
  if (!domain) return
  await run(async () => {
    await store.api.addDomain(domain)
    clearPreview()
    await store.loadDomains(true)
  })
}

const makePrimary = (domain) =>
  run(async () => {
    await store.api.setPrimaryDomain(domain)
    await store.loadDomains(true)
  })

const remove = (domain) =>
  run(async () => {
    await store.api.removeDomain(domain)
    await store.loadDomains(true)
  })

const run = async (action) => {
  working.value = true
  store.state.domainsError = ''
  try {
    await action()
  } catch (exception) {
    store.state.domainsError = store.api.getErrorMessage(exception)
  } finally {
    working.value = false
  }
}

const clearPreview = () => {
  dnsRecords.value = []
  pendingDomain.value = ''
  input.value = ''
}
</script>

<template>
  <SettingsHeader class="!px-4 !pt-6 sm:!px-10 sm:!pt-9 relative z-10 pb-6 bg-surface-elevation-1">
    <h2 class="text-lg-semibold text-ink-gray-8">{{ __('Domains') }}</h2>

    <p class="mt-1 text-base leading-5 text-ink-gray-6">
      {{ __('The addresses this site answers on.') }}
    </p>
  </SettingsHeader>

  <SettingsBody viewport-class="px-4 pb-10 sm:px-10 sm:pb-16">
    <PanelState
      :loading="!domains && !error"
      :error="loadFailed ? error : ''"
      :title="__(`Couldn't load domains`)"
      @retry="store.loadDomains(true)"
    >
      <div class="flex items-end gap-2">
        <TextInput
          v-model="input"
          class="flex-1 [&_[data-slot='label']]:leading-5"
          :label="__('Add a domain')"
          :placeholder="__('shop.mycompany.in')"
          :disabled="working"
          @keydown.enter="previewDomain"
        />

        <Button
          :disabled="!canAdd"
          :loading="working && !pendingDomain"
          :label="__('Add')"
          @click="previewDomain"
        />
      </div>

      <ErrorMessage class="mt-2" :message="domainError || error" />

      <section v-if="dnsRecords.length" class="mt-6 rounded-6 border border-outline-gray-2 p-5">
        <h2 class="text-base-semibold text-ink-gray-8">{{ pendingDomain }}</h2>

        <p class="mt-0.5 text-p-sm text-ink-gray-5">
          {{ __("Add these DNS records at your provider, then continue.") }}
        </p>

        <dl class="mt-4 divide-y divide-outline-gray-1 border-t border-outline-gray-1">
          <div
            v-for="(record, index) in dnsRecords"
            :key="index"
            class="grid grid-cols-[4rem_minmax(0,1fr)] items-baseline gap-x-3 py-3 sm:grid-cols-[4rem_minmax(0,1fr)_minmax(0,1.4fr)]"
          >
            <dt class="text-sm-medium text-ink-gray-8">{{ record.type }}</dt>
            <dd class="truncate text-p-sm text-ink-gray-5">{{ record.host }}</dd>
            <dd class="col-start-2 truncate text-p-sm text-ink-gray-5 sm:col-start-3">
              {{ record.value }}
            </dd>
          </div>
        </dl>

        <div class="mt-4 flex justify-end gap-2">
          <Button :disabled="working" :label="__('Cancel')" @click="clearPreview" />

          <Button
            variant="solid"
            :loading="working"
            :label="__('Add domain')"
            @click="confirmAdd"
          />
        </div>
      </section>

      <div class="mt-6 space-y-2">
        <div
          v-for="domain in domains"
          :key="domain.domain"
          class="grid grid-cols-[minmax(0,auto)_auto_1fr_auto] items-center gap-x-1.5 rounded-6 border border-outline-gray-2 p-4 dark:bg-surface-gray-2"
        >
          <p class="truncate text-base-medium text-ink-gray-8">{{ domain.domain }}</p>

          <Badge v-if="domain.is_primary" theme="green" size="sm" :label="__('Primary')" />

          <Badge v-else-if="domain.is_default" size="sm" :label="__('Included')" />

          <p
            class="col-span-3 col-start-1 mt-1 flex items-center gap-1.5 text-p-sm text-ink-gray-5"
          >
            <span class="lucide-lock size-3.5 shrink-0 text-ink-green-7" aria-hidden="true" />
            {{ __("Managed SSL") }}
          </p>

          <div class="col-start-4 row-span-2 row-start-1 flex items-center gap-2">
            <Button
              v-if="!domain.is_primary"
              :disabled="working"
              :label="__('Make primary')"
              @click="makePrimary(domain.domain)"
            />

            <Button
              v-if="!domain.is_default"
              :disabled="working"
              :label="__('Remove')"
              @click="remove(domain.domain)"
            />
          </div>
        </div>
      </div>

      <p v-if="(domains || []).length <= 1" class="mt-6 text-p-sm text-ink-gray-5">
        {{ __(
              "No custom domains yet. Add one above and we'll handle SSL once DNS checks out.",
            ) }}
      </p>
    </PanelState>
  </SettingsBody>
</template>
