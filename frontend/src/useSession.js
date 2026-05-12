import { useCallback, useEffect, useMemo, useRef, useState } from 'react'

const WS_PROTOCOL = location.protocol === 'https:' ? 'wss' : 'ws'
const WS_URL = `${WS_PROTOCOL}://${location.host}/ws/watch`
const RECONNECT_MS = 3000

const EMPTY_SESSION = {
  session_id: null,
  phase: 'idle',
  shots: [],
  selected_shot_id: null,
  selected_shot: null,
  prompt_id: null,
  result_filename: null,
  result_url: null,
  error: null,
  logs: [],
}

export function useSession() {
  const [session, setSession] = useState(EMPTY_SESSION)
  const [progress, setProgress] = useState(null)
  const [wsConnected, setWsConnected] = useState(false)
  const [previewActive, setPreviewActive] = useState(false)
  const wsRef = useRef(null)
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

    const connect = () => {
      ws = new WebSocket(WS_URL)
      wsRef.current = ws

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
            {
              const nextSession = msg.session || EMPTY_SESSION
              setSession(nextSession)
              syncPreviewState(nextSession.preview_until)
              if (nextSession.phase !== 'processing') {
                setProgress(null)
              }
            }
            break
          case 'progress':
            if (msg.session) {
              setSession(msg.session)
              syncPreviewState(msg.session.preview_until)
            }
            setProgress({ value: msg.value, max: msg.max })
            break
          case 'session_error':
            {
              const nextSession = msg.session || EMPTY_SESSION
              setSession(nextSession)
              syncPreviewState(nextSession.preview_until)
              setProgress(null)
            }
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

  return useMemo(() => ({
    session,
    progress,
    wsConnected,
    selectShot,
    sessionId: session.session_id,
    phase: session.phase,
    shots: session.shots || [],
    selectedShotId: session.selected_shot_id,
    selectedShot: session.selected_shot,
    previewShotId: session.preview_shot_id,
    previewShot: session.preview_shot,
    previewUntil: session.preview_until,
    previewActive,
    promptId: session.prompt_id,
    resultFilename: session.result_filename,
    resultUrl: session.result_url,
    error: session.error,
    logs: session.logs || [],
  }), [session, progress, wsConnected, selectShot, previewActive])
}
