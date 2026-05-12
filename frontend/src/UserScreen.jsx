import { useMemo } from 'react'
import { useSession } from './useSession'
import './App.css'

const PHASE_LABEL = {
  idle: '대기 중',
  capturing: '촬영 중',
  reviewing: '사진 선택 중',
  queued: 'AI 대기열',
  processing: 'AI 처리 중',
  result_ready: '결과 준비 완료',
  completed: '세션 완료',
  error: '오류',
}

function resolveHeroSession(currentSession, processingSessions, printReadySessions) {
  return currentSession || processingSessions[0] || printReadySessions[0] || null
}

function resolveHeroImage(session, previewActive) {
  if (!session) return null
  if (session.phase === 'result_ready' && session.result_url) return session.result_url
  if (session.phase === 'capturing' && previewActive && session.preview_shot?.url) return session.preview_shot.url
  if (session.selected_shot?.url) return session.selected_shot.url
  return session.shots?.[session.shots.length - 1]?.url || null
}

export default function UserScreen() {
  const {
    currentSession,
    processingSessions,
    printReadySessions,
    previewActive,
    progress,
    wsConnected,
  } = useSession()

  const heroSession = useMemo(
    () => resolveHeroSession(currentSession, processingSessions, printReadySessions),
    [currentSession, processingSessions, printReadySessions],
  )
  const heroImage = resolveHeroImage(heroSession, previewActive)

  return (
    <div className="screen public-screen">
      <div className="top-bar">
        <span className="brand">픽셀네컷</span>
        <div className="status-inline">
          <span className={`phase-badge phase-${heroSession?.phase || 'idle'}`}>
            {PHASE_LABEL[heroSession?.phase || 'idle']}
          </span>
          <div className={`ws-dot ${wsConnected ? 'on' : 'off'}`} title={wsConnected ? '연결됨' : '연결 끊김'} />
        </div>
      </div>

      <div className="status-card status-card-three">
        <div>
          <div className="status-card-label">현재 Capture</div>
          <div className="status-card-value">{currentSession?.session_id || '비어 있음'}</div>
        </div>
        <div>
          <div className="status-card-label">AI 대기/진행</div>
          <div className="status-card-value">{processingSessions.length}</div>
        </div>
        <div>
          <div className="status-card-label">출력 대기</div>
          <div className="status-card-value">{printReadySessions.length}</div>
        </div>
      </div>

      <div className="preview-area public-preview">
        {heroImage ? (
          <img src={heroImage} alt="session" className="preview-img" />
        ) : (
          <div className="placeholder">
            현재 진행 중인 세션이 없습니다.
          </div>
        )}
      </div>

      {currentSession?.phase === 'capturing' && previewActive && (
        <div className="status-bar">현재 촬영 세션의 최신 컷 프리뷰입니다.</div>
      )}

      {processingSessions.some((item) => item.phase === 'processing') && (
        <div className="status-bar">
          <div className="spinner" />
          AI 처리 중...{progress && ` (${progress.value} / ${progress.max})`}
        </div>
      )}

      {printReadySessions.length > 0 && (
        <div className="status-bar">결과가 준비된 팀이 있습니다. 운영자가 인화를 진행합니다.</div>
      )}

      <section className="public-log-section">
        <div className="section-header">
          <h3>현재 진행 현황</h3>
        </div>
        <div className="public-queue-grid">
          <div className="public-queue-box">
            <div className="summary-label">촬영 중</div>
            {currentSession ? (
              <strong>{currentSession.session_id}</strong>
            ) : (
              <span className="muted-text">없음</span>
            )}
          </div>
          <div className="public-queue-box">
            <div className="summary-label">AI 처리 대기/중</div>
            {processingSessions.length === 0 ? (
              <span className="muted-text">없음</span>
            ) : (
              processingSessions.map((item) => (
                <div key={item.session_id} className="queue-line">
                  <span>{item.session_id}</span>
                  <span className={`phase-badge phase-${item.phase}`}>{PHASE_LABEL[item.phase]}</span>
                </div>
              ))
            )}
          </div>
          <div className="public-queue-box">
            <div className="summary-label">출력 대기</div>
            {printReadySessions.length === 0 ? (
              <span className="muted-text">없음</span>
            ) : (
              printReadySessions.map((item) => (
                <div key={item.session_id} className="queue-line">
                  <span>{item.session_id}</span>
                  <span className={`phase-badge phase-${item.phase}`}>{PHASE_LABEL[item.phase]}</span>
                </div>
              ))
            )}
          </div>
        </div>
      </section>
    </div>
  )
}
