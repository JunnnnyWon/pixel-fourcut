import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

const WS_PROTOCOL = location.protocol === 'https:' ? 'wss' : 'ws'
const WS_URL = `${WS_PROTOCOL}://${location.host}/ws/watch`
const RECONNECT_MS = 3000

const EMPTY_STATE = {
  active_capture_session_id: null,
  current_session: null,
  processing_sessions: [],
  print_ready_sessions: [],
  completed_sessions: [],
  errored_sessions: [],
  all_sessions: [],
}

export function useSession() {
  const [state, setState] = useState(EMPTY_STATE)
  const [progress, setProgress] = useState(null)
  const [wsConnected, setWsConnected] = useState(false)
  const [previewActive, setPreviewActive] = useState(false)
  const previewTimerRef = useRef(null)

  useEffect(() => {
    let ws
    let reconnectTimer

    const syncPreviewState = (previewUntil) => {
      window.clearTimeout(previewTimerRef.current)
      if (!previewUntil) {
        setPreviewActive(false)
        return
      }

      const remaining = new Date(previewUntil).getTime() - Date.now()
      if (Number.isNaN(remaining) || remaining <= 0) {
        setPreviewActive(false)
        return
      }

      setPreviewActive(true)
      previewTimerRef.current = window.setTimeout(() => {
        setPreviewActive(false)
      }, remaining + 50)
    }

    const applySnapshot = (nextSession) => {
      const snapshot = nextSession || EMPTY_STATE
      setState(snapshot)
      syncPreviewState(snapshot.current_session?.preview_until)
      const hasRunningProcess = (snapshot.processing_sessions || []).some(
        (item) => item.phase === 'processing',
      )
      if (!hasRunningProcess) {
        setProgress(null)
      }
    }

    const connect = () => {
      ws = new WebSocket(WS_URL)

      ws.onopen = () => setWsConnected(true)
      ws.onclose = () => {
        setWsConnected(false)
        reconnectTimer = setTimeout(connect, RECONNECT_MS)
      }

      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data)
        switch (msg.event) {
          case 'session_init':
          case 'session_updated':
            applySnapshot(msg.session)
            break
          case 'progress':
            applySnapshot(msg.session)
            setProgress({ value: msg.value, max: msg.max })
            break
          case 'session_error':
            applySnapshot(msg.session)
            break
          default:
            break
        }
      }
    }

    connect()
    return () => {
      clearTimeout(reconnectTimer)
      window.clearTimeout(previewTimerRef.current)
      ws?.close()
    }
  }, [])

  const selectShot = useCallback(async (shotId) => {
    const response = await fetch('/api/session/select-shot', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ shot_id: shotId }),
    })
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.detail || '컷 선택 실패')
    }
  }, [])

  const completeSession = useCallback(async (sessionId) => {
    const response = await fetch('/api/session/complete', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId }),
    })
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.detail || '세션 완료 실패')
    }
  }, [])

  const rerunSession = useCallback(async (sessionId) => {
    const response = await fetch('/api/session/rerun', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ session_id: sessionId }),
    })
    if (!response.ok) {
      const data = await response.json().catch(() => ({}))
      throw new Error(data.detail || 'AI 재생성 실패')
    }
  }, [])

  return useMemo(() => {
    const currentSession = state.current_session
    const processingSessions = state.processing_sessions || []
    const printReadySessions = state.print_ready_sessions || []
    const completedSessions = state.completed_sessions || []
    const erroredSessions = state.errored_sessions || []

    return {
      state,
      progress,
      wsConnected,
      previewActive,
      selectShot,
      completeSession,
      rerunSession,
      currentSession,
      processingSessions,
      printReadySessions,
      completedSessions,
      erroredSessions,
      allSessions: state.all_sessions || [],
      activeCaptureSessionId: state.active_capture_session_id,
      sessionId: currentSession?.session_id || null,
      phase: currentSession?.phase || 'idle',
      shots: currentSession?.shots || [],
      selectedShotId: currentSession?.selected_shot_id || null,
      selectedShot: currentSession?.selected_shot || null,
      previewShotId: currentSession?.preview_shot_id || null,
      previewShot: currentSession?.preview_shot || null,
      previewUntil: currentSession?.preview_until || null,
      promptId: currentSession?.prompt_id || null,
      resultFilename: currentSession?.result_filename || null,
      resultUrl: currentSession?.result_url || null,
      error: currentSession?.error || null,
      logs: currentSession?.logs || [],
    }
  }, [
    state,
    progress,
    wsConnected,
    previewActive,
    selectShot,
    completeSession,
    rerunSession,
  ])
}
