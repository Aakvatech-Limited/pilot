<script setup>
import { Button, ErrorMessage, SettingsBody, SettingsHeader } from 'frappe-ui'
import { computed, ref, watch } from 'vue'
import AddPaymentCard from '../components/AddPaymentCard.vue'
import BillingProfileCard from '../components/BillingProfileCard.vue'
import PanelState from '../components/PanelState.vue'
import { openExternal } from '../external'

const props = defineProps({
  store: { type: Object, required: true },
  active: { type: Boolean, default: false },
})
const store = props.store

const flow = ref('')
const removing = ref(false)
const removeError = ref('')
const openingChangePlan = ref(false)
const changePlanError = ref('')

const load = async () => {
  try {
    await store.api.reconcilePaymentSetup()
  } catch {}
  await store.loadBilling(true)
}

watch(
  () => props.active,
  (active) => {
    if (active) load()
  },
  { immediate: true },
)

const billing = computed(() => store.state.billing)
const error = computed(() => store.state.billingError)
const loadFailed = computed(() => Boolean(error.value) && !billing.value)
const plan = computed(() => billing.value?.plan)

const planSubtitle = computed(() => {
  if (plan.value?.subtitle) return plan.value.subtitle
  return Object.values(plan.value?.specs || {})
    .filter(Boolean)
    .join(' · ')
})

const meters = computed(() => {
  const usage = billing.value?.usage
  if (Array.isArray(usage) && usage.length) {
    return usage.map((m) => ({ ...m, percent: clamp(m.percent) }))
  }
  const specs = plan.value?.specs || {}
  return [
    { name: __('CPU'), percent: 0, detail: specs.cpu || __('Not reported') },
    {
      name: __('Memory'),
      percent: 0,
      detail: specs.memory || __('Not reported'),
    },
    {
      name: __('Storage'),
      percent: 0,
      detail: specs.storage || __('Not reported'),
    },
  ]
})

const clamp = (percent) => {
  return Math.max(0, Math.min(100, Math.round(Number(percent) || 0)))
}

const startPayment = () => {
  removeError.value = ''
  flow.value = billing.value?.profile_complete ? 'payment' : 'profile'
}

const removeCard = async () => {
  if (removing.value) return
  removing.value = true
  removeError.value = ''
  try {
    await store.api.removePaymentMethod(billing.value.payment_method.name)
    await store.loadBilling(true)
  } catch (exception) {
    removeError.value = store.api.getErrorMessage(exception)
  } finally {
    removing.value = false
  }
}

const openChangePlan = async () => {
  if (openingChangePlan.value) return
  openingChangePlan.value = true
  changePlanError.value = ''
  try {
    const response = store.state.context?.account_url
      ? { url: store.state.context.account_url }
      : await store.api.getAccountUrl()
    if (!response?.url) throw new Error(__('Central is not configured.'))
    openExternal(response.url)
  } catch (exception) {
    changePlanError.value = store.api.getErrorMessage(exception)
  } finally {
    openingChangePlan.value = false
  }
}
</script>

<template>
  <SettingsHeader
    :title="__('Billing')"
    :description="__('Your plan, usage, credit and payment method.')"
  />

  <SettingsBody>
    <PanelState
      class="pt-8"
      :loading="!billing && !error"
      :error="loadFailed ? error : ''"
      :title="__(`Couldn't load billing`)"
      @retry="load"
    >
      <div
        v-if="!plan"
        class="grid grid-cols-[auto_minmax(0,1fr)] items-start gap-x-3 rounded-7 border border-dashed border-outline-gray-3 p-4"
      >
        <span class="lucide-wallet mt-0.5 size-4 text-ink-gray-5" aria-hidden="true" />

        <p class="text-base font-medium text-ink-gray-9">
          {{ __("Billing isn't available for this site yet") }}
        </p>

        <p class="col-start-2 mt-1 text-p-sm text-ink-gray-6">
          {{ __(
              "This site isn't connected to a billing account, or the connection isn't ready.",
            ) }}
        </p>

        <Button
          class="col-start-2 mt-3 justify-self-start"
          icon-right="arrow-up-right"
          :disabled="openingChangePlan"
          @click="openChangePlan"
        >
          {{ openingChangePlan ? __("Opening…") : __("View plans") }}
        </Button>
        <ErrorMessage :message="changePlanError" class="col-start-2 mt-2" />
      </div>

      <div v-else class="space-y-4">
        <ErrorMessage :message="loadFailed ? '' : error" />

        <section
          class="grid grid-cols-[minmax(0,1fr)_auto] items-start gap-x-4 rounded-7 border border-outline-gray-2 p-4"
        >
          <p class="text-p-sm text-ink-gray-5">{{ __("Plan") }}</p>

          <p class="text-lg font-semibold text-ink-gray-9">
            {{ plan.name || __("Current plan") }}
          </p>

          <p class="text-p-sm text-ink-gray-6">{{ planSubtitle }}</p>

          <Button
            class="col-start-2 row-span-3 row-start-1"
            icon-right="arrow-up-right"
            :disabled="openingChangePlan"
            @click="openChangePlan"
          >
            {{ openingChangePlan ? __("Opening…") : __("Change plan") }}
          </Button>
          <ErrorMessage :message="changePlanError" class="col-span-2 mt-2" />

          <div class="col-span-2 mt-3 grid grid-cols-3 gap-5">
            <div
              v-for="meter in meters"
              :key="meter.name"
              class="grid grid-cols-[1fr_auto] items-center text-p-sm"
            >
              <span class="text-ink-gray-7">{{ meter.name }}</span>
              <span class="font-medium text-ink-gray-9"> {{ meter.percent }}% </span>

              <div
                class="col-span-2 my-1 h-1.5 overflow-hidden rounded-full bg-surface-gray-3"
                role="progressbar"
                :aria-label="meter.name"
                aria-valuemin="0"
                aria-valuemax="100"
                :aria-valuenow="meter.percent"
              >
                <div
                  class="h-full rounded-full bg-surface-gray-7"
                  :style="{ width: `${meter.percent}%` }"
                />
              </div>

              <p class="col-span-2 text-p-xs text-ink-gray-5">
                {{ meter.detail }}
              </p>
            </div>
          </div>
        </section>

        <div class="grid grid-cols-2 gap-3">
          <section class="rounded-7 border border-outline-gray-2 p-4">
            <p class="text-p-sm text-ink-gray-5">
              {{ __("Estimated this cycle") }}
            </p>

            <p class="mt-1 text-2xl font-semibold text-ink-gray-9">
              {{ billing.estimate?.amount ?? "—" }}
            </p>

            <p class="mt-1 text-p-sm text-ink-gray-6">
              {{ billing.estimate?.note }}
            </p>
          </section>

          <section class="rounded-7 border border-outline-gray-2 p-4">
            <p class="text-p-sm text-ink-gray-5">{{ __("Trial credit") }}</p>

            <p class="mt-1 text-2xl font-semibold text-ink-gray-9">
              {{ billing.credit?.amount ?? "—" }}
            </p>

            <p
              class="mt-1 flex items-center gap-1.5 text-p-sm"
              :class="
                billing.credit?.warning ? 'text-ink-amber-8' : 'text-ink-gray-6'
              "
            >
              <span
                v-if="billing.credit?.warning"
                class="lucide-triangle-alert size-3.5"
                aria-hidden="true"
              />
              {{ billing.credit?.note }}
            </p>
          </section>
        </div>

        <BillingProfileCard
          v-if="flow === 'profile'"
          :store="store"
          @close="flow = ''"
          @saved="flow = 'payment'"
        />

        <AddPaymentCard v-else-if="flow === 'payment'" :store="store" @close="flow = ''" />

        <section
          v-else
          class="grid items-start gap-x-3 rounded-7 border border-dashed border-outline-gray-3 p-4"
          :class="
            billing.payment_method
              ? 'grid-cols-[auto_minmax(0,1fr)_auto]'
              : 'grid-cols-[auto_minmax(0,1fr)]'
          "
        >
          <span class="lucide-credit-card mt-0.5 size-4 text-ink-gray-5" aria-hidden="true" />

          <p class="text-base font-medium text-ink-gray-9">
            {{ billing.payment_method
                ? billing.payment_method.label
                : __("No payment method yet") }}
          </p>

          <p class="col-start-2 mt-1 text-p-sm text-ink-gray-6">
            {{ billing.payment_method
                ? __("Used for your monthly bill.")
                : __(
                    "You're on trial credit. Add a payment method to keep this site running after it.",
                  ) }}
          </p>

          <ErrorMessage :message="removeError" class="col-start-2 mt-2" />
          <Button
            v-if="billing.payment_method"
            class="col-start-3 row-span-3 row-start-1 ml-1 self-center"
            :loading="removing"
            @click="removeCard"
          >
            {{ __("Remove") }}
          </Button>
          <Button
            v-else
            class="col-span-2 mt-3 justify-self-start"
            variant="solid"
            icon-left="plus"
            @click="startPayment"
          >
            {{ __("Add payment method") }}
          </Button>
        </section>
      </div>
    </PanelState>
  </SettingsBody>
</template>
