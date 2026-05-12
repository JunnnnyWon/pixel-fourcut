import { useState, useEffect, useRef } from 'react'

export default function AdminPanel({ onBack }) {
  const [presets, setPresets] = useState([])
  const [active, setActive] = useState(null)
  const [presetName, setPresetName] = useState('')
  const [presetFile, setPresetFile] = useState(null)
  const [autoActivate, setAutoActivate] = useState(true)
  const [uploadFile, setUploadFile] = useState(null)
  const [uploadPreview, setUploadPreview] = useState(null)
  const [msg, setMsg] = useState({ text: '', type: 'ok' })
  const fileInputRef = useRef(null)

  const loadPresets = async () => {
    const r = await fetch('/api/presets')
    const d = await r.json()
    setPresets(d.presets)
    setActive(d.active)
  }

  useEffect(() => { loadPresets() }, [])

  const flash = (text, type = 'ok') => {
    setMsg({ text, type })
    setTimeout(() => setMsg({ text: '', type: 'ok' }), 3000)
  }

  const handleUploadPreset = async () => {
    if (!presetName.trim()) return flash('프리셋 이름을 입력하세요', 'err')
    if (!presetFile) return flash('workflow.json 파일을 선택하세요', 'err')
    const fd = new FormData()
    fd.append('file', presetFile)
    const r = await fetch(`/api/presets?name=${encodeURIComponent(presetName.trim())}`, { method: 'POST', body: fd })
    if (!r.ok) return flash('업로드 실패', 'err')
    if (autoActivate) {
      await fetch(`/api/presets/${encodeURIComponent(presetName.trim())}/activate`, { method: 'POST' })
      flash(`"${presetName.trim()}" 업로드 및 활성화 완료`)
    } else {
      flash(`"${presetName.trim()}" 업로드 완료`)
    }
    setPresetName('')
    setPresetFile(null)
    loadPresets()
  }

  const handleActivate = async (name) => {
    const r = await fetch(`/api/presets/${encodeURIComponent(name)}/activate`, { method: 'POST' })
    if (r.ok) { flash(`"${name}" 활성화됨`); loadPresets() }
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
      flash('이미지 업로드 완료 — 사용자 화면에 반영됩니다')
      setUploadFile(null)
      setUploadPreview(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    } else {
      flash('업로드 실패', 'err')
    }
  }

  return (
    <div className="admin">
      <button className="back-btn" onClick={onBack}>← 사용자 화면</button>
      <h2>관리자 패널</h2>

      {msg.text && <div className={`flash ${msg.type === 'err' ? 'flash-err' : ''}`}>{msg.text}</div>}

      {/* 프리셋 없음 경고 */}
      {presets.length === 0 && (
        <div className="warn-box">⚠️ 등록된 워크플로우 프리셋이 없습니다. 아래에서 업로드해주세요.</div>
      )}
      {presets.length > 0 && !active && (
        <div className="warn-box">⚠️ 활성화된 프리셋이 없습니다. 아래 목록에서 활성화해주세요.</div>
      )}

      <section>
        <h3>워크플로우 프리셋</h3>
        <ul className="preset-list">
          {presets.map(name => (
            <li key={name} className={name === active ? 'active' : ''}>
              <span className="preset-name">{name}</span>
              {name === active && <span className="badge">활성</span>}
              {name !== active && (
                <button className="btn-activate" onClick={() => handleActivate(name)}>활성화</button>
              )}
              <button className="btn-delete" onClick={() => handleDelete(name)}>삭제</button>
            </li>
          ))}
        </ul>

        <div className="form-col">
          <div className="form-row">
            <input
              placeholder="프리셋 이름"
              value={presetName}
              onChange={e => setPresetName(e.target.value)}
            />
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
      </section>

      <section>
        <h3>이미지 직접 업로드</h3>
        {uploadPreview && (
          <img src={uploadPreview} alt="preview" className="upload-preview" />
        )}
        <div className="form-row" style={{marginTop: uploadPreview ? 10 : 0}}>
          <label className="file-label">
            {uploadFile ? uploadFile.name : '사진 선택'}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              style={{display:'none'}}
              onChange={handleImageSelect}
            />
          </label>
          <button className="btn-primary" onClick={handleImageUpload}>업로드</button>
        </div>
      </section>
    </div>
  )
}
