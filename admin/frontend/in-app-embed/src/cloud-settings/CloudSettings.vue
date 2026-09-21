<script setup>
import {
  Badge,
  Button,
  SettingsContent,
  SettingsDialog,
  SettingsNavGroup,
  SettingsNavItem,
  SettingsPanel,
  SettingsSidebar,
} from 'frappe-ui'
import { ConfigProvider } from 'reka-ui'
import { computed, onBeforeUnmount, onMounted, provide, ref, watch } from 'vue'

import FrappeCloudLogo from './components/FrappeCloudLogo.vue'
import AdvancedPanel from './panels/AdvancedPanel.vue'
import BillingPanel from './panels/BillingPanel.vue'
import DomainsPanel from './panels/DomainsPanel.vue'
import MarketplacePanel from './panels/MarketplacePanel.vue'
import { createStore } from './store'
import TailwindStyles from './TailwindStyles.vue'

const props = defineProps({
  context: { type: Object, default: () => ({}) },
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['close'])

const TABS = [
  {
    value: 'billing',
    label: __('Billing'),
    icon: 'lucide-credit-card',
    component: BillingPanel,
  },
  {
    value: 'marketplace',
    label: __('Marketplace'),
    icon: 'lucide-store',
    component: MarketplacePanel,
  },
  {
    value: 'domains',
    label: __('Domains'),
    icon: 'lucide-globe-code',
    component: DomainsPanel,
  },
  {
    value: 'advanced',
    label: __('Advanced'),
    icon: 'lucide-bolt',
    component: AdvancedPanel,
  },
]

const overlays = ref(null)
provide('overlayTarget', overlays)

const isOpen = ref(props.open)
const tab = ref(TABS[0].value)
const store = ref(createStore(props.context))

watch(
  () => props.open,
  (open) => {
    if (open) {
      store.value = createStore(props.context)
      tab.value = TABS[0].value
    }
    isOpen.value = open
  },
)
watch(isOpen, (open) => !open && emit('close'))

const isDark = ref(document.documentElement.dataset.theme === 'dark')
let themeWatcher
onMounted(() => {
  themeWatcher = new MutationObserver(() => {
    isDark.value = document.documentElement.dataset.theme === 'dark'
  })
  themeWatcher.observe(document.documentElement, {
    attributeFilter: ['data-theme'],
  })
})
onBeforeUnmount(() => themeWatcher?.disconnect())
const updateCount = computed(() => store.value.state.marketplace?.update_count || 0)
const needsBilling = computed(() => Boolean(store.value.state.billing?.credit?.warning))
</script>

<template>
  <ConfigProvider :teleport-to="overlays">
    <SettingsDialog
      v-model:open="isOpen"
      v-model:tab="tab"
      size="5xl"
      :keyboard-shortcut="false"
      :unmount-on-hide="false"
    >
      <template #title>{{ __("Cloud Settings") }}</template>

      <SettingsSidebar class="!border-0 !border-r  border-outline-gray-2">
        <SettingsNavGroup>
          <p class="mb-1 flex h-7 items-center px-2 text-base text-ink-gray-7">
            <FrappeCloudLogo class="mr-2 size-4 rounded-2" />
            {{ __("Cloud Settings") }}
          </p>
          <SettingsNavItem v-for="item in TABS" :key="item.value" :value="item.value">
            <template #prefix>
              <span :class="[item.icon, 'size-4 shrink-0 text-ink-gray-6']" />
            </template>
            {{ item.label }}

            <template #suffix>
              <span
                v-if="item.value === 'billing' && needsBilling"
                class="size-1.5 rounded-full bg-surface-amber-3"
                :aria-label="__('Billing needs attention')"
              />

              <Badge
                v-else-if="item.value === 'marketplace' && updateCount"
                theme="gray"
                :label="String(updateCount)"
              />
            </template>
          </SettingsNavItem>
        </SettingsNavGroup>
      </SettingsSidebar>

      <SettingsContent class="relative">
        <Button
          variant="ghost"
          icon="x"
          :label="__('Close')"
          class="absolute right-4 top-3.5 z-10"
          @click="isOpen = false"
        />

        <SettingsPanel v-for="item in TABS" :key="item.value" :value="item.value">
          <component :is="item.component" :store="store" :active="tab === item.value" />
        </SettingsPanel>
      </SettingsContent>
    </SettingsDialog>

    <div ref="overlays" :data-theme="isDark ? 'dark' : 'light'" />

    <TailwindStyles />
  </ConfigProvider>
</template>
