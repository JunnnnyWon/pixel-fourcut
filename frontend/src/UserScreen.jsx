import { useSession } from './useSession'
import './App.css'

export default function UserScreen() {
  const { images, selected, status, progress, promptId, error, wsConnected } = useSession()

  return (
    <div className="screen">
      <div className="top-bar">
        <span className="brand">픽셀네컷</span>
        <div className={`ws-dot ${wsConnected ? 'on' : 'off'}`} title={wsConnected ? '연결됨' : '연결 끊김'} />
      </div>

      {/* 갤러리 */}
      {images.length > 0 && (
        <div className="gallery">
          {images.map(fn => (
            <div key={fn} className={`thumb ${selected === fn ? 'selected' : ''}`}>
              <img src={`/api/input/${fn}`} alt={fn} />
            </div>
          ))}
        </div>
      )}

      {/* 메인 프리뷰 */}
      <div className="preview-area">
        {selected
          ? <img src={`/api/input/${selected}`} alt="selected" className="preview-img" />
          : images.length > 0
            ? <div className="placeholder">관리자가 사진을 선택하는 중...</div>
            : <div className="placeholder">촬영을 기다리는 중...</div>
        }
      </div>

      {/* 상태 표시 */}
      {status === 'processing' && (
        <div className="status-bar">
          <div className="spinner" />
          AI 처리 중...{progress && ` (${progress.value} / ${progress.max})`}
        </div>
      )}
      {status === 'error' && (
        <div className="status-bar error">❌ {error}</div>
      )}

      {/* 결과 오버레이 */}
      {status === 'done' && promptId && (
        <div className="result-overlay">
          <img src={`/api/result/${promptId}`} alt="result" className="result-img" />
          <p className="result-hint">관리자에게 문의하세요</p>
        </div>
      )}
    </div>
  )
}
