import test from 'node:test'
import assert from 'node:assert/strict'

import { getAdminHeroState } from './adminHeroState.js'

test('reviewing with a selected shot and no active preset explains the real blocking reason', () => {
  const state = getAdminHeroState({
    currentSession: { phase: 'reviewing' },
    selectedShot: { shot_id: 'shot-001' },
    activePreset: null,
    comfyOnline: true,
  })

  assert.equal(state.actionKind, 'run')
  assert.equal(state.disabled, true)
  assert.equal(state.buttonLabel, '프리셋 활성화 필요')
})

test('reviewing with a selected shot and offline ComfyUI explains the connection requirement', () => {
  const state = getAdminHeroState({
    currentSession: { phase: 'reviewing' },
    selectedShot: { shot_id: 'shot-001' },
    activePreset: 'default',
    comfyOnline: false,
  })

  assert.equal(state.actionKind, 'run')
  assert.equal(state.disabled, true)
  assert.equal(state.buttonLabel, 'ComfyUI 연결 필요')
})

test('reviewing with a selected shot, active preset, and online ComfyUI enables AI generation', () => {
  const state = getAdminHeroState({
    currentSession: { phase: 'reviewing' },
    selectedShot: { shot_id: 'shot-001' },
    activePreset: 'default',
    comfyOnline: true,
  })

  assert.equal(state.actionKind, 'run')
  assert.equal(state.disabled, false)
  assert.equal(state.buttonLabel, 'AI 그림 만들기')
})
