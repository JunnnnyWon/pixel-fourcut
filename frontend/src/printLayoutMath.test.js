import test from 'node:test'
import assert from 'node:assert/strict'

import {
  applyDragDelta,
  applyResizeDelta,
  clampScale,
  getCoverSize,
  getScalePercent,
  scaleFromPercent,
} from './printLayoutMath.js'

test('scale percent helpers map between 0-100 and internal 1.0-2.0 scale', () => {
  assert.equal(getScalePercent(1), 0)
  assert.equal(getScalePercent(1.57), 57)
  assert.equal(scaleFromPercent(0), 1)
  assert.equal(scaleFromPercent(100), 2)
})

test('drag delta stays in logical slot coordinates regardless of preview scale', () => {
  const next = applyDragDelta(
    { offset_x: 10, offset_y: -20 },
    52,
    -26,
    2,
  )

  assert.deepEqual(next, { offset_x: 36, offset_y: -33 })
})

test('resize from south-east handle increases scale and keeps north-west corner anchored', () => {
  const next = applyResizeDelta({
    origin: { offset_x: 0, offset_y: 0 },
    handle: { sx: 1, sy: 1 },
    baseSize: { width: 200, height: 100 },
    startScale: 1,
    deltaX: 80,
    deltaY: 40,
    previewScale: 1,
  })

  assert.equal(next.scale, 1.4)
  assert.deepEqual(next, { scale: 1.4, offset_x: 40, offset_y: 20 })
})

test('resize from north-west handle moves center negative so opposite corner remains fixed', () => {
  const next = applyResizeDelta({
    origin: { offset_x: 0, offset_y: 0 },
    handle: { sx: -1, sy: -1 },
    baseSize: { width: 200, height: 100 },
    startScale: 1,
    deltaX: -80,
    deltaY: -40,
    previewScale: 1,
  })

  assert.equal(next.scale, 1.4)
  assert.deepEqual(next, { scale: 1.4, offset_x: -40, offset_y: -20 })
})

test('resize is clamped to 0-100 percent extra scale range', () => {
  const next = applyResizeDelta({
    origin: { offset_x: 0, offset_y: 0 },
    handle: { sx: 1, sy: 1 },
    baseSize: { width: 200, height: 100 },
    startScale: 1.9,
    deltaX: 1000,
    deltaY: 1000,
    previewScale: 1,
  })

  assert.equal(next.scale, 2)
  assert.equal(getScalePercent(next.scale), 100)
  assert.equal(clampScale(9), 2)
})

test('cover sizing keeps image filling the target slot', () => {
  const next = getCoverSize(
    { width: 300, height: 600 },
    { width: 500, height: 300 },
  )

  assert.deepEqual(next, { width: 500, height: 1000 })
})
