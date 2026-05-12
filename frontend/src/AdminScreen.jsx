import { useCallback, useEffect, useRef, useState } from 'react'
import { useSession } from './useSession'
import './App.css'

const PHASE_LABEL = {
  idle: '대기 중',
  capturing: '촬영 중',
  reviewing: '사진 선택 중',
  queued: 'AI 대기열',
  processing: 'AI 처리 중',
  result_ready: '인화 대기',
  completed: '완료',
  error: '오류',
}

function SessionCard({ title, session, children, compact = false }) {
  if (!session) return null
  const heroImage = session.result_url || session.selected_shot?.url || session.preview_shot?.url || session.shots?.[0]?.url
  return (
    <div className={`queue-card ${compact ? 'compact' : ''}`}>
      <div className="queue-card-head">
        <div>
          <div className="summary-label">{title}</div>
          <strong>{session.session_id}</strong>
        </div>
        <span className={`phase-badge phase-${session.phase}`}>{PHASE_LABEL[session.phase] || session.phase}</span>
      </div>
      <div className="queue-card-meta">
        <span>shots {session.shots?.length || 0}</span>
        {session.selected_shot && <span>selected {session.selected_shot.filename}</span>}
        {session.result_filename && <span>result {session.result_filename}</span>}
      </div>
      {heroImage && <img src={heroImage} alt={session.session_id} className="queue-card-image" />}
      {children}
    </div>
  )
}

export default function AdminScreen() {
  const {
    currentSession,
    phase,
    shots,
    selectedShotId,
    selectedShot,
    progress,
    wsConnected,
    processingSessions,
    printReadySessions,
    erroredSessions,
    selectShot,
    completeSession,
  } = useSession()

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
  const flashTimerRef = useRef(null)

  const flash = useCallback((text, type = 'ok') => {
    setMsg({ text, type })
    window.clearTimeout(flashTimerRef.current)
    flashTimerRef.current = window.setTimeout(() => setMsg({ text: '', type: 'ok' }), 4000)
  }, [])

  const request = useCallback(async (url, options = {}, errorMessage = '요청 실패') => {
    const response = await fetch(url, options)
    const data = await response.json().catch(() => ({}))
    if (!response.ok) {
      throw new Error(data.detail || errorMessage)
    }
    return data
  }, [])

  const loadPresets = useCallback(async () => {
    const data = await request('/api/presets', {}, '프리셋 로드 실패')
    setPresets(data.presets || [])
    setActivePreset(data.active)
  }, [request])

  const checkComfy = useCallback(async () => {
    const data = await request('/api/comfyui/status', {}, 'ComfyUI 상태 조회 실패')
    setComfyOnline(data.online)
  }, [request])

  useEffect(() => {
    const bootstrap = async () => {
      try {
        await loadPresets()
      } catch (err) {
        flash(err.message, 'err')
      }
      try {
        await checkComfy()
      } catch (err) {
        flash(err.message, 'err')
      }
    }
    bootstrap()
    const timer = setInterval(() => {
      checkComfy().catch(() => {})
    }, 10000)
    return () => clearInterval(timer)
  }, [checkComfy, flash, loadPresets])

  useEffect(() => () => window.clearTimeout(flashTimerRef.current), [])

  const handleStartSession = async () => {
    try {
      await request('/api/session/start', { method: 'POST' }, '세션 시작 실패')
      flash('새 세션을 시작했습니다')
    } catch (err) {
      flash(err.message, 'err')
    }
  }

  const handleFinishCapture = async () => {
    try {
      await request('/api/session/finish-capture', { method: 'POST' }, '촬영 종료 실패')
      flash('촬영을 종료했습니다')
    } catch (err) {
      flash(err.message, 'err')
    }
  }

  const handleRunSelected = async () => {
    try {
      await request('/api/session/run-selected', { method: 'POST' }, 'AI 처리 시작 실패')
      flash('AI 대기열에 추가했습니다')
    } catch (err) {
      flash(err.message, 'err')
    }
  }

  const handleReset = async () => {
    if (!confirm('모든 세션과 inbox를 초기화할까요?')) return
    try {
      await request('/api/session/reset', { method: 'POST' }, '초기화 실패')
      flash('초기화 완료')
    } catch (err) {
      flash(err.message, 'err')
    }
  }

  const handleUploadPreset = async () => {
    if (!presetName.trim()) return flash('프리셋 이름을 입력하세요', 'err')
    if (!presetFile) return flash('workflow.json 파일을 선택하세요', 'err')
    const fd = new FormData()
    fd.append('file', presetFile)
    try {
      await request(`/api/presets?name=${encodeURIComponent(presetName.trim())}`, { method: 'POST', body: fd }, '프리셋 업로드 실패')
      if (autoActivate) {
        await request(`/api/presets/${encodeURIComponent(presetName.trim())}/activate`, { method: 'POST' }, '프리셋 활성화 실패')
        flash(`"${presetName.trim()}" 업로드 및 활성화 완료`)
      } else {
        flash(`"${presetName.trim()}" 업로드 완료`)
      }
      setPresetName('')
      setPresetFile(null)
      loadPresets().catch(() => {})
    } catch (err) {
      flash(err.message, 'err')
    }
  }

  const handleActivate = async (name) => {
    try {
      await request(`/api/presets/${encodeURIComponent(name)}/activate`, { method: 'POST' }, '프리셋 활성화 실패')
      flash(`"${name}" 활성화됨`)
      loadPresets().catch(() => {})
    } catch (err) {
      flash(err.message, 'err')
    }
  }

  const handleDelete = async (name) => {
    if (!confirm(`"${name}" 프리셋을 삭제할까요?`)) return
    try {
      await request(`/api/presets/${encodeURIComponent(name)}`, { method: 'DELETE' }, '프리셋 삭제 실패')
      flash(`"${name}" 삭제됨`)
      loadPresets().catch(() => {})
    } catch (err) {
      flash(err.message, 'err')
    }
  }

  const handleImageSelect = (e) => {
    const file = e.target.files?.[0]
    if (!file) return
    setUploadFile(file)
    setUploadPreview(URL.createObjectURL(file))
  }

  const handleImageUpload = async () => {
    if (!uploadFile) return flash('파일을 선택하세요', 'err')
    const fd = new FormData()
    fd.append('file', uploadFile)
    try {
      await request('/api/upload', { method: 'POST', body: fd }, '이미지 업로드 실패')
      flash(currentSession?.phase === 'capturing' ? '업로드 완료: 현재 촬영 세션에 편입됩니다' : '업로드 완료: 현재 capture lane이 비어 있습니다')
      setUploadFile(null)
      setUploadPreview(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    } catch (err) {
      flash(err.message, 'err')
    }
  }

  const canRun = currentSession?.phase === 'reviewing' && !!selectedShotId && !!activePreset && comfyOnline

  return (
    <div className="admin">
      <div className="admin-topbar">
        <span className="brand">픽셀네컷 관리자</span>
        <div className="admin-status-row">
          <span className={`status-chip ${comfyOnline ? 'ok' : 'err'}`}>
            ComfyUI {comfyOnline ? '연결됨' : '오프라인'}
          </span>
          <span className={`status-chip ${activePreset ? 'ok' : 'warn'}`}>
            {activePreset ? `프리셋: ${activePreset}` : '프리셋 없음'}
          </span>
          <span className={`phase-badge phase-${phase}`}>{PHASE_LABEL[phase] || phase}</span>
          <div className={`ws-dot ${wsConnected ? 'on' : 'off'}`} />
        </div>
      </div>

      {msg.text && <div className={`flash ${msg.type === 'err' ? 'flash-err' : ''}`}>{msg.text}</div>}

      <section>
        <div className="section-header">
          <h3>현재 Capture Lane</h3>
          <button className="btn-new-guest" onClick={handleReset}>전체 초기화</button>
        </div>

        <div className="session-summary session-summary-four">
          <div>
            <span className="summary-label">현재 세션</span>
            <strong>{currentSession?.session_id || '비어 있음'}</strong>
          </div>
          <div>
            <span className="summary-label">상태</span>
            <strong>{PHASE_LABEL[currentSession?.phase || 'idle'] || '대기 중'}</strong>
          </div>
          <div>
            <span className="summary-label">처리 대기/중</span>
            <strong>{processingSessions.length}</strong>
          </div>
          <div>
            <span className="summary-label">출력 대기</span>
            <strong>{printReadySessions.length}</strong>
          </div>
        </div>

        <div className="action-row">
          <button className="btn-primary" onClick={handleStartSession} disabled={!!currentSession}>
            새 세션 시작
          </button>
          <button className="btn-primary secondary" onClick={handleFinishCapture} disabled={currentSession?.phase !== 'capturing'}>
            촬영 종료
          </button>
          <button className="btn-primary" onClick={handleRunSelected} disabled={!canRun}>
            {currentSession?.phase === 'reviewing' ? 'AI 대기열 추가' : 'AI 대기열 추가'}
          </button>
        </div>

        {currentSession ? (
          <>
            <div className="capture-lane-header">
              <span className={`phase-badge phase-${currentSession.phase}`}>{PHASE_LABEL[currentSession.phase] || currentSession.phase}</span>
              <span className="lane-meta">shots {shots.length}</span>
            </div>

            {shots.length === 0 ? (
              <div className="empty-gallery">촬영된 사진이 아직 없습니다</div>
            ) : (
              <div className="admin-gallery">
                {shots.map((shot) => (
                  <div
                    key={`${currentSession.session_id}-${shot.shot_id}`}
                    className={`admin-thumb ${selectedShotId === shot.shot_id ? 'selected' : ''}`}
                    onClick={() => selectShot(shot.shot_id).catch((err) => flash(err.message, 'err'))}
                  >
                    <img src={shot.url} alt={shot.filename} />
                    {selectedShotId === shot.shot_id && <div className="thumb-check">✓</div>}
                  </div>
                ))}
              </div>
            )}

            {selectedShot && (
              <div className="selected-panel">
                <img src={selectedShot.url} alt={selectedShot.filename} />
                <div>
                  <div className="summary-label">선택 컷</div>
                  <strong>{selectedShot.filename}</strong>
                </div>
              </div>
            )}
          </>
        ) : (
          <div className="empty-gallery">지금은 capture lane이 비어 있습니다. 처리 대기 중인 팀과 별개로 새 팀을 받을 수 있습니다.</div>
        )}

        {processingSessions.some((item) => item.phase === 'processing') && (
          <div className="status-bar" style={{ marginTop: 12 }}>
            <div className="spinner" />
            AI 처리 중...{progress && ` (${progress.value} / ${progress.max})`}
          </div>
        )}
      </section>

      <section>
        <div className="section-header">
          <h3>AI 처리 대기 / 진행 중</h3>
        </div>
        {processingSessions.length === 0 ? (
          <div className="empty-gallery">대기 중인 세션이 없습니다</div>
        ) : (
          <div className="queue-grid">
            {processingSessions.map((item) => (
              <SessionCard
                key={item.session_id}
                title={item.phase === 'queued' ? '대기열' : '처리 중'}
                session={item}
                compact
              />
            ))}
          </div>
        )}
      </section>

      <section>
        <div className="section-header">
          <h3>출력 대기</h3>
        </div>
        {printReadySessions.length === 0 ? (
          <div className="empty-gallery">출력 대기 세션이 없습니다</div>
        ) : (
          <div className="queue-grid">
            {printReadySessions.map((item) => (
              <SessionCard key={item.session_id} title="출력 대기" session={item}>
                <div className="queue-card-actions">
                  <button
                    className="btn-primary"
                    onClick={() => completeSession(item.session_id).catch((err) => flash(err.message, 'err'))}
                  >
                    인화 완료 처리
                  </button>
                </div>
              </SessionCard>
            ))}
          </div>
        )}
      </section>

      {erroredSessions.length > 0 && (
        <section>
          <div className="section-header">
            <h3>오류 세션</h3>
          </div>
          <div className="queue-grid">
            {erroredSessions.map((item) => (
              <SessionCard key={item.session_id} title="오류" session={item} compact />
            ))}
          </div>
        </section>
      )}

      <section>
        <h3>이미지 직접 업로드</h3>
        {uploadPreview && <img src={uploadPreview} alt="preview" className="upload-preview" />}
        <div className="form-row" style={{ marginTop: uploadPreview ? 10 : 0 }}>
          <label className="file-label">
            {uploadFile ? uploadFile.name : '사진 선택'}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              capture="environment"
              style={{ display: 'none' }}
              onChange={handleImageSelect}
            />
          </label>
          <button className="btn-primary" onClick={handleImageUpload}>업로드</button>
        </div>
      </section>

      <section>
        <div className="section-header" onClick={() => setPresetsOpen((open) => !open)} style={{ cursor: 'pointer' }}>
          <h3>워크플로우 프리셋 {presetsOpen ? '▲' : '▼'}</h3>
        </div>
        {presetsOpen && (
          <>
            {presets.length === 0 && <div className="warn-box">등록된 프리셋이 없습니다.</div>}
            {presets.length > 0 && !activePreset && <div className="warn-box">활성화된 프리셋이 없습니다.</div>}
            <ul className="preset-list">
              {presets.map((name) => (
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
              ComfyUI에서 <strong>Save (API Format)</strong>으로 내보낸 workflow.json만 사용합니다.
            </div>
            <div className="form-col">
              <div className="form-row">
                <input placeholder="프리셋 이름" value={presetName} onChange={(e) => setPresetName(e.target.value)} />
                <label className="file-label">
                  {presetFile ? presetFile.name : 'workflow.json 선택'}
                  <input type="file" accept=".json" style={{ display: 'none' }} onChange={(e) => setPresetFile(e.target.files?.[0] || null)} />
                </label>
              </div>
              <label className="checkbox-row">
                <input type="checkbox" checked={autoActivate} onChange={(e) => setAutoActivate(e.target.checked)} />
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
