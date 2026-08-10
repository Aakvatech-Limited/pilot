import test from 'node:test'
import assert from 'node:assert/strict'

import { branchComboboxOptions } from './branchComboboxOptions.js'

const BRANCHES = ['version-16', 'develop']

function lastRow(options) {
  return options.at(-1)
}

test('maps branches to options and appends the typed-branch row', () => {
  const options = branchComboboxOptions(BRANCHES, 'develop', () => {})
  assert.deepEqual(
    options.slice(0, -1),
    BRANCHES.map((name) => ({ label: name, value: name })),
  )
  assert.equal(lastRow(options).type, 'custom')
  assert.equal(lastRow(options).slot, 'typed-branch')
})

test('prepends a selected branch missing from the list', () => {
  const options = branchComboboxOptions(BRANCHES, 'my-fork-feature', () => {})
  assert.deepEqual(options[0], { label: 'my-fork-feature', value: 'my-fork-feature' })
  assert.equal(options.length, BRANCHES.length + 2)
})

test('typed-branch row shows only for a new non-empty query', () => {
  const { condition } = lastRow(branchComboboxOptions(BRANCHES, 'my-fork-feature', () => {}))
  assert.equal(condition({ query: '' }), false)
  assert.equal(condition({ query: '   ' }), false)
  assert.equal(condition({ query: 'develop' }), false)
  assert.equal(condition({ query: ' my-fork-feature ' }), false)
  assert.equal(condition({ query: 'hotfix-1' }), true)
})

test('typed-branch row commits the trimmed query', () => {
  const picked = []
  const { onClick } = lastRow(branchComboboxOptions(BRANCHES, 'develop', (b) => picked.push(b)))
  onClick({ query: ' hotfix-1 ' })
  onClick({ query: '   ' })
  assert.deepEqual(picked, ['hotfix-1'])
})
