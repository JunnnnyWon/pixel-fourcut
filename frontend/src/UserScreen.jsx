import { useSession } from './useSession'
import './App.css'

const PHASE_LABEL = {
  idle: '대기 중',
  capturing: '촬영 중',
  reviewing: '사진 선택 중',
  processing: 'AI 처리 중',
  result_ready: '결과 준비 완료',
  completed: '세션 완료',
  error: '오류',
}

function resolveMainImage({ phase, selectedShot, previewShot, previewActive, shots, resultUrl }) {
  if (phase === 'result_ready' || phase === 'completed') {
    return resultUrl
  }
  if (phase === 'capturing' && previewActive && previewShot?.url) {
    return previewShot.url
  }
  if (selectedShot?.url) {
    return selectedShot.url
  }
  return shots.length > 0 ? shots[shots.length - 1].url : null
}

export default function UserScreen() {
  const { sessionId, phase, shots, selectedShot, previewShot, previewActive, resultUrl, progress, logs, error, wsConnected } = useSession()
  const mainImage = resolveMainImage({ phase, selectedShot, previewShot, previewActive, shots, resultUrl })
  const latestLogs = [...logs].slice(-6).reverse()

  return (
    <div className="screen public-screen">
      <div className="top-bar">
        <span className="brand">픽셀네컷</span>
        <div className="status-inline">
          <span className={`phase-badge phase-${phase}`}>{PHASE_LABEL[phase] || phase}</span>
          <div className={`ws-dot ${wsConnected ? 'on' : 'off'}`} title={wsConnected ? '연결됨' : '연결 끊김'} />
        </div>
      </div>

      <div className="status-card">
        <div>
          <div className="status-card-label">현재 세션</div>
          <div className="status-card-value">{sessionId || '대기 중'}</div>
        </div>
        <div>
          <div className="status-card-label">촬영 컷 수</div>
          <div className="status-card-value">{shots.length}</div>
        </div>
      </div>

      <div className="preview-area public-preview">
        {mainImage ? (
          <img src={mainImage} alt="session" className="preview-img" />
        ) : (
          <div className="placeholder">
            {phase === 'idle' ? '관리자가 새 세션을 시작하면 여기서 상태를 볼 수 있습니다.' : '사진을 기다리는 중...'}
          </div>
        )}
      </div>

      {phase === 'processing' && (
        <div className="status-bar">
          <div className="spinner" />
          AI 처리 중...{progress && ` (${progress.value} / ${progress.max})`}
        </div>
      )}

      {phase === 'capturing' && previewActive && (
        <div className="status-bar">방금 촬영한 컷을 3초 프리뷰 상태로 표시 중입니다.</div>
      )}

      {phase === 'reviewing' && (
        <div className="status-bar">관리자가 촬영본 중 베스트컷을 고르는 중입니다.</div>
      )}

      {(phase === 'result_ready' || phase === 'completed') && (
        <div className="status-bar">결과 이미지가 준비되었습니다. 관리자 안내에 따라 출력합니다.</div>
      )}

      {phase === 'error' && (
        <div className="status-bar error">오류: {error || '알 수 없는 오류'}</div>
      )}

      <section className="public-log-section">
        <div className="section-header">
          <h3>세션 로그</h3>
        </div>
        {latestLogs.length === 0 ? (
          <div className="empty-gallery">표시할 로그가 없습니다</div>
        ) : (
          <ul className="log-list">
            {latestLogs.map((log, index) => (
              <li key={`${log.at}-${index}`}>
                <span className="log-time">{log.at}</span>
                <span className="log-message">{log.message}</span>
              </li>
            ))}
          </ul>
        )}
      </section>
    </div>
  )
}
