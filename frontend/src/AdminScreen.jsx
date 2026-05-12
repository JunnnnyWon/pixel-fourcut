import { useState, useEffect, useRef } from 'react'
import { useSession } from './useSession'
import './App.css'

export default function AdminScreen() {
  const { images, selected, selectImage, status, progress, promptId, error, wsConnected } = useSession()
  const [presets, setPresets] = useState([])
  const [activePreset, setActivePreset] = useState(null)
  const [comfyOnline, setComfyOnline] = useState(null)
  const [presetName, setPresetName] = useState('')
  const [presetFile, setPresetFile] = useState(null)
  const [autoActivate, setAutoActivate] = useState(true)
  const [uploadFile, setUploadFile] = useState(null)
  const [uploadPreview, setUploadPreview] = useState(null)
  const [msg, setMsg] = useState({ text: '', type: 'ok' })
  const [presetsOpen, setPresetsOpen] = useState(false)
  const fileInputRef = useRef(null)

  const flash = (text, type = 'ok') => {
    setMsg({ text, type })
    setTimeout(() => setMsg({ text: '', type: 'ok' }), 4000)
  }

  const loadPresets = async () => {
    const r = await fetch('/api/presets')
    const d = await r.json()
    setPresets(d.presets)
    setActivePreset(d.active)
  }

  const checkComfy = async () => {
    const r = await fetch('/api/comfyui/status')
    const d = await r.json()
    setComfyOnline(d.online)
  }

  useEffect(() => {
    loadPresets()
    checkComfy()
    const t = setInterval(checkComfy, 10000)
    return () => clearInterval(t)
  }, [])

  const handleRun = async () => {
    if (!selected) return flash('사진을 먼저 선택하세요', 'err')
    if (status === 'processing') return flash('이미 처리 중입니다', 'err')
    const r = await fetch('/api/run', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ filename: selected }),
    })
    if (!r.ok) {
      const d = await r.json().catch(() => ({}))
      flash(d.detail || '처리 실패', 'err')
    }
  }

  const handleReset = async () => {
    if (!confirm('새 손님을 시작합니다. 현재 사진과 결과가 모두 삭제됩니다.')) return
    await fetch('/api/reset', { method: 'POST' })
    flash('초기화 완료')
  }

  const handleUploadPreset = async () => {
    if (!presetName.trim()) return flash('프리셋 이름을 입력하세요', 'err')
    if (!presetFile) return flash('workflow.json 파일을 선택하세요', 'err')
    const fd = new FormData()
    fd.append('file', presetFile)
    const r = await fetch(`/api/presets?name=${encodeURIComponent(presetName.trim())}`, { method: 'POST', body: fd })
    const d = await r.json().catch(() => ({}))
    if (!r.ok) return flash(d.detail || '업로드 실패', 'err')
    if (autoActivate) {
      await fetch(`/api/presets/${encodeURIComponent(presetName.trim())}/activate`, { method: 'POST' })
      flash(`"${presetName.trim()}" 업로드 및 활성화 완료`)
    } else {
      flash(`"${presetName.trim()}" 업로드 완료`)
    }
    setPresetName(''); setPresetFile(null)
    loadPresets()
  }

  const handleActivate = async (name) => {
    await fetch(`/api/presets/${encodeURIComponent(name)}/activate`, { method: 'POST' })
    flash(`"${name}" 활성화됨`)
    loadPresets()
  }

  const handleDelete = async (name) => {
    if (!confirm(`"${name}" 프리셋을 삭제할까요?`)) return
    const r = await fetch(`/api/presets/${encodeURIComponent(name)}`, { method: 'DELETE' })
    if (r.ok) { flash(`"${name}" 삭제됨`); loadPresets() }
    else flash('삭제 실패', 'err')
  }

  const handleImageSelect = (e) => {
    const file = e.target.files[0]
    if (!file) return
    setUploadFile(file)
    setUploadPreview(URL.createObjectURL(file))
  }

  const handleImageUpload = async () => {
    if (!uploadFile) return flash('파일을 선택하세요', 'err')
    const fd = new FormData()
    fd.append('file', uploadFile)
    const r = await fetch('/api/upload', { method: 'POST', body: fd })
    if (r.ok) {
      flash('이미지 업로드 완료')
      setUploadFile(null); setUploadPreview(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    } else flash('업로드 실패', 'err')
  }

  const canRun = selected && status !== 'processing' && activePreset && comfyOnline

  return (
    <div className="admin">
      {/* 상단 상태바 */}
      <div className="admin-topbar">
        <span className="brand">픽셀네컷 관리자</span>
        <div className="admin-status-row">
          <span className={`status-chip ${comfyOnline ? 'ok' : 'err'}`}>
            ComfyUI {comfyOnline ? '연결됨' : '오프라인'}
          </span>
          <span className={`status-chip ${activePreset ? 'ok' : 'warn'}`}>
            {activePreset ? `프리셋: ${activePreset}` : '프리셋 없음'}
          </span>
          <div className={`ws-dot ${wsConnected ? 'on' : 'off'}`} />
        </div>
      </div>

      {msg.text && <div className={`flash ${msg.type === 'err' ? 'flash-err' : ''}`}>{msg.text}</div>}

      {/* 갤러리 + 선택 */}
      <section>
        <div className="section-header">
          <h3>사진 선택</h3>
          <button className="btn-new-guest" onClick={handleReset}>🔄 새 손님</button>
        </div>

        {images.length === 0
          ? <div className="empty-gallery">촬영된 사진이 없습니다</div>
          : (
            <div className="admin-gallery">
              {images.map(fn => (
                <div
                  key={fn}
                  className={`admin-thumb ${selected === fn ? 'selected' : ''}`}
                  onClick={() => selectImage(fn)}
                >
                  <img src={`/api/input/${fn}`} alt={fn} />
                  {selected === fn && <div className="thumb-check">✓</div>}
                </div>
              ))}
            </div>
          )
        }

        {/* 처리 상태 */}
        {status === 'processing' && (
          <div className="status-bar" style={{marginTop:10}}>
            <div className="spinner" />
            AI 처리 중...{progress && ` (${progress.value} / ${progress.max})`}
          </div>
        )}
        {status === 'error' && (
          <div className="status-bar error" style={{marginTop:10}}>❌ {error}</div>
        )}
        {status === 'done' && promptId && (
          <div className="result-preview">
            <img src={`/api/result/${promptId}`} alt="result" />
            <span>처리 완료 ✅</span>
          </div>
        )}

        <button
          className="run-btn"
          style={{marginTop:12}}
          disabled={!canRun}
          onClick={handleRun}
          title={!activePreset ? '프리셋을 먼저 활성화하세요' : !comfyOnline ? 'ComfyUI가 오프라인입니다' : !selected ? '사진을 선택하세요' : ''}
        >
          {status === 'processing' ? '처리 중...' : '✨ AI 처리 시작'}
        </button>
      </section>

      {/* 이미지 업로드 */}
      <section>
        <h3>이미지 직접 업로드</h3>
        {uploadPreview && <img src={uploadPreview} alt="preview" className="upload-preview" />}
        <div className="form-row" style={{marginTop: uploadPreview ? 10 : 0}}>
          <label className="file-label">
            {uploadFile ? uploadFile.name : '사진 선택'}
            <input ref={fileInputRef} type="file" accept="image/*" capture="environment"
              style={{display:'none'}} onChange={handleImageSelect} />
          </label>
          <button className="btn-primary" onClick={handleImageUpload}>업로드</button>
        </div>
      </section>

      {/* 프리셋 관리 (접이식) */}
      <section>
        <div className="section-header" onClick={() => setPresetsOpen(o => !o)} style={{cursor:'pointer'}}>
          <h3>워크플로우 프리셋 {presetsOpen ? '▲' : '▼'}</h3>
        </div>
        {presetsOpen && (
          <>
            {presets.length === 0 && <div className="warn-box">⚠️ 등록된 프리셋이 없습니다.</div>}
            {presets.length > 0 && !activePreset && <div className="warn-box">⚠️ 활성화된 프리셋이 없습니다.</div>}
            <ul className="preset-list">
              {presets.map(name => (
                <li key={name} className={name === activePreset ? 'active' : ''}>
                  <span className="preset-name">{name}</span>
                  {name === activePreset && <span className="badge">활성</span>}
                  {name !== activePreset && (
                    <button className="btn-activate" onClick={() => handleActivate(name)}>활성화</button>
                  )}
                  <button className="btn-delete" onClick={() => handleDelete(name)}>삭제</button>
                </li>
              ))}
            </ul>
            <div className="api-guide">
              💡 <strong>API 형식</strong> 파일만 가능 — ComfyUI ⚙️ → Enable Dev Mode → <em>Save (API Format)</em>
            </div>
            <div className="form-col">
              <div className="form-row">
                <input placeholder="프리셋 이름" value={presetName} onChange={e => setPresetName(e.target.value)} />
                <label className="file-label">
                  {presetFile ? presetFile.name : 'workflow.json 선택'}
                  <input type="file" accept=".json" style={{display:'none'}} onChange={e => setPresetFile(e.target.files[0])} />
                </label>
              </div>
              <label className="checkbox-row">
                <input type="checkbox" checked={autoActivate} onChange={e => setAutoActivate(e.target.checked)} />
                업로드 후 자동 활성화
              </label>
              <button className="btn-primary" onClick={handleUploadPreset}>업로드</button>
            </div>
          </>
        )}
      </section>
    </div>
  )
}
