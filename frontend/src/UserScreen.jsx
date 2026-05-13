import { useMemo } from 'react'
import { useSession } from './useSession'
import './App.css'

const PHASE_LABEL = {
  idle: '기다리는 중',
  capturing: '사진 찍는 중',
  reviewing: '사진 고르는 중',
  queued: 'AI 기다리는 중',
  processing: 'AI 그림 만드는 중',
  result_ready: '결과가 나왔어요',
  completed: '완료',
  error: '문제가 생겼어요',
}

function pickDisplaySession(currentSession, processingSessions, printReadySessions) {
  return currentSession || processingSessions[0] || printReadySessions[0] || null
}

function pickDisplayImage(session, previewActive) {
  if (!session) return null
  if (session.phase === 'result_ready' && session.result_url) return session.result_url
  if (session.phase === 'capturing' && previewActive && session.preview_shot?.url) return session.preview_shot.url
  if (session.selected_shot?.url) return session.selected_shot.url
  return session.shots?.[session.shots.length - 1]?.url || null
}

export default function UserScreen() {
  const { currentSession, processingSessions, printReadySessions, previewActive, progress, wsConnected } = useSession()

  const displaySession = useMemo(
    () => pickDisplaySession(currentSession, processingSessions, printReadySessions),
    [currentSession, processingSessions, printReadySessions],
  )
  const displayImage = pickDisplayImage(displaySession, previewActive)
  const statusLabel = PHASE_LABEL[displaySession?.phase || 'idle']

  return (
    <div className="screen public-screen">
      <div className="top-bar">
        <span className="brand">픽셀네컷</span>
        <div className="status-inline">
          <span className={`phase-badge phase-${displaySession?.phase || 'idle'}`}>{statusLabel}</span>
          <div className={`ws-dot ${wsConnected ? 'on' : 'off'}`} title={wsConnected ? '연결됨' : '연결 끊김'} />
        </div>
      </div>

      <section className="public-hero">
        <div className="public-hero-copy">
          <span className="hero-kicker">지금 상태</span>
          <h1>{statusLabel}</h1>
          <p>
            {!displaySession && '새 팀을 기다리고 있어요.'}
            {displaySession?.phase === 'capturing' && '카메라 앞에서 포즈를 잡고 사진을 찍고 있어요.'}
            {displaySession?.phase === 'reviewing' && '찍은 사진 중에서 가장 마음에 드는 사진을 고르고 있어요.'}
            {displaySession?.phase === 'queued' && '곧 AI 그림 만들기를 시작해요.'}
            {displaySession?.phase === 'processing' && 'AI가 사진을 그림으로 바꾸고 있어요.'}
            {displaySession?.phase === 'result_ready' && '결과가 준비됐어요. 곧 인화할 수 있어요.'}
          </p>
        </div>
        <div className="public-hero-stats">
          <div>
            <span className="summary-label">촬영 중인 팀</span>
            <strong>{currentSession ? '있음' : '없음'}</strong>
          </div>
          <div>
            <span className="summary-label">AI 기다리는 팀</span>
            <strong>{processingSessions.length}</strong>
          </div>
          <div>
            <span className="summary-label">인화 대기 팀</span>
            <strong>{printReadySessions.length}</strong>
          </div>
        </div>
      </section>

      <div className="preview-area public-preview">
        {displayImage ? (
          <img src={displayImage} alt="session" className="preview-img" />
        ) : (
          <div className="placeholder">현재 보여줄 사진이 없습니다.</div>
        )}
      </div>

      {displaySession?.phase === 'capturing' && previewActive && (
        <div className="status-bar">방금 찍은 사진을 잠깐 크게 보여주고 있어요.</div>
      )}

      {processingSessions.some((item) => item.phase === 'processing') && (
        <div className="status-bar">
          <div className="spinner" />
          AI 그림 만드는 중...{progress && ` (${progress.value} / ${progress.max})`}
        </div>
      )}

      <section className="public-log-section">
        <div className="section-header">
          <h3>한눈에 보기</h3>
        </div>
        <div className="public-queue-grid">
          <div className="public-queue-box">
            <div className="summary-label">사진 찍는 팀</div>
            <strong>{currentSession ? '진행 중' : '없음'}</strong>
          </div>
          <div className="public-queue-box">
            <div className="summary-label">AI 그림 만드는 팀</div>
            <strong>{processingSessions.length}팀</strong>
          </div>
          <div className="public-queue-box">
            <div className="summary-label">결과 준비된 팀</div>
            <strong>{printReadySessions.length}팀</strong>
          </div>
        </div>
      </section>
    </div>
  )
}
