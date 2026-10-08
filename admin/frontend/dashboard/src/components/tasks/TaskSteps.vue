<script setup lang="ts">
import { computed, toRef } from 'vue'

import CopyBtn from '@/components/common/CopyBtn.vue'
import LogView from '@/components/logs/LogView.vue'
import TaskStep from '@/components/tasks/TaskStep.vue'

import { STEP_MARKER_RE, type StepSection, useTaskSteps } from '@/composables/tasks/useTaskSteps'
import { processLine, processPlainLine } from '@/utils/ansi'

interface Props {
  rawLines?: string[]
  streaming?: boolean
  taskStatus?: string
  emptyText?: string
}

const props = withDefaults(defineProps<Props>(), {
  rawLines: () => [],
  streaming: false,
  taskStatus: '',
  emptyText: 'No output.',
})

const rawLinesRef = toRef(props, 'rawLines')
const streamingRef = toRef(props, 'streaming')
const taskRef = computed(() => ({ status: props.taskStatus }))

const { stepSections, hasSteps, stepDuration } = useTaskSteps(rawLinesRef, streamingRef, taskRef)
const processedLines = computed(() => props.rawLines.map(processLine))
const logText = computed(() => props.rawLines.map(processPlainLine).join('\n'))

const sectionRawLines = (section: StepSection) => {
  return props.rawLines
    .slice(section.lineStart, section.lineEnd)
    .filter((line) => !STEP_MARKER_RE.test(line))
}

const sectionHasOutput = (section: StepSection) => {
  return props.rawLines
    .slice(section.lineStart, section.lineEnd)
    .some((line) => line.trim() && !STEP_MARKER_RE.test(line))
}
</script>

<template>
  <div v-if="logText.trim()" class="flex justify-end mb-2">
    <CopyBtn
      :text="logText"
      label="Copy logs"
      class="flex items-center gap-1.5 px-2 py-1 rounded-4 text-sm text-ink-gray-7 hover:bg-surface-gray-1"
    />
  </div>
  <div
    v-if="hasSteps"
    class="flex flex-col gap-1 p-1 border border-outline-gray-2 rounded-6 min-w-0"
  >
    <TaskStep
      v-for="section in stepSections"
      :key="section.key"
      :label="section.label"
      :status="section.status"
      :duration="stepDuration(section)"
      :lines="sectionRawLines(section).map(processLine)"
      :raw-lines="sectionRawLines(section)"
      :has-output="sectionHasOutput(section)"
      :streaming="streaming && section.status === 'running'"
    />
  </div>

  <LogView v-else :lines="processedLines" :streaming="streaming" :empty-text="emptyText" />
</template>
