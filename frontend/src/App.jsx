import { useState, useEffect, useRef } from 'react'
import AdminPanel from './AdminPanel'
import './App.css'

const WS_URL = `ws://${location.host}/ws/watch`
const RECONNECT_MS = 3000

export default function App() {
  const [page, setPage] = useState(location.pathname === '/admin' ? 'admin' : 'user')
  const [inputImage, setInputImage] = useState(null)   // { filename, url }
  const [status, setStatus] = useState('idle')          // idle | processing | done | error
  const [progress, setProgress] = useState(null)        // { value, max }
  const [resultUrl, setResultUrl] = useState(null)
  const [errorMsg, setErrorMsg] = useState(null)
  const wsRef = useRef(null)

  useEffect(() => {
    let ws
    const connect = () => {
      ws = new WebSocket(WS_URL)
      wsRef.current = ws
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data)
        if (msg.event === 'new_image') {
          setInputImage({ filename: msg.filename, url: msg.url })
          setStatus('idle')
          setResultUrl(null)
          setProgress(null)
        } else if (msg.event === 'progress') {
          setProgress({ value: msg.value, max: msg.max })
        } else if (msg.event === 'done') {
          setResultUrl(`/api/result/${msg.prompt_id}`)
          setStatus('done')
          setProgress(null)
        } else if (msg.event === 'error') {
          setErrorMsg(msg.message)
          setStatus('error')
          setProgress(null)
        }
      }
      ws.onclose = () => setTimeout(connect, RECONNECT_MS)
    }
    connect()
    return () => ws?.close()
  }, [])

  const handleRun = async () => {
    if (!inputImage) return
    setStatus('processing')
    setProgress(null)
    setResultUrl(null)
    setErrorMsg(null)
    await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: inputImage.filename }),
    })
  }

  if (page === 'admin') return <AdminPanel onBack={() => setPage('user')} />

  return (
    <div className="screen">
      <button className="admin-link" onClick={() => setPage('admin')}>관리자</button>

      <div className="preview-area">
        {inputImage
          ? <img src={inputImage.url} alt="input" className="preview-img" />
          : <div className="placeholder">DSLR 촬영 또는 관리자 업로드를 기다리는 중...</div>
        }
      </div>

      {status === 'processing' && (
        <div className="status-bar">
          처리 중...
          {progress && <span> {progress.value} / {progress.max}</span>}
        </div>
      )}
      {status === 'error' && <div className="status-bar error">{errorMsg}</div>}

      <button
        className="run-btn"
        disabled={!inputImage || status === 'processing'}
        onClick={handleRun}
      >
        {status === 'processing' ? '처리 중...' : '처리 시작'}
      </button>

      {resultUrl && status === 'done' && (
        <div className="result-overlay" onClick={() => setResultUrl(null)}>
          <img src={resultUrl} alt="result" className="result-img" />
          <p className="close-hint">화면을 터치하면 닫힙니다</p>
        </div>
      )}
    </div>
  )
}
