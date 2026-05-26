import test from 'node:test'
import assert from 'node:assert/strict'

import { buildPrintSessionPool, nextPrintSessionIdAfterComplete, orderSessionsByCreatedAt } from './printQueueUtils.js'

test('orderSessionsByCreatedAt sorts oldest first for print work', () => {
  const ordered = orderSessionsByCreatedAt([
    { session_id: 'b', created_at: '2026-05-17T10:00:00' },
    { session_id: 'a', created_at: '2026-05-17T09:00:00' },
  ])

  assert.deepEqual(ordered.map((item) => item.session_id), ['a', 'b'])
})

test('buildPrintSessionPool prioritizes print-ready before processing and history states', () => {
  const pool = buildPrintSessionPool({
    printReadySessions: [{ session_id: 'ready-2', created_at: '2026-05-17T11:00:00' }, { session_id: 'ready-1', created_at: '2026-05-17T10:00:00' }],
    processingSessions: [{ session_id: 'processing-1', created_at: '2026-05-17T09:30:00' }],
    completedSessions: [{ session_id: 'completed-1', created_at: '2026-05-17T08:00:00' }],
    erroredSessions: [{ session_id: 'error-1', created_at: '2026-05-17T12:00:00' }],
  })

  assert.deepEqual(pool.map((item) => item.session_id), ['ready-1', 'ready-2', 'processing-1', 'error-1', 'completed-1'])
})

test('nextPrintSessionIdAfterComplete returns the next available session', () => {
  const nextId = nextPrintSessionIdAfterComplete('ready-1', [
    { session_id: 'ready-1' },
    { session_id: 'ready-2' },
    { session_id: 'processing-1' },
  ])

  assert.equal(nextId, 'ready-2')
})
