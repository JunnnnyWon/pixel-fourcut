import { useState, useEffect, useRef, useCallback } from 'react'

const WS_URL = `ws://${location.host}/ws/watch`
const RECONNECT_MS = 3000

export function useSession() {
  const [images, setImages] = useState([])
  const [selected, setSelectedState] = useState(null)
  const [status, setStatus] = useState('idle')
  const [progress, setProgress] = useState(null)
  const [promptId, setPromptId] = useState(null)
  const [error, setError] = useState(null)
  const [wsConnected, setWsConnected] = useState(false)
  const wsRef = useRef(null)

  useEffect(() => {
    let ws
    const connect = () => {
      ws = new WebSocket(WS_URL)
      wsRef.current = ws
      ws.onopen = () => setWsConnected(true)
      ws.onclose = () => { setWsConnected(false); setTimeout(connect, RECONNECT_MS) }
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data)
        switch (msg.event) {
          case 'init':
            setImages(msg.images || [])
            setSelectedState(msg.selected)
            setStatus(msg.status || 'idle')
            setPromptId(msg.prompt_id)
            if (msg.error) setError(msg.error)
            break
          case 'new_image':
            setImages(msg.images || [])
            break
          case 'image_removed':
            setImages(msg.images || [])
            break
          case 'selected':
            setSelectedState(msg.filename)
            break
          case 'progress':
            setStatus('processing')
            setProgress({ value: msg.value, max: msg.max })
            break
          case 'done':
            setStatus('done')
            setPromptId(msg.prompt_id)
            setProgress(null)
            break
          case 'error':
            setStatus('error')
            setError(msg.message)
            setProgress(null)
            break
          case 'reset':
            setImages([])
            setSelectedState(null)
            setStatus('idle')
            setProgress(null)
            setPromptId(null)
            setError(null)
            break
        }
      }
    }
    connect()
    return () => ws?.close()
  }, [])

  const selectImage = useCallback(async (filename) => {
    setSelectedState(filename)
    await fetch('/api/select', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename }),
    })
  }, [])

  return { images, selected, selectImage, status, progress, promptId, error, wsConnected }
}
