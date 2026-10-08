import assert from 'node:assert/strict'
import test from 'node:test'

import { processLine, processPlainLine } from './ansi.ts'

test('copied logs preserve literal traceback text instead of HTML markup', () => {
  const raw = '\x1b[31m  File "<stdin>", line 1: a & b\x1b[0m'
  assert.equal(processPlainLine(raw), '  File "<stdin>", line 1: a & b')
  assert.match(processLine(raw), /<span/)
})

test('copied logs match the visible progress update', () => {
  assert.equal(
    processPlainLine('Downloading 10%\r\x1b[32mDownloading 100%\x1b[0m\r'),
    'Downloading 100%',
  )
  assert.equal(processPlainLine('  [redacted]'), '  [redacted]')
  assert.equal(processPlainLine(''), '')
})
