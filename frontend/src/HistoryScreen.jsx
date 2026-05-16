import { useMemo, useState } from 'react'
import OperatorNav from './OperatorNav'
import GalleryLightbox from './GalleryLightbox'
import { useSession } from './useSession'
import { PHASE_LABEL, sessionHeroImage, sessionSummaryText } from './sessionViewUtils'
import './App.css'

function toGalleryItems(items = []) {
  return items.map((item) => ({
    url: item.url,
    label: item.source_filename || item.filename || item.shot_id || item.result_id || item.print_id,
  }))
}

export default function HistoryScreen() {
  const { allSessions } = useSession()
  const [selectedSessionId, setSelectedSessionId] = useState(null)
  const [lightbox, setLightbox] = useState(null)

  const selectedSession = useMemo(() => {
    if (!allSessions.length) return null
    return allSessions.find((item) => item.session_id === selectedSessionId) || allSessions[0]
  }, [allSessions, selectedSessionId])

  const openGallery = (type, items, index) => {
    setLightbox({ type, items: toGalleryItems(items), index })
  }

  const shiftGallery = (delta) => {
    setLightbox((current) => {
      if (!current) return current
      const nextIndex = (current.index + delta + current.items.length) % current.items.length
      return { ...current, index: nextIndex }
    })
  }

  return (
    <div className="admin admin-wide">
      <div className="admin-topbar">
        <span className="brand">픽셀네컷 지난 팀</span>
      </div>
      <OperatorNav />

      <section>
        <div className="section-header">
          <h3>지난 팀 목록</h3>
        </div>
        {allSessions.length === 0 ? (
          <div className="friendly-empty">아직 기록된 팀이 없습니다.</div>
        ) : (
          <div className="history-layout">
            <div className="history-list">
              {allSessions.map((session) => (
                <button
                  key={session.session_id}
                  className={`history-row ${selectedSession?.session_id === session.session_id ? 'selected' : ''}`}
                  onClick={() => setSelectedSessionId(session.session_id)}
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
              {!selectedSession ? (
                <div className="friendly-empty">세션을 선택하면 사진, AI 결과, 인화본을 확인할 수 있습니다.</div>
              ) : (
                <>
                  <div className="history-detail-head">
                    <div>
                      <div className="summary-label">선택 세션</div>
                      <strong>{selectedSession.session_id}</strong>
                    </div>
                    <span className={`phase-badge phase-${selectedSession.phase}`}>{PHASE_LABEL[selectedSession.phase] || selectedSession.phase}</span>
                  </div>

                  <div className="history-detail-meta">
                    <span>{sessionSummaryText(selectedSession)}</span>
                    {selectedSession.error ? <span>오류: {selectedSession.error}</span> : null}
                  </div>

                  {sessionHeroImage(selectedSession) ? (
                    <img src={sessionHeroImage(selectedSession)} alt={selectedSession.session_id} className="history-detail-image history-hero-image" />
                  ) : null}

                  <div className="section-header compact">
                    <h3>촬영 사진 갤러리</h3>
                  </div>
                  <div className="shot-picker gallery-grid">
                    {(selectedSession.shots || []).map((shot, index) => (
                      <button key={shot.shot_id} className="shot-tile" onClick={() => openGallery('촬영 사진', selectedSession.shots, index)}>
                        <img src={shot.url} alt={shot.filename} />
                        <span>{shot.source_filename || shot.filename}</span>
                      </button>
                    ))}
                  </div>

                  <div className="section-header compact">
                    <h3>AI 결과 갤러리</h3>
                  </div>
                  <div className="result-history-grid selectable-grid">
                    {(selectedSession.generated_results || []).map((result, index) => (
                      <button key={result.result_id} className="result-history-card result-pick" onClick={() => openGallery('AI 결과', selectedSession.generated_results, index)}>
                        <img src={result.url} alt={result.filename} className="history-detail-image result-thumb" />
                        <div className="history-row-sub">{result.source_filename || result.filename}</div>
                      </button>
                    ))}
                  </div>

                  <div className="section-header compact">
                    <h3>인화본 기록</h3>
                  </div>
                  <div className="print-output-grid">
                    {(selectedSession.print_outputs || []).length === 0 ? (
                      <div className="history-empty">저장된 인화본이 없습니다.</div>
                    ) : (
                      selectedSession.print_outputs.map((printOutput, index) => (
                        <button key={printOutput.print_id} className="result-history-card result-pick" onClick={() => openGallery('인화본', selectedSession.print_outputs, index)}>
                          <img src={printOutput.url} alt={printOutput.filename} className="history-detail-image result-thumb" />
                          <div className="history-row-sub">{printOutput.filename}</div>
                        </button>
                      ))
                    )}
                  </div>
                </>
              )}
            </div>
          </div>
        )}
      </section>

      {lightbox ? (
        <GalleryLightbox
          items={lightbox.items}
          index={lightbox.index}
          title={lightbox.type}
          onClose={() => setLightbox(null)}
          onPrev={() => shiftGallery(-1)}
          onNext={() => shiftGallery(1)}
          onSelect={(index) => setLightbox((current) => current ? { ...current, index } : current)}
        />
      ) : null}
    </div>
  )
}
