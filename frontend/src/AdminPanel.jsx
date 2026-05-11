import { useState, useEffect } from 'react'

export default function AdminPanel({ onBack }) {
  const [presets, setPresets] = useState([])
  const [active, setActive] = useState(null)
  const [presetName, setPresetName] = useState('')
  const [presetFile, setPresetFile] = useState(null)
  const [uploadFile, setUploadFile] = useState(null)
  const [msg, setMsg] = useState('')

  const loadPresets = async () => {
    const r = await fetch('/api/presets')
    const d = await r.json()
    setPresets(d.presets)
    setActive(d.active)
  }

  useEffect(() => { loadPresets() }, [])

  const flash = (m) => { setMsg(m); setTimeout(() => setMsg(''), 3000) }

  const handleUploadPreset = async () => {
    if (!presetName || !presetFile) return flash('이름과 파일을 선택하세요')
    const fd = new FormData()
    fd.append('file', presetFile)
    const r = await fetch(`/api/presets?name=${encodeURIComponent(presetName)}`, { method: 'POST', body: fd })
    if (r.ok) { flash('프리셋 업로드 완료'); loadPresets() }
    else flash('업로드 실패')
  }

  const handleActivate = async (name) => {
    const r = await fetch(`/api/presets/${encodeURIComponent(name)}/activate`, { method: 'POST' })
    if (r.ok) { flash(`"${name}" 활성화됨`); loadPresets() }
  }

  const handleImageUpload = async () => {
    if (!uploadFile) return flash('파일을 선택하세요')
    const fd = new FormData()
    fd.append('file', uploadFile)
    const r = await fetch('/api/upload', { method: 'POST', body: fd })
    if (r.ok) flash('이미지 업로드 완료')
    else flash('업로드 실패')
  }

  return (
    <div className="admin">
      <button className="back-btn" onClick={onBack}>← 사용자 화면</button>
      <h2>관리자 패널</h2>

      {msg && <div className="flash">{msg}</div>}

      <section>
        <h3>워크플로우 프리셋</h3>
        <ul className="preset-list">
          {presets.map(name => (
            <li key={name} className={name === active ? 'active' : ''}>
              {name} {name === active && <span className="badge">활성</span>}
              {name !== active && (
                <button onClick={() => handleActivate(name)}>활성화</button>
              )}
            </li>
          ))}
          {presets.length === 0 && <li className="empty">프리셋 없음</li>}
        </ul>

        <div className="form-row">
          <input
            placeholder="프리셋 이름"
            value={presetName}
            onChange={e => setPresetName(e.target.value)}
          />
          <input type="file" accept=".json" onChange={e => setPresetFile(e.target.files[0])} />
          <button onClick={handleUploadPreset}>업로드</button>
        </div>
      </section>

      <section>
        <h3>이미지 직접 업로드 (휴대폰)</h3>
        <div className="form-row">
          <input
            type="file"
            accept="image/*"
            capture="environment"
            onChange={e => setUploadFile(e.target.files[0])}
          />
          <button onClick={handleImageUpload}>업로드</button>
        </div>
      </section>
    </div>
  )
}
