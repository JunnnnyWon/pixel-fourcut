import { useCallback, useEffect, useRef, useState } from 'react'
import OperatorNav from './OperatorNav'
import { useSession } from './useSession'
import { getAdminHeroState } from './adminHeroState'
import GalleryLightbox from './GalleryLightbox'
import { PHASE_LABEL, sessionHeroImage, sessionSummaryText } from './sessionViewUtils'
import './App.css'

function QueueCard({ session, title }) {
  const heroImage = sessionHeroImage(session)
  return (
    <div className="queue-card">
      <div className="queue-card-head">
        <div>
          <div className="summary-label">{title}</div>
          <strong>{session.session_id}</strong>
        </div>
        <span className={`phase-badge phase-${session.phase}`}>{PHASE_LABEL[session.phase] || session.phase}</span>
      </div>
      <div className="queue-card-meta">
        <span>사진 {session.shots?.length || 0}장</span>
        {session.selected_shot && <span>선택 {session.selected_shot.filename}</span>}
        {session.generated_results?.length ? <span>AI {session.generated_results.length}개</span> : null}
      </div>
      {heroImage && <img src={heroImage} alt={session.session_id} className="queue-card-image" />}
    </div>
  )
}

export default function AdminScreen() {
  const {
    currentSession,
    shots,
    selectedShotId,
    selectedShot,
    progress,
    wsConnected,
    processingSessions,
    erroredSessions,
    allSessions,
    selectShot,
    rerunSession,
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
  const [selectedManageSessionId, setSelectedManageSessionId] = useState(null)
  const [selectedManageShotChoice, setSelectedManageShotChoice] = useState(null)
  const [lightbox, setLightbox] = useState(null)
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

  const handleStartSession = useCallback(async () => {
    try {
      await request('/api/session/start', { method: 'POST' }, '새 팀 시작 실패')
      flash('새 팀을 받았습니다')
    } catch (err) {
      flash(err.message, 'err')
    }
  }, [flash, request])

  const handleFinishCapture = useCallback(async () => {
    try {
      await request('/api/session/finish-capture', { method: 'POST' }, '촬영 종료 실패')
      flash('사진 고르기 단계로 넘어갑니다')
    } catch (err) {
      flash(err.message, 'err')
    }
  }, [flash, request])

  const handleRunSelected = useCallback(async () => {
    try {
      await request('/api/session/run-selected', { method: 'POST' }, 'AI 시작 실패')
      flash('AI 그림 만들기를 시작했습니다')
    } catch (err) {
      flash(err.message, 'err')
    }
  }, [flash, request])

  const handleRetryCapture = useCallback(async () => {
    try {
      await request('/api/session/retry-capture', { method: 'POST' }, '다시 촬영 실패')
      flash('다시 촬영 단계로 돌아갑니다')
    } catch (err) {
      flash(err.message, 'err')
    }
  }, [flash, request])

  const handleDiscardCurrent = useCallback(async () => {
    if (!currentSession) return
    if (!confirm('이 팀을 파기할까요?')) return
    try {
      await request('/api/session/discard', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: currentSession.session_id }),
      }, '팀 파기 실패')
      flash('현재 팀을 파기했습니다')
    } catch (err) {
      flash(err.message, 'err')
    }
  }, [currentSession, flash, request])

  const handleReset = async () => {
    if (!confirm('모든 세션과 받은 사진을 초기화할까요?')) return
    try {
      await request('/api/session/reset', { method: 'POST' }, '초기화 실패')
      flash('전체 초기화 완료')
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
      flash(currentSession?.phase === 'capturing' ? '사진이 현재 팀에 추가됩니다' : '지금은 새 팀을 시작한 뒤 업로드해야 합니다')
      setUploadFile(null)
      setUploadPreview(null)
      if (fileInputRef.current) fileInputRef.current.value = ''
    } catch (err) {
      flash(err.message, 'err')
    }
  }

  const heroState = getAdminHeroState({
    currentSession,
    selectedShot,
    activePreset,
    comfyOnline,
  })

  const handleHeroAction = async () => {
    if (heroState.actionKind === 'start') return handleStartSession()
    if (heroState.actionKind === 'finish') return handleFinishCapture()
    if (heroState.actionKind === 'run' && !heroState.disabled) return handleRunSelected()
  }

  const manageableSessions = allSessions.filter((item) => (item.shots || []).length > 0 && item.phase !== 'capturing')
  const selectedManageSession = manageableSessions.find((item) => item.session_id === selectedManageSessionId) || manageableSessions[0] || null
  const selectedManageShotId =
    (selectedManageShotChoice && selectedManageSession?.shots?.some((shot) => shot.shot_id === selectedManageShotChoice)
      ? selectedManageShotChoice
      : null) ||
    selectedManageSession?.selected_shot_id ||
    selectedManageSession?.shots?.[0]?.shot_id ||
    null
  const selectedManageShot = selectedManageSession?.shots?.find((shot) => shot.shot_id === selectedManageShotId) || null

  const openGallery = (title, items, index = 0) => {
    setLightbox({
      title,
      items: items.map((item) => ({
        url: item.url,
        label: item.source_filename || item.filename || item.shot_id || item.result_id,
      })),
      index,
    })
  }

  const shiftGallery = (delta) => {
    setLightbox((current) => {
      if (!current) return current
      const nextIndex = (current.index + delta + current.items.length) % current.items.length
      return { ...current, index: nextIndex }
    })
  }

  const handleRerunSession = async (sessionId) => {
    try {
      await rerunSession(sessionId)
      flash('AI 재생성을 시작했습니다')
    } catch (err) {
      flash(err.message, 'err')
    }
  }

  const handleManageShotSelect = async (sessionId, shotId) => {
    try {
      await request(`/api/sessions/${encodeURIComponent(sessionId)}/select-shot`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ shot_id: shotId }),
      }, '촬영 사진 선택 변경 실패')
      setSelectedManageShotChoice(shotId)
      flash('AI 재제작에 사용할 촬영 사진을 바꿨습니다')
    } catch (err) {
      flash(err.message, 'err')
    }
  }

  return (
    <div className="admin admin-wide">
      <div className="admin-topbar">
        <span className="brand">픽셀네컷 관리자</span>
        <div className="admin-status-row">
          <span className={`status-chip ${comfyOnline ? 'ok' : 'err'}`}>
            ComfyUI {comfyOnline ? '연결됨' : '오프라인'}
          </span>
          <span className={`status-chip ${activePreset ? 'ok' : 'warn'}`}>
            {activePreset ? `프리셋 ${activePreset}` : '프리셋 없음'}
          </span>
          <div className={`ws-dot ${wsConnected ? 'on' : 'off'}`} />
        </div>
      </div>
      <OperatorNav />

      {msg.text && <div className={`flash ${msg.type === 'err' ? 'flash-err' : ''}`}>{msg.text}</div>}

      <section className="hero-action">
        <div className="hero-copy">
          <span className="hero-kicker">다음으로 할 일</span>
          <h2>{heroState.title}</h2>
          <p>{heroState.description}</p>
        </div>
        <div className="hero-actions">
          <button
            className="hero-button"
            disabled={heroState.disabled}
            onClick={handleHeroAction}
          >
            {heroState.buttonLabel}
          </button>
          <button className="btn-new-guest" onClick={handleReset}>전체 초기화</button>
        </div>
      </section>

      <section>
        <div className="section-header">
          <h3>지금 촬영하는 팀</h3>
        </div>

        {!currentSession ? (
          <div className="friendly-empty">
            지금은 촬영 중인 팀이 없습니다. 위의 큰 버튼으로 바로 새 팀을 받을 수 있습니다.
          </div>
        ) : (
          <>
            <div className="session-summary session-summary-four">
              <div>
                <span className="summary-label">현재 팀</span>
                <strong>{currentSession.session_id}</strong>
              </div>
              <div>
                <span className="summary-label">상태</span>
                <strong>{PHASE_LABEL[currentSession.phase] || currentSession.phase}</strong>
              </div>
              <div>
                <span className="summary-label">받은 사진</span>
                <strong>{shots.length}장</strong>
              </div>
              <div>
                <span className="summary-label">선택한 사진</span>
                <strong>{selectedShot ? '있음' : '없음'}</strong>
              </div>
            </div>

            <div className="capture-workspace">
              <div className="capture-preview-panel">
                {sessionHeroImage(currentSession) ? (
                  <button className="image-button" onClick={() => openGallery('현재 대표 이미지', [currentSession.selected_shot || currentSession.preview_shot || currentSession.shots?.[0]].filter(Boolean), 0)}>
                    <img src={sessionHeroImage(currentSession)} alt={currentSession.session_id} className="capture-preview-image" />
                  </button>
                ) : (
                  <div className="history-empty">촬영된 사진이 아직 없습니다.</div>
                )}
                {currentSession.phase === 'reviewing' && selectedShot && (
                  <div className="selected-label">이 사진으로 AI를 만들어요</div>
                )}
                {shots.length > 0 ? (
                  <div className="action-row" style={{ marginTop: 10 }}>
                    <button className="btn-primary secondary" onClick={() => openGallery('촬영 사진', shots, 0)}>
                      촬영 사진 전체화면 보기
                    </button>
                  </div>
                ) : null}
              </div>

              <div className="capture-step-panel">
                <div className="step-card">
                  <span className="step-number">1</span>
                  <div>
                    <strong>사진이 들어오는지 확인</strong>
                    <p>카메라나 업로드로 들어온 사진이 아래에 자동으로 쌓입니다.</p>
                  </div>
                </div>
                <div className="step-card">
                  <span className="step-number">2</span>
                  <div>
                    <strong>마음에 드는 사진을 누르기</strong>
                    <p>사진을 한 장 누르면 바로 선택되고, 전체화면으로도 넘겨가며 볼 수 있습니다.</p>
                  </div>
                </div>
                <div className="step-card">
                  <span className="step-number">3</span>
                  <div>
                    <strong>큰 버튼으로 다음 단계 진행</strong>
                    <p>촬영 끝내기 또는 AI 그림 만들기를 순서대로 누르면 됩니다.</p>
                  </div>
                </div>
              </div>
            </div>

            {shots.length > 0 ? (
              <div className="shot-picker">
                {shots.map((shot) => (
                  <button
                    key={`${currentSession.session_id}-${shot.shot_id}`}
                    className={`shot-tile ${selectedShotId === shot.shot_id ? 'selected' : ''}`}
                    onClick={() => selectShot(shot.shot_id).catch((err) => flash(err.message, 'err'))}
                  >
                    <img src={shot.url} alt={shot.filename} />
                    <span>{selectedShotId === shot.shot_id ? '선택됨' : '누르면 선택'}</span>
                  </button>
                ))}
              </div>
            ) : (
              <div className="friendly-empty">
                아직 받은 사진이 없습니다.
                <div className="queue-card-actions" style={{ marginTop: 12 }}>
                  <button className="btn-primary secondary" onClick={handleRetryCapture}>다시 촬영</button>
                  <button className="btn-delete" onClick={handleDiscardCurrent}>팀 파기</button>
                </div>
              </div>
            )}
          </>
        )}

        {processingSessions.some((item) => item.phase === 'processing') && (
          <div className="status-bar" style={{ marginTop: 12 }}>
            <div className="spinner" />
            AI 그림 만드는 중...{progress && ` (${progress.value} / ${progress.max})`}
          </div>
        )}
      </section>

      {lightbox ? (
        <GalleryLightbox
          items={lightbox.items}
          index={lightbox.index}
          title={lightbox.title}
          onClose={() => setLightbox(null)}
          onPrev={() => shiftGallery(-1)}
          onNext={() => shiftGallery(1)}
          onSelect={(index) => setLightbox((current) => current ? { ...current, index } : current)}
        />
      ) : null}

      <section>
        <div className="section-header">
          <h3>기다리는 팀</h3>
        </div>
        {processingSessions.length === 0 ? (
          <div className="friendly-empty">지금은 AI를 기다리거나 만드는 팀이 없습니다.</div>
        ) : (
          <div className="queue-grid">
            {processingSessions.map((item) => (
              <QueueCard
                key={item.session_id}
                title={item.phase === 'queued' ? 'AI 기다리는 팀' : 'AI 만드는 팀'}
                session={item}
              />
            ))}
          </div>
        )}
      </section>

      <section>
        <div className="section-header">
          <h3>AI 결과 / 재제작 관리</h3>
        </div>
        {manageableSessions.length === 0 ? (
          <div className="friendly-empty">촬영 사진이 있는 세션이 아직 없습니다.</div>
        ) : (
          <div className="history-layout">
            <div className="history-list">
              {manageableSessions.map((session) => (
                <button
                  key={session.session_id}
                  className={`history-row ${selectedManageSession?.session_id === session.session_id ? 'selected' : ''}`}
                  onClick={() => setSelectedManageSessionId(session.session_id)}
                >
                  <div className="history-row-main">
                    <strong>{session.session_id}</strong>
                    <span>{PHASE_LABEL[session.phase] || session.phase}</span>
                  </div>
                  <div className="history-row-sub">{sessionSummaryText(session)}</div>
                </button>
              ))}
            </div>

            <div className="history-detail history-detail-wide">
              {selectedManageSession ? (
                <>
                  <div className="history-detail-head">
                    <div>
                      <div className="summary-label">재제작 대상 세션</div>
                      <strong>{selectedManageSession.session_id}</strong>
                    </div>
                    <div className="action-row">
                      <span className={`phase-badge phase-${selectedManageSession.phase}`}>{PHASE_LABEL[selectedManageSession.phase] || selectedManageSession.phase}</span>
                      <button className="btn-primary" onClick={() => handleRerunSession(selectedManageSession.session_id)}>
                        {selectedManageShot ? `${selectedManageShot.source_filename || selectedManageShot.filename}로 AI 다시 만들기` : 'AI 다시 만들기'}
                      </button>
                    </div>
                  </div>

                  <div className="history-detail-meta">
                    <span>촬영 사진 {selectedManageSession.shots?.length || 0}장</span>
                    <span>AI 결과 {(selectedManageSession.generated_results || []).length}개</span>
                    {selectedManageShot ? <span>다음 AI 소스: {selectedManageShot.source_filename || selectedManageShot.filename}</span> : null}
                  </div>

                  <div className="desktop-gallery-grid">
                    <div>
                      <div className="section-header compact">
                        <h3>촬영 사진 선택</h3>
                      </div>
                      <div className="shot-picker gallery-grid">
                        {(selectedManageSession.shots || []).map((shot, index) => (
                          <button
                            key={shot.shot_id}
                            className={`shot-tile ${selectedManageShotId === shot.shot_id ? 'selected' : ''}`}
                            onClick={() => handleManageShotSelect(selectedManageSession.session_id, shot.shot_id)}
                            onDoubleClick={() => openGallery('촬영 사진', selectedManageSession.shots, index)}
                          >
                            <img src={shot.url} alt={shot.filename} />
                            <span>{selectedManageShotId === shot.shot_id ? '재제작 소스로 선택됨' : (shot.source_filename || shot.filename)}</span>
                          </button>
                        ))}
                      </div>
                    </div>

                    <div>
                      <div className="section-header compact">
                        <h3>AI 결과</h3>
                      </div>
                      {(selectedManageSession.generated_results || []).length > 0 ? (
                        <div className="action-row" style={{ marginBottom: 10 }}>
                          <button className="btn-primary secondary" onClick={() => openGallery('AI 결과', selectedManageSession.generated_results, 0)}>
                            AI 결과 전체화면 보기
                          </button>
                        </div>
                      ) : <div className="history-empty">아직 AI 결과가 없습니다. 위에서 촬영 사진을 고르고 다시 만들 수 있습니다.</div>}
                      <div className="result-history-grid selectable-grid">
                        {(selectedManageSession.generated_results || []).map((result, index) => (
                          <button key={result.result_id} className="result-history-card result-pick" onClick={() => openGallery('AI 결과', selectedManageSession.generated_results, index)}>
                            <img src={result.url} alt={result.filename} className="history-detail-image result-thumb" />
                            <div className="history-row-sub">{result.source_filename || result.filename}</div>
                            <div className="history-row-sub">소스 컷: {result.source_shot_filename || '기록 없음'}</div>
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                </>
              ) : null}
            </div>
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
              <QueueCard key={item.session_id} title="오류" session={item} />
            ))}
          </div>
        </section>
      )}

      <section>
        <div className="section-header">
          <h3>테스트용 사진 직접 넣기</h3>
        </div>
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
          <button className="btn-primary" onClick={handleImageUpload}>지금 팀에 넣기</button>
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
