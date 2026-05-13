import { useMemo, useState } from 'react'
import OperatorNav from './OperatorNav'
import { useSession } from './useSession'
import './App.css'

const PHASE_LABEL = {
  idle: '대기 중',
  capturing: '촬영 중',
  reviewing: '사진 고르기',
  queued: 'AI 대기',
  processing: 'AI 만드는 중',
  result_ready: '인화 대기',
  completed: '완료',
  error: '오류',
}

function pickSessionImage(session) {
  return session.result_url || session.selected_shot?.url || session.preview_shot?.url || session.shots?.[0]?.url || null
}

function ResultGrid({ session, onRerun }) {
  const generatedResults = session.generated_results || []
  return (
    <div className="result-history-grid">
      {generatedResults.length === 0 ? (
        <div className="history-empty">AI 결과가 아직 없습니다.</div>
      ) : (
        generatedResults.map((result) => (
          <div key={`${session.session_id}-${result.result_id}`} className="result-history-card">
            <img src={result.url} alt={result.filename} className="history-detail-image" />
            <div className="history-row-sub">{result.filename}</div>
          </div>
        ))
      )}
      <button className="btn-primary" onClick={() => onRerun(session.session_id)}>
        AI 다시 만들기
      </button>
    </div>
  )
}

export default function PrintScreen() {
  const { printReadySessions, processingSessions, completedSessions, erroredSessions, allSessions, completeSession, rerunSession } = useSession()
  const [selectedSessionId, setSelectedSessionId] = useState(null)

  const sessionPool = useMemo(() => {
    return [...printReadySessions, ...processingSessions, ...completedSessions, ...erroredSessions]
  }, [completedSessions, erroredSessions, printReadySessions, processingSessions])

  const selectedSession = useMemo(() => {
    if (!sessionPool.length) return null
    return sessionPool.find((item) => item.session_id === selectedSessionId) || sessionPool[0]
  }, [selectedSessionId, sessionPool])

  const historySessions = useMemo(() => {
    return allSessions
  }, [allSessions])

  return (
    <div className="admin">
      <div className="admin-topbar">
        <span className="brand">픽셀네컷 인화</span>
      </div>
      <OperatorNav />

      <section>
        <div className="section-header">
          <h3>지금 인화할 팀</h3>
        </div>
        {printReadySessions.length === 0 ? (
          <div className="friendly-empty">인화 대기 팀이 없습니다.</div>
        ) : (
          <div className="queue-grid">
            {printReadySessions.map((session) => (
              <button
                key={session.session_id}
                className={`history-row ${selectedSession?.session_id === session.session_id ? 'selected' : ''}`}
                onClick={() => setSelectedSessionId(session.session_id)}
              >
                <div className="history-row-main">
                  <strong>{session.session_id}</strong>
                  <span>{PHASE_LABEL[session.phase]}</span>
                </div>
                <div className="history-row-sub">
                  사진 {session.shots?.length || 0}장 · 결과 {(session.generated_results || []).length}개
                </div>
              </button>
            ))}
          </div>
        )}
      </section>

      <section>
        <div className="section-header">
          <h3>인화 작업 공간</h3>
        </div>
        {!selectedSession ? (
          <div className="friendly-empty">세션을 선택하면 원본 사진과 AI 결과를 모두 볼 수 있습니다.</div>
        ) : (
          <div className="history-layout">
            <div className="history-detail">
              <div className="history-detail-head">
                <div>
                  <div className="summary-label">선택 세션</div>
                  <strong>{selectedSession.session_id}</strong>
                </div>
                <span className={`phase-badge phase-${selectedSession.phase}`}>{PHASE_LABEL[selectedSession.phase]}</span>
              </div>
              {pickSessionImage(selectedSession) ? (
                <img src={pickSessionImage(selectedSession)} alt={selectedSession.session_id} className="history-detail-image" />
              ) : (
                <div className="history-empty">보여줄 이미지가 없습니다.</div>
              )}
              <div className="history-detail-meta">
                <span>원본 {selectedSession.shots?.length || 0}장</span>
                <span>AI 결과 {(selectedSession.generated_results || []).length}개</span>
              </div>
              <button className="btn-primary secondary" onClick={() => completeSession(selectedSession.session_id)}>
                인화 완료 처리
              </button>
            </div>

            <div className="history-detail">
              <div className="section-header">
                <h3>원본 사진</h3>
              </div>
              <div className="history-shot-grid">
                {(selectedSession.shots || []).map((shot) => (
                  <div key={`${selectedSession.session_id}-${shot.shot_id}`} className="history-shot">
                    <img src={shot.url} alt={shot.filename} />
                  </div>
                ))}
              </div>
              <div className="section-header">
                <h3>AI 결과 목록</h3>
              </div>
              <ResultGrid session={selectedSession} onRerun={rerunSession} />
              <div className="frame-placeholder">
                <strong>프레임 기능 예정</strong>
                <p>여기에 프레임 선택, 배치, 최종 인화 구성이 들어갑니다.</p>
              </div>
            </div>
          </div>
        )}
      </section>

      <section>
        <div className="section-header">
          <h3>지난 팀 목록</h3>
        </div>
        <div className="history-list">
          {historySessions.map((session) => (
            <button
              key={session.session_id}
              className={`history-row ${selectedSession?.session_id === session.session_id ? 'selected' : ''}`}
              onClick={() => setSelectedSessionId(session.session_id)}
            >
              <div className="history-row-main">
                <strong>{session.session_id}</strong>
                <span>{PHASE_LABEL[session.phase] || session.phase}</span>
              </div>
              <div className="history-row-sub">
                사진 {session.shots?.length || 0}장 · AI 결과 {(session.generated_results || []).length}개
              </div>
            </button>
          ))}
        </div>
      </section>
    </div>
  )
}
