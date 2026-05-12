import { useState, useEffect, useRef } from 'react'
import AdminPanel from './AdminPanel'
import './App.css'

const WS_URL = `ws://${location.host}/ws/watch`
const RECONNECT_MS = 3000

export default function App() {
  const [page, setPage] = useState(location.pathname === '/admin' ? 'admin' : 'user')
  const [inputImage, setInputImage] = useState(null)
  const [status, setStatus] = useState('idle')   // idle | processing | done | error
  const [progress, setProgress] = useState(null)
  const [resultUrl, setResultUrl] = useState(null)
  const [errorMsg, setErrorMsg] = useState(null)
  const [wsConnected, setWsConnected] = useState(false)
  const [noPreset, setNoPreset] = useState(false)
  const wsRef = useRef(null)

  // 프리셋 활성화 여부 확인
  const checkPreset = async () => {
    try {
      const r = await fetch('/api/presets')
      const d = await r.json()
      setNoPreset(!d.active)
    } catch {}
  }

  useEffect(() => {
    checkPreset()
    let ws
    const connect = () => {
      ws = new WebSocket(WS_URL)
      wsRef.current = ws
      ws.onopen = () => setWsConnected(true)
      ws.onmessage = (e) => {
        const msg = JSON.parse(e.data)
        if (msg.event === 'new_image') {
          setInputImage({ filename: msg.filename, url: msg.url })
          setStatus('idle')
          setResultUrl(null)
          setProgress(null)
          setErrorMsg(null)
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
      ws.onclose = () => { setWsConnected(false); setTimeout(connect, RECONNECT_MS) }
    }
    connect()
    return () => ws?.close()
  }, [])

  const handleRun = async () => {
    if (!inputImage || status === 'processing') return
    setStatus('processing')
    setProgress(null)
    setResultUrl(null)
    setErrorMsg(null)
    const r = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: inputImage.filename }),
    })
    if (!r.ok) {
      const d = await r.json().catch(() => ({}))
      setErrorMsg(d.detail || '처리 요청 실패')
      setStatus('error')
    }
  }

  const handleRetry = () => {
    setStatus('idle')
    setResultUrl(null)
    setErrorMsg(null)
    setProgress(null)
  }

  if (page === 'admin') return <AdminPanel onBack={() => { setPage('user'); checkPreset() }} />

  return (
    <div className="screen">
      <div className="top-bar">
        <div className={`ws-dot ${wsConnected ? 'on' : 'off'}`} title={wsConnected ? '연결됨' : '연결 끊김'} />
        <button className="admin-link" onClick={() => setPage('admin')}>관리자</button>
      </div>

      {noPreset && (
        <div className="warn-box">⚠️ 활성화된 워크플로우가 없습니다. 관리자 패널에서 프리셋을 활성화해주세요.</div>
      )}

      <div className="preview-area">
        {inputImage
          ? <img src={inputImage.url} alt="input" className="preview-img" />
          : <div className="placeholder">DSLR 촬영 또는 관리자 업로드를 기다리는 중...</div>
        }
      </div>

      {status === 'processing' && (
        <div className="status-bar">
          처리 중...{progress && ` (${progress.value} / ${progress.max})`}
        </div>
      )}
      {status === 'error' && (
        <div className="status-bar error">
          ❌ {errorMsg}
          <button className="retry-btn" onClick={handleRetry}>다시 시도</button>
        </div>
      )}
      {status === 'done' && !resultUrl && (
        <div className="status-bar">결과 이미지 로딩 중...</div>
      )}

      {status !== 'done' && (
        <button
          className="run-btn"
          disabled={!inputImage || status === 'processing' || noPreset}
          onClick={handleRun}
        >
          {status === 'processing' ? '처리 중...' : '처리 시작'}
        </button>
      )}

      {resultUrl && status === 'done' && (
        <div className="result-overlay">
          <img src={resultUrl} alt="result" className="result-img" />
          <button className="result-close-btn" onClick={handleRetry}>↩ 다시 처리하기</button>
        </div>
      )}
    </div>
  )
}
