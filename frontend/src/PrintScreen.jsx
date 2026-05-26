import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import GalleryLightbox from './GalleryLightbox'
import OperatorNav from './OperatorNav'
import {
  applyDragDelta,
  applyResizeDelta,
  getCoverSize,
  getScalePercent,
  scaleFromPercent,
} from './printLayoutMath'
import { buildPrintSessionPool, nextPrintSessionIdAfterComplete, orderSessionsByCreatedAt } from './printQueueUtils'
import { useSession } from './useSession'
import { PHASE_LABEL } from './sessionViewUtils'
import './App.css'

const DEFAULT_LAYOUT = {
  original: { scale: 1, offset_x: 0, offset_y: 0 },
  ai: { scale: 1, offset_x: 0, offset_y: 0 },
}

const DEFAULT_SLOTS = {
  original: { x: 130, y: 350, width: 940, height: 600 },
  ai: { x: 130, y: 1000, width: 940, height: 600 },
}

const RESIZE_HANDLES = [
  { key: 'nw', sx: -1, sy: -1 },
  { key: 'ne', sx: 1, sy: -1 },
  { key: 'sw', sx: -1, sy: 1 },
  { key: 'se', sx: 1, sy: 1 },
]

function normalizeLayout(layout) {
  return {
    original: {
      scale: Number(layout?.original?.scale ?? DEFAULT_LAYOUT.original.scale),
      offset_x: Number(layout?.original?.offset_x ?? DEFAULT_LAYOUT.original.offset_x),
      offset_y: Number(layout?.original?.offset_y ?? DEFAULT_LAYOUT.original.offset_y),
    },
    ai: {
      scale: Number(layout?.ai?.scale ?? DEFAULT_LAYOUT.ai.scale),
      offset_x: Number(layout?.ai?.offset_x ?? DEFAULT_LAYOUT.ai.offset_x),
      offset_y: Number(layout?.ai?.offset_y ?? DEFAULT_LAYOUT.ai.offset_y),
    },
  }
}

function normalizeSlots(slots) {
  return {
    original: {
      x: Number(slots?.original?.x ?? DEFAULT_SLOTS.original.x),
      y: Number(slots?.original?.y ?? DEFAULT_SLOTS.original.y),
      width: Number(slots?.original?.width ?? DEFAULT_SLOTS.original.width),
      height: Number(slots?.original?.height ?? DEFAULT_SLOTS.original.height),
    },
    ai: {
      x: Number(slots?.ai?.x ?? DEFAULT_SLOTS.ai.x),
      y: Number(slots?.ai?.y ?? DEFAULT_SLOTS.ai.y),
      width: Number(slots?.ai?.width ?? DEFAULT_SLOTS.ai.width),
      height: Number(slots?.ai?.height ?? DEFAULT_SLOTS.ai.height),
    },
  }
}

function getDefaultResultId(session) {
  if (!session) return null
  return session.selected_generated_result_id || session.generated_results?.[session.generated_results.length - 1]?.result_id || null
}

function getDefaultPrintId(session) {
  if (!session) return null
  return session.latest_print_output?.print_id || session.print_outputs?.[session.print_outputs.length - 1]?.print_id || null
}

function slotStyleFromPixels(slot) {
  return {
    left: `${(slot.x / 1200) * 100}%`,
    top: `${(slot.y / 1800) * 100}%`,
    width: `${(slot.width / 1200) * 100}%`,
    height: `${(slot.height / 1800) * 100}%`,
  }
}

function scaledPreviewStyle(layout, previewScale, imageSize) {
  return {
    width: `${imageSize.width * previewScale * layout.scale}px`,
    height: `${imageSize.height * previewScale * layout.scale}px`,
    transform: `translate(calc(-50% + ${layout.offset_x * previewScale}px), calc(-50% + ${layout.offset_y * previewScale}px))`,
  }
}

function LayoutControl({ title, layout, isActive, onSelect, onScaleStep, onCenter, onReset }) {
  return (
    <div className="layout-control-card">
      <div className="layout-control-head">
        <div>
          <strong>{title}</strong>
          <div className="history-row-sub">
            {isActive ? '선택됨 · 미리보기에서 바로 드래그 가능' : '선택 후 미리보기에서 드래그'}
          </div>
        </div>
        <div className="action-row">
          <button className="btn-primary secondary" onClick={onSelect}>
            {isActive ? '선택 중' : '선택'}
          </button>
          <button className="btn-primary secondary" onClick={() => onScaleStep(-5)}>축소</button>
          <button className="btn-primary secondary" onClick={() => onScaleStep(5)}>확대</button>
          <button className="btn-primary secondary" onClick={onCenter}>가운데 정렬</button>
          <button className="btn-primary secondary" onClick={onReset}>기본값</button>
        </div>
      </div>
      <div className="layout-metrics">
        <span>확대 {getScalePercent(layout.scale)}%</span>
        <span>X {layout.offset_x}px</span>
        <span>Y {layout.offset_y}px</span>
      </div>
    </div>
  )
}

function PrintPreview({
  originalUrl,
  aiUrl,
  frameUrl,
  layout,
  slots,
  activeSlot,
  onSelectSlot,
  onDragSlot,
  onScaleSlot,
}) {
  const stageRef = useRef(null)
  const [previewScale, setPreviewScale] = useState(1)
  const [dragging, setDragging] = useState(null)
  const [resizing, setResizing] = useState(null)
  const [imageDimensions, setImageDimensions] = useState({})

  useEffect(() => {
    if (!stageRef.current) return undefined
    const node = stageRef.current
    const updateScale = () => {
      const rect = node.getBoundingClientRect()
      if (!rect.width) return
      setPreviewScale(rect.width / 1200)
    }
    updateScale()
    const observer = new ResizeObserver(updateScale)
    observer.observe(node)
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    if (!dragging && !resizing) return undefined

    const handleMove = (event) => {
      if (dragging) {
        onDragSlot(dragging.slotKey, applyDragDelta(
          {
            offset_x: dragging.originOffsetX,
            offset_y: dragging.originOffsetY,
          },
          event.clientX - dragging.startX,
          event.clientY - dragging.startY,
          previewScale,
        ))
        return
      }

      if (resizing) {
        onDragSlot(resizing.slotKey, applyResizeDelta({
          origin: {
            offset_x: resizing.originOffsetX,
            offset_y: resizing.originOffsetY,
          },
          handle: {
            sx: resizing.sx,
            sy: resizing.sy,
          },
          baseSize: {
            width: resizing.baseWidth,
            height: resizing.baseHeight,
          },
          startScale: resizing.startScale,
          deltaX: event.clientX - resizing.startX,
          deltaY: event.clientY - resizing.startY,
          previewScale,
        }))
      }
    }

    const handleUp = () => {
      setDragging(null)
      setResizing(null)
    }

    window.addEventListener('pointermove', handleMove)
    window.addEventListener('pointerup', handleUp)
    return () => {
      window.removeEventListener('pointermove', handleMove)
      window.removeEventListener('pointerup', handleUp)
    }
  }, [dragging, onDragSlot, previewScale, resizing])

  if (!frameUrl) {
    return <div className="history-empty">프레임을 선택하면 미리보기가 나타납니다.</div>
  }

  const resolvedLayout = normalizeLayout(layout)
  const resolvedSlots = normalizeSlots(slots)
  const imageBaseSize = {
    original: getCoverSize(imageDimensions.original, resolvedSlots.original),
    ai: getCoverSize(imageDimensions.ai, resolvedSlots.ai),
  }

  const beginDrag = (slotKey, event) => {
    event.preventDefault()
    event.stopPropagation()
    onSelectSlot(slotKey)
    setDragging({
      slotKey,
      startX: event.clientX,
      startY: event.clientY,
      originOffsetX: resolvedLayout[slotKey].offset_x,
      originOffsetY: resolvedLayout[slotKey].offset_y,
    })
  }

  const handleWheel = (slotKey, event) => {
    event.preventDefault()
    onSelectSlot(slotKey)
    onScaleSlot(slotKey, event.deltaY < 0 ? 5 : -5)
  }

  const beginResize = (slotKey, handle, event) => {
    event.preventDefault()
    event.stopPropagation()
    onSelectSlot(slotKey)
    const baseSize = imageBaseSize[slotKey]
    const currentScale = resolvedLayout[slotKey].scale
    setResizing({
      slotKey,
      sx: handle.sx,
      sy: handle.sy,
      startX: event.clientX,
      startY: event.clientY,
      originOffsetX: resolvedLayout[slotKey].offset_x,
      originOffsetY: resolvedLayout[slotKey].offset_y,
      baseWidth: baseSize.width,
      baseHeight: baseSize.height,
      startScale: currentScale,
    })
  }

  return (
    <div className="print-preview-stage">
      <div className="print-preview-canvas" ref={stageRef}>
        <div className={`print-preview-slot ${activeSlot === 'original' ? 'active' : ''}`} style={slotStyleFromPixels(resolvedSlots.original)}>
          <div className="print-preview-clip">
            {originalUrl ? (
              <img
                src={originalUrl}
                alt="원본 미리보기"
                className="print-preview-photo"
                style={scaledPreviewStyle(resolvedLayout.original, previewScale, imageBaseSize.original)}
                onLoad={(event) => {
                  const { naturalWidth, naturalHeight } = event.currentTarget
                  setImageDimensions((current) => ({
                    ...current,
                    original: {
                      width: naturalWidth,
                      height: naturalHeight,
                    },
                  }))
                }}
                onPointerDown={(event) => beginDrag('original', event)}
                onWheel={(event) => handleWheel('original', event)}
              />
            ) : null}
          </div>
          {activeSlot === 'original' && originalUrl ? (
            <div
              className="print-preview-selection"
              style={scaledPreviewStyle(resolvedLayout.original, previewScale, imageBaseSize.original)}
              onPointerDown={(event) => beginDrag('original', event)}
              onWheel={(event) => handleWheel('original', event)}
            >
              {RESIZE_HANDLES.map((handle) => (
                <button
                  key={handle.key}
                  className={`print-preview-handle handle-${handle.key}`}
                  onPointerDown={(event) => beginResize('original', handle, event)}
                  type="button"
                  aria-label={`원본 ${handle.key} 리사이즈`}
                />
              ))}
            </div>
          ) : null}
        </div>
        <div className={`print-preview-slot ${activeSlot === 'ai' ? 'active' : ''}`} style={slotStyleFromPixels(resolvedSlots.ai)}>
          <div className="print-preview-clip">
            {aiUrl ? (
              <img
                src={aiUrl}
                alt="AI 미리보기"
                className="print-preview-photo"
                style={scaledPreviewStyle(resolvedLayout.ai, previewScale, imageBaseSize.ai)}
                onLoad={(event) => {
                  const { naturalWidth, naturalHeight } = event.currentTarget
                  setImageDimensions((current) => ({
                    ...current,
                    ai: {
                      width: naturalWidth,
                      height: naturalHeight,
                    },
                  }))
                }}
                onPointerDown={(event) => beginDrag('ai', event)}
                onWheel={(event) => handleWheel('ai', event)}
              />
            ) : null}
          </div>
          {activeSlot === 'ai' && aiUrl ? (
            <div
              className="print-preview-selection"
              style={scaledPreviewStyle(resolvedLayout.ai, previewScale, imageBaseSize.ai)}
              onPointerDown={(event) => beginDrag('ai', event)}
              onWheel={(event) => handleWheel('ai', event)}
            >
              {RESIZE_HANDLES.map((handle) => (
                <button
                  key={handle.key}
                  className={`print-preview-handle handle-${handle.key}`}
                  onPointerDown={(event) => beginResize('ai', handle, event)}
                  type="button"
                  aria-label={`AI ${handle.key} 리사이즈`}
                />
              ))}
            </div>
          ) : null}
        </div>
        <img src={frameUrl} alt="프레임 미리보기" className="print-preview-frame" />
      </div>
    </div>
  )
}

export default function PrintScreen() {
  const {
    printReadySessions,
    processingSessions,
    completedSessions,
    erroredSessions,
    completeSession,
    composePrint,
  } = useSession()
  const [selectedSessionId, setSelectedSessionId] = useState(null)
  const [frames, setFrames] = useState([])
  const [frameError, setFrameError] = useState('')
  const [composeError, setComposeError] = useState('')
  const [composeBusy, setComposeBusy] = useState(false)
  const [printers, setPrinters] = useState([])
  const [printerDiagnostics, setPrinterDiagnostics] = useState(null)
  const [printerError, setPrinterError] = useState('')
  const [printerCapabilities, setPrinterCapabilities] = useState(null)
  const [selectedPrinterName, setSelectedPrinterName] = useState('')
  const [printCopies, setPrintCopies] = useState(1)
  const [printBusy, setPrintBusy] = useState(false)
  const [printError, setPrintError] = useState('')
  const [testPrintBusy, setTestPrintBusy] = useState(false)
  const [printInfo, setPrintInfo] = useState('')
  const [refreshPrintJobsBusy, setRefreshPrintJobsBusy] = useState(false)
  const [selectedFrameChoice, setSelectedFrameChoice] = useState(null)
  const [selectedResultChoice, setSelectedResultChoice] = useState(null)
  const [selectedPrintChoice, setSelectedPrintChoice] = useState(null)
  const [layoutDrafts, setLayoutDrafts] = useState({})
  const [activeSlot, setActiveSlot] = useState('original')
  const [lightbox, setLightbox] = useState(null)

  useEffect(() => {
    let cancelled = false

    const loadFrames = async () => {
      try {
        const response = await fetch('/api/frames')
        const data = await response.json()
        if (!response.ok) {
          throw new Error(data.detail || '프레임 목록을 불러오지 못했습니다.')
        }
        if (!cancelled) {
          setFrames(data.frames || [])
          setFrameError('')
        }
      } catch (error) {
        if (!cancelled) {
          setFrameError(error.message || '프레임 목록을 불러오지 못했습니다.')
        }
      }
    }

    loadFrames()
    return () => {
      cancelled = true
    }
  }, [])

  const loadPrinters = useCallback(async () => {
    const [printerResponse, diagnosticsResponse] = await Promise.all([
      fetch('/api/printers'),
      fetch('/api/printers/diagnostics'),
    ])
    const printerData = await printerResponse.json().catch(() => ({}))
    const diagnosticsData = await diagnosticsResponse.json().catch(() => ({}))
    if (!printerResponse.ok) {
      throw new Error(printerData.detail || '프린터 목록을 불러오지 못했습니다.')
    }
    const nextPrinters = printerData.printers || []
    setPrinters(nextPrinters)
    setPrinterDiagnostics(diagnosticsResponse.ok ? diagnosticsData : null)
    if (nextPrinters.length === 0) {
      setPrinterCapabilities(null)
    }
    setPrinterError('')
    setSelectedPrinterName((current) => {
      if (current && nextPrinters.some((printer) => printer.name === current)) {
        return current
      }
      const preferred = nextPrinters.find((printer) => printer.is_available) || nextPrinters[0]
      return preferred?.name || ''
    })
  }, [])

  useEffect(() => {
    let cancelled = false

    const run = async () => {
      try {
        await loadPrinters()
      } catch (error) {
        if (!cancelled) {
          setPrinterError(error.message || '프린터 목록을 불러오지 못했습니다.')
        }
      }
    }

    run()
    return () => {
      cancelled = true
    }
  }, [loadPrinters])

  useEffect(() => {
    let cancelled = false
    if (!selectedPrinterName) {
      return () => {
        cancelled = true
      }
    }

    const loadCapabilities = async () => {
      try {
        const response = await fetch(`/api/printers/${encodeURIComponent(selectedPrinterName)}/capabilities`)
        const data = await response.json().catch(() => ({}))
        if (!response.ok) {
          throw new Error(data.detail || '프린터 용지 정보를 불러오지 못했습니다.')
        }
        if (!cancelled) {
          setPrinterCapabilities(data)
        }
      } catch {
        if (!cancelled) {
          setPrinterCapabilities(null)
        }
      }
    }

    loadCapabilities()
    return () => {
      cancelled = true
    }
  }, [selectedPrinterName])

  const sessionPool = useMemo(() => {
    return buildPrintSessionPool({
      printReadySessions,
      processingSessions,
      completedSessions,
      erroredSessions,
    })
  }, [completedSessions, erroredSessions, printReadySessions, processingSessions])

  const prioritizedPrintReadySessions = useMemo(() => orderSessionsByCreatedAt(printReadySessions, 'asc'), [printReadySessions])

  const selectedSession = useMemo(() => {
    if (!sessionPool.length) return null
    return sessionPool.find((item) => item.session_id === selectedSessionId) || sessionPool[0]
  }, [selectedSessionId, sessionPool])

  const selectedFrameId = useMemo(() => {
    if (!selectedSession) return null
    if (selectedFrameChoice && frames.some((frame) => frame.frame_id === selectedFrameChoice)) {
      return selectedFrameChoice
    }
    return selectedSession.selected_frame_id || frames[0]?.frame_id || null
  }, [frames, selectedFrameChoice, selectedSession])

  const selectedResultId = useMemo(() => {
    if (!selectedSession) return null
    if (selectedResultChoice && selectedSession.generated_results?.some((result) => result.result_id === selectedResultChoice)) {
      return selectedResultChoice
    }
    return getDefaultResultId(selectedSession)
  }, [selectedResultChoice, selectedSession])

  const selectedPrintId = useMemo(() => {
    if (!selectedSession) return null
    if (selectedPrintChoice && selectedSession.print_outputs?.some((printOutput) => printOutput.print_id === selectedPrintChoice)) {
      return selectedPrintChoice
    }
    return getDefaultPrintId(selectedSession)
  }, [selectedPrintChoice, selectedSession])

  const selectedResult = useMemo(() => {
    if (!selectedSession) return null
    return selectedSession.generated_results?.find((result) => result.result_id === selectedResultId) || null
  }, [selectedResultId, selectedSession])

  const selectedPrintOutput = useMemo(() => {
    if (!selectedSession) return null
    return selectedSession.print_outputs?.find((printOutput) => printOutput.print_id === selectedPrintId) || selectedSession.latest_print_output || null
  }, [selectedPrintId, selectedSession])
  const selectedPrinter = useMemo(
    () => printers.find((printer) => printer.name === selectedPrinterName) || null,
    [printers, selectedPrinterName],
  )
  const selectedPrintWasSent = useMemo(() => {
    if (!selectedSession || !selectedPrintOutput) return false
    return (selectedSession.printer_jobs || []).some((job) => job.print_id === selectedPrintOutput.print_id)
  }, [selectedPrintOutput, selectedSession])

  const selectedFrame = useMemo(() => {
    return frames.find((frame) => frame.frame_id === selectedFrameId) || null
  }, [frames, selectedFrameId])
  const selectedFrameSlots = normalizeSlots(selectedFrame?.slots)

  const baseLayout = useMemo(() => {
    if (selectedPrintOutput && selectedPrintOutput.frame_id === selectedFrameId && selectedPrintOutput.result_id === selectedResultId) {
      return normalizeLayout(selectedPrintOutput.layout)
    }
    return normalizeLayout(null)
  }, [selectedFrameId, selectedPrintOutput, selectedResultId])

  const draftLayoutKey = useMemo(() => {
    return `${selectedSession?.session_id || 'none'}:${selectedFrameId || 'none'}:${selectedResultId || 'none'}:${selectedPrintOutput?.print_id || 'draft'}`
  }, [selectedFrameId, selectedPrintOutput, selectedResultId, selectedSession])

  const activeLayout = layoutDrafts[draftLayoutKey] || baseLayout

  const updateSlotLayout = (slotKey, patch) => {
    setLayoutDrafts((current) => {
      const base = current[draftLayoutKey] || baseLayout
      return {
        ...current,
        [draftLayoutKey]: {
          ...base,
          [slotKey]: {
            ...base[slotKey],
            ...patch,
          },
        },
      }
    })
  }

  const adjustSlotScale = (slotKey, deltaPercent) => {
    const currentPercent = getScalePercent(activeLayout[slotKey].scale)
    const nextPercent = Math.max(0, Math.min(100, currentPercent + deltaPercent))
    updateSlotLayout(slotKey, { scale: scaleFromPercent(nextPercent) })
  }

  const handleCenterSlot = (slotKey) => {
    updateSlotLayout(slotKey, { offset_x: 0, offset_y: 0 })
  }

  const handleResetSlot = (slotKey) => {
    updateSlotLayout(slotKey, { ...DEFAULT_LAYOUT[slotKey] })
  }

  const handleComposePrint = async () => {
    if (!selectedSession || !selectedFrameId || !selectedResultId) return
    setComposeBusy(true)
    setComposeError('')
    try {
      const payload = await composePrint(selectedSession.session_id, selectedFrameId, selectedResultId, activeLayout)
      setSelectedPrintChoice(payload.print_output?.print_id || null)
    } catch (error) {
      setComposeError(error.message || '최종 인화본 생성 실패')
    } finally {
      setComposeBusy(false)
    }
  }

  const handleComplete = async () => {
    if (!selectedSession) return
    setComposeError('')
    try {
      const nextSessionId = nextPrintSessionIdAfterComplete(selectedSession.session_id, prioritizedPrintReadySessions)
      await completeSession(selectedSession.session_id, selectedPrintOutput?.print_id || null)
      setSelectedSessionId(nextSessionId)
    } catch (error) {
      setComposeError(error.message || '세션 완료 처리 실패')
    }
  }

  const handleSelectPrintOutput = (printOutput) => {
    setSelectedPrintChoice(printOutput.print_id)
    setSelectedFrameChoice(printOutput.frame_id)
    setSelectedResultChoice(printOutput.result_id)
  }

  const handleSendToPrinter = async () => {
    if (!selectedSession || !selectedPrintOutput || !selectedPrinterName) return
    setPrintBusy(true)
    setPrintError('')
    setPrintInfo('')
    try {
      const response = await fetch('/api/session/send-to-printer', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: selectedSession.session_id,
          print_id: selectedPrintOutput.print_id,
          printer_name: selectedPrinterName,
          copies: Math.max(1, Number(printCopies) || 1),
        }),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(data.detail || '프린터 출력 전송 실패')
      }
      const jobId = data?.printer_job?.windows_job_id
      setPrintInfo(`출력 전송 완료: ${selectedPrinterName}${jobId ? ` · Job ${jobId}` : ''}`)
      await loadPrinters().catch(() => {})
      const refreshResponse = await fetch(`/api/sessions/${encodeURIComponent(selectedSession.session_id)}/printer-jobs/refresh`, {
        method: 'POST',
      })
      if (refreshResponse.ok) {
        await refreshResponse.json().catch(() => ({}))
      }
    } catch (error) {
      setPrintError(error.message || '프린터 출력 전송 실패')
    } finally {
      setPrintBusy(false)
    }
  }

  const handleRefreshPrinterJobs = async () => {
    if (!selectedSession) return
    setRefreshPrintJobsBusy(true)
    setPrintError('')
    setPrintInfo('')
    try {
      const response = await fetch(`/api/sessions/${encodeURIComponent(selectedSession.session_id)}/printer-jobs/refresh`, {
        method: 'POST',
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(data.detail || '출력 상태 새로고침 실패')
      }
    } catch (error) {
      setPrintError(error.message || '출력 상태 새로고침 실패')
    } finally {
      setRefreshPrintJobsBusy(false)
    }
  }

  const handleSendTestPage = async () => {
    if (!selectedPrinterName) return
    setTestPrintBusy(true)
    setPrintError('')
    setPrintInfo('')
    try {
      const response = await fetch('/api/printers/test-page', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          printer_name: selectedPrinterName,
          copies: 1,
        }),
      })
      const data = await response.json().catch(() => ({}))
      if (!response.ok) {
        throw new Error(data.detail || '테스트 페이지 출력 실패')
      }
      const jobId = data?.dispatch?.windows_job_id
      setPrintInfo(`테스트 페이지 전송 완료: ${selectedPrinterName}${jobId ? ` · Job ${jobId}` : ''}`)
      await loadPrinters().catch(() => {})
    } catch (error) {
      setPrintError(error.message || '테스트 페이지 출력 실패')
    } finally {
      setTestPrintBusy(false)
    }
  }

  const openGallery = (title, items, index = 0) => {
    setLightbox({
      title,
      items: items.map((item) => ({
        url: item.url,
        label: item.source_filename || item.filename || item.shot_id || item.result_id || item.print_id,
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

  return (
    <div className="admin admin-wide">
      <div className="admin-topbar">
        <span className="brand">픽셀네컷 인화 작업실</span>
      </div>
      <OperatorNav />

      <section>
        <div className="section-header">
          <h3>지금 인화할 팀</h3>
        </div>
        {prioritizedPrintReadySessions.length === 0 ? (
          <div className="friendly-empty">인화 대기 팀이 없습니다.</div>
        ) : (
          <div className="queue-grid print-priority-grid">
            {prioritizedPrintReadySessions.map((session, index) => (
              <button
                key={session.session_id}
                className={`history-row print-priority-card ${selectedSession?.session_id === session.session_id ? 'selected' : ''}`}
                onClick={() => setSelectedSessionId(session.session_id)}
              >
                <div className="history-row-main">
                  <strong>{index + 1}. {session.session_id}</strong>
                  <span>{PHASE_LABEL[session.phase]}</span>
                </div>
                <div className="history-row-sub">
                  사진 {session.shots?.length || 0}장 · 결과 {(session.generated_results || []).length}개 · 인화본 {(session.print_outputs || []).length}개
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
          <div className="friendly-empty">세션을 선택하면 원본, AI 결과, 프레임, 인화본을 한 화면에서 관리할 수 있습니다.</div>
        ) : (
          <div className="print-operator-layout">
            <div className="composition-stage">
              <div className="print-card print-session-card">
                <div className="print-stage-header">
                  <div>
                    <div className="summary-label">선택 세션</div>
                    <strong>{selectedSession.session_id}</strong>
                  </div>
                  <span className={`phase-badge phase-${selectedSession.phase}`}>{PHASE_LABEL[selectedSession.phase]}</span>
                </div>
                <div className="session-stat-grid">
                  <div className="session-stat-card">
                    <span className="summary-label">우선순위</span>
                    <strong>{
                      (() => {
                        const priorityIndex = prioritizedPrintReadySessions.findIndex((item) => item.session_id === selectedSession.session_id)
                        return priorityIndex >= 0 ? `${priorityIndex + 1}번` : '대기열 외'
                      })()
                    }</strong>
                  </div>
                  <div className="session-stat-card">
                    <span className="summary-label">원본 컷</span>
                    <strong>{selectedSession.shots?.length || 0}장</strong>
                  </div>
                  <div className="session-stat-card">
                    <span className="summary-label">AI 결과</span>
                    <strong>{(selectedSession.generated_results || []).length}개</strong>
                  </div>
                  <div className="session-stat-card">
                    <span className="summary-label">저장된 인화본</span>
                    <strong>{(selectedSession.print_outputs || []).length}개</strong>
                  </div>
                </div>
              </div>

              <div className="preview-pair">
                <div className="print-card preview-card">
                  <div className="section-header compact">
                    <h3>선택된 원본 컷</h3>
                    {selectedSession.selected_shot ? (
                      <button
                        className="btn-primary secondary"
                        onClick={() => openGallery('원본 사진', selectedSession.shots || [], (selectedSession.shots || []).findIndex((item) => item.shot_id === selectedSession.selected_shot.shot_id))}
                      >
                        크게 보기
                      </button>
                    ) : null}
                  </div>
                  {selectedSession.selected_shot ? (
                    <>
                      <button className="image-button" onClick={() => openGallery('원본 사진', selectedSession.shots || [], (selectedSession.shots || []).findIndex((item) => item.shot_id === selectedSession.selected_shot.shot_id))}>
                        <img src={selectedSession.selected_shot.url} alt={selectedSession.selected_shot.filename} className="history-detail-image print-primary-image preview-card-image" />
                      </button>
                      <div className="history-row-sub print-card-muted text-ellipsis">{selectedSession.selected_shot.filename}</div>
                    </>
                  ) : (
                    <div className="history-empty">선택된 원본 컷이 없습니다.</div>
                  )}
                </div>

                <div className="print-card preview-card">
                  <div className="section-header compact">
                    <h3>선택된 AI 결과</h3>
                    {(selectedSession.generated_results || []).length > 0 ? (
                      <button className="btn-primary secondary" onClick={() => openGallery('AI 결과', selectedSession.generated_results || [], 0)}>
                        결과 모아보기
                      </button>
                    ) : null}
                  </div>
                  {selectedResult ? (
                    <>
                      <button className="image-button" onClick={() => openGallery('AI 결과', selectedSession.generated_results || [], (selectedSession.generated_results || []).findIndex((item) => item.result_id === selectedResult.result_id))}>
                        <img src={selectedResult.url} alt={selectedResult.filename} className="history-detail-image print-primary-image preview-card-image" />
                      </button>
                      <div className="history-row-sub print-card-muted text-ellipsis">{selectedResult.filename}</div>
                      <div className="history-row-sub print-card-muted text-ellipsis">소스 컷: {selectedResult.source_shot_filename || '기록 없음'}</div>
                    </>
                  ) : (
                    <div className="history-empty">AI 결과를 먼저 선택하세요.</div>
                  )}
                </div>
              </div>

              <div className="print-card">
                <div className="section-header compact">
                  <h3>AI 결과 선택</h3>
                </div>
                <div className="result-history-grid selectable-grid compact-gallery-grid">
                  {(selectedSession.generated_results || []).map((result, index) => (
                    <button
                      key={`${selectedSession.session_id}-${result.result_id}`}
                      className={`result-history-card result-pick ${selectedResultId === result.result_id ? 'selected' : ''}`}
                      onClick={() => setSelectedResultChoice(result.result_id)}
                      onDoubleClick={() => openGallery('AI 결과', selectedSession.generated_results || [], index)}
                    >
                      <img src={result.url} alt={result.filename} className="history-detail-image result-thumb" />
                      <div className="history-row-sub text-ellipsis">{result.filename}</div>
                      <div className="history-row-sub text-ellipsis">소스 컷: {result.source_shot_filename || '기록 없음'}</div>
                    </button>
                  ))}
                </div>
              </div>

              <div className="print-card">
                <div className="section-header compact">
                  <h3>프레임 선택</h3>
                </div>
                {frameError ? (
                  <div className="friendly-empty">{frameError}</div>
                ) : (
                  <div className="frame-grid compact-gallery-grid">
                    {frames.map((frame) => (
                      <button
                        key={frame.frame_id}
                        className={`frame-card ${selectedFrameId === frame.frame_id ? 'selected' : ''}`}
                        onClick={() => setSelectedFrameChoice(frame.frame_id)}
                      >
                        <img src={frame.url} alt={frame.label} className="frame-thumb" />
                        <span>{frame.label}</span>
                      </button>
                    ))}
                  </div>
                )}

                <div className="compose-panel print-compose-panel">
                  <div className="print-selection-summary">
                    <div className="summary-label">현재 선택</div>
                    <strong>{selectedFrame?.label || '프레임 없음'}</strong>
                    <div className="history-row-sub">위에는 일반 사진, 아래에는 선택한 AI 결과가 들어갑니다.</div>
                  </div>
                  <button
                    className="btn-primary compose-button"
                    disabled={!selectedFrameId || !selectedResultId || composeBusy}
                    onClick={handleComposePrint}
                  >
                    {composeBusy ? '최종 인화본 만드는 중...' : '최종 인화본 만들기'}
                  </button>
                </div>
                {composeError ? <div className="flash flash-err">{composeError}</div> : null}
              </div>

              <div className="print-card">
                <div className="section-header compact">
                  <h3>최종 인화본 레이아웃 조정</h3>
                </div>
                <PrintPreview
                  originalUrl={selectedSession.selected_shot?.url}
                  aiUrl={selectedResult?.url}
                  frameUrl={selectedFrame?.url}
                  layout={activeLayout}
                  slots={selectedFrameSlots}
                  activeSlot={activeSlot}
                  onSelectSlot={setActiveSlot}
                  onDragSlot={updateSlotLayout}
                  onScaleSlot={adjustSlotScale}
                />

                <div className="layout-editor-grid">
                  <LayoutControl
                    title="일반 사진"
                    layout={activeLayout.original}
                    isActive={activeSlot === 'original'}
                    onSelect={() => setActiveSlot('original')}
                    onScaleStep={(delta) => adjustSlotScale('original', delta)}
                    onCenter={() => handleCenterSlot('original')}
                    onReset={() => handleResetSlot('original')}
                  />
                  <LayoutControl
                    title="AI 사진"
                    layout={activeLayout.ai}
                    isActive={activeSlot === 'ai'}
                    onSelect={() => setActiveSlot('ai')}
                    onScaleStep={(delta) => adjustSlotScale('ai', delta)}
                    onCenter={() => handleCenterSlot('ai')}
                    onReset={() => handleResetSlot('ai')}
                  />
                </div>
              </div>

              <div className="print-card">
                <div className="section-header compact">
                  <h3>저장된 인화본</h3>
                  {(selectedSession.print_outputs || []).length > 0 ? (
                    <button className="btn-primary secondary" onClick={() => openGallery('인화본', selectedSession.print_outputs || [], 0)}>
                      전체화면 보기
                    </button>
                  ) : null}
                </div>
                <div className="print-output-grid compact-gallery-grid">
                  {(selectedSession.print_outputs || []).length === 0 ? (
                    <div className="history-empty">아직 저장된 인화본이 없습니다.</div>
                  ) : (
                    selectedSession.print_outputs.map((printOutput, index) => (
                      <button
                        key={`${selectedSession.session_id}-${printOutput.print_id}`}
                        className={`result-history-card result-pick ${selectedPrintId === printOutput.print_id ? 'selected' : ''}`}
                        onClick={() => handleSelectPrintOutput(printOutput)}
                        onDoubleClick={() => openGallery('인화본', selectedSession.print_outputs || [], index)}
                      >
                        <img src={printOutput.url} alt={printOutput.filename} className="history-detail-image result-thumb" />
                        <div className="history-row-sub text-ellipsis">{printOutput.filename}</div>
                      </button>
                    ))
                  )}
                </div>
              </div>
            </div>

            <div className="command-sidebar">
              <div className="command-sidebar-sticky sidebar-scrollable">
                <div className="print-card unified-sidebar-card">
                  <div className="sidebar-section">
                    <div className="section-header compact">
                      <h3>출력 대상</h3>
                    </div>
                    {selectedPrintOutput ? (
                      <div className="print-sidebar-stack">
                        <button className="image-button" onClick={() => openGallery('인화본', selectedSession.print_outputs || [], (selectedSession.print_outputs || []).findIndex((item) => item.print_id === selectedPrintOutput.print_id))}>
                          <img src={selectedPrintOutput.url} alt={selectedPrintOutput.filename} className="history-detail-image print-final-preview" />
                        </button>
                        <div className="print-meta-list">
                          <div className="print-meta-row">
                            <span className="summary-label">파일</span>
                            <strong className="text-ellipsis">{selectedPrintOutput.filename}</strong>
                          </div>
                          <div className="print-meta-row">
                            <span className="summary-label">프레임</span>
                            <strong>{selectedPrintOutput.frame_id}</strong>
                          </div>
                          <div className="print-meta-row">
                            <span className="summary-label">원본 확대</span>
                            <strong>{Math.round((selectedPrintOutput.layout?.original?.scale ?? 1) * 100)}%</strong>
                          </div>
                          {selectedPrintOutput.last_printer_name ? (
                            <div className="print-meta-row">
                              <span className="summary-label">최근 전송</span>
                              <strong className="text-ellipsis">
                                {selectedPrintOutput.last_printer_name} · {selectedPrintOutput.copies || 1}장 · {selectedPrintOutput.job_status || selectedPrintOutput.status || 'sent'}
                                {selectedPrintOutput.windows_job_id ? ` · Job ${selectedPrintOutput.windows_job_id}` : ''}
                              </strong>
                            </div>
                          ) : null}
                          {selectedPrintOutput.document_name || selectedPrintOutput.submitted_time ? (
                            <div className="print-meta-row">
                              <span className="summary-label">스풀 정보</span>
                              <strong className="text-ellipsis">
                                {selectedPrintOutput.document_name ? `문서명 ${selectedPrintOutput.document_name}` : '문서명 없음'}
                                {selectedPrintOutput.submitted_time ? ` · 제출 ${selectedPrintOutput.submitted_time}` : ''}
                              </strong>
                            </div>
                          ) : null}
                        </div>
                      </div>
                    ) : (
                      <div className="history-empty">프레임과 위치를 조절한 뒤 최종 인화본을 만들면 여기에서 확인할 수 있습니다.</div>
                    )}
                  </div>

                  <div className="sidebar-divider" />

                  <div className="sidebar-section">
                    <div className="section-header compact">
                      <h3>프린터 출력</h3>
                      <div className="action-row">
                        <button className="btn-primary secondary" onClick={() => loadPrinters().catch((error) => setPrinterError(error.message || '프린터 목록을 불러오지 못했습니다.'))}>
                          프린터 새로고침
                        </button>
                        <button className="btn-primary secondary" disabled={!selectedSession || refreshPrintJobsBusy} onClick={handleRefreshPrinterJobs}>
                          {refreshPrintJobsBusy ? '상태 확인 중...' : '출력 상태 새로고침'}
                        </button>
                      </div>
                    </div>

                    {printerError ? <div className="history-empty">{printerError}</div> : null}
                    {!printerError && printers.length === 0 ? (
                      <div className="history-empty">표시 가능한 프린터가 없습니다. Windows에 CP1500 프린터를 설치하고, 필요하면 `PRINTER_NAME_ALLOWLIST` 설정을 확인하세요.</div>
                    ) : null}
                    {!printerError && printers.length === 0 && printerDiagnostics ? (
                      <div className="printer-diagnostics-box">
                        <div className="history-row-sub">Windows 등록 프린터 {printerDiagnostics.all_printers?.length || 0}대 · 숨김 {printerDiagnostics.hidden_printers?.length || 0}대</div>
                        <div className="history-row-sub">숨김 프린터: {printerDiagnostics.hidden_printers?.length ? printerDiagnostics.hidden_printers.map((printer) => printer.name).join(', ') : '없음'}</div>
                        <div className="history-row-sub">설치된 드라이버: {(printerDiagnostics.installed_print_drivers || []).length > 0 ? printerDiagnostics.installed_print_drivers.map((driver) => driver.name).join(', ') : '없음'}</div>
                        <div className="history-row-sub">관련 장치: {(printerDiagnostics.related_pnp_devices || []).length > 0 ? printerDiagnostics.related_pnp_devices.map((device) => device.friendly_name || device.instance_id).join(', ') : '없음'}</div>
                      </div>
                    ) : null}

                    {printers.length > 0 ? (
                      <>
                        <div className="printer-form-grid">
                          <label className="form-col">
                            <span className="summary-label">프린터 선택</span>
                            <select value={selectedPrinterName} onChange={(event) => setSelectedPrinterName(event.target.value)}>
                              {printers.map((printer) => (
                                <option key={printer.name} value={printer.name} disabled={!printer.is_available}>
                                  {printer.name}{printer.is_available ? '' : ' (오프라인)'}
                                </option>
                              ))}
                            </select>
                          </label>
                          <label className="form-col printer-copies">
                            <span className="summary-label">장수</span>
                            <input
                              type="number"
                              min="1"
                              max="9"
                              value={printCopies}
                              onChange={(event) => setPrintCopies(event.target.value)}
                            />
                          </label>
                        </div>

                        <div className="printer-toolbar">
                          <button
                            className="btn-primary printer-primary-action"
                            disabled={!selectedPrintOutput || !selectedPrinterName || !selectedPrinter?.is_available || printBusy}
                            onClick={handleSendToPrinter}
                          >
                            {printBusy ? '프린터로 보내는 중...' : '선택 프린터로 출력'}
                          </button>
                          <button
                            className="btn-primary secondary"
                            disabled={!selectedPrinterName || !selectedPrinter?.is_available || testPrintBusy}
                            onClick={handleSendTestPage}
                          >
                            {testPrintBusy ? '테스트 페이지 전송 중...' : '테스트 페이지 출력'}
                          </button>
                        </div>
                      </>
                    ) : null}

                    {printerCapabilities?.preferred_paper ? (
                      <div className="history-row-sub">추천 용지: {printerCapabilities.preferred_paper.name}{printerCapabilities.preferred_paper.width && printerCapabilities.preferred_paper.height ? ` (${printerCapabilities.preferred_paper.width}x${printerCapabilities.preferred_paper.height})` : ''}</div>
                    ) : null}
                    {selectedPrinterName && printerCapabilities && !printerCapabilities.preferred_paper ? (
                      <div className="history-row-sub">이 프린터 드라이버에서는 postcard/4x6 용지를 찾지 못했습니다.</div>
                    ) : null}
                    {selectedPrinter && !selectedPrinter.is_available ? (
                      <div className="history-row-sub">선택한 프린터가 현재 오프라인 상태입니다. 다른 프린터를 고르거나 연결 상태를 확인하세요.</div>
                    ) : null}
                    {printError ? <div className="flash flash-err">{printError}</div> : null}
                    {printInfo ? <div className="flash">{printInfo}</div> : null}
                  </div>

                  <div className="sidebar-divider" />

                  <div className="sidebar-section">
                    <div className="section-header compact">
                      <h3>출력 작업 추적</h3>
                    </div>
                    {selectedSession.latest_printer_job ? (
                      <div className="print-meta-list">
                        <div className="print-meta-row">
                          <span className="summary-label">최근 출력</span>
                          <strong className="text-ellipsis">
                            {selectedSession.latest_printer_job.printer_name} · {selectedSession.latest_printer_job.copies}장 · {selectedSession.latest_printer_job.status}
                            {selectedSession.latest_printer_job.windows_job_id ? ` · Job ${selectedSession.latest_printer_job.windows_job_id}` : ''}
                          </strong>
                        </div>
                      </div>
                    ) : (
                      <div className="history-row-sub">아직 프린터로 보낸 기록이 없습니다.</div>
                    )}

                    {(selectedSession.printer_jobs || []).length > 0 ? (
                      <div className="printer-job-list">
                        {selectedSession.printer_jobs.map((job) => (
                          <div key={job.printer_job_id} className="printer-job-card">
                            <div className="printer-job-card-head">
                              <strong className="text-ellipsis">{job.printer_name}</strong>
                              <span>{job.job_status || job.status}</span>
                            </div>
                            <div className="printer-job-meta">
                              <span className="text-ellipsis">인화본 {job.print_id}</span>
                              <span>{job.copies}장</span>
                              <span>{job.windows_job_id ? `Job ${job.windows_job_id}` : 'Job 없음'}</span>
                              <span className="text-ellipsis">{job.submitted_time || '제출 시각 없음'}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : null}
                  </div>

                  <div className="sidebar-divider" />

                  <div className="sidebar-section">
                    <div className="section-header compact">
                      <h3>프린터 상태</h3>
                    </div>
                    {printers.length > 0 ? (
                      <div className="printer-status-list">
                        {printers.map((printer) => (
                          <div key={printer.name} className="printer-status-card">
                            <div className="printer-status-card-head">
                              <strong className="text-ellipsis">{printer.name}</strong>
                              <span className={`status-chip ${printer.is_available ? 'ok' : 'warn'}`}>{printer.is_available ? '준비됨' : '오프라인'}</span>
                            </div>
                            <div className="printer-job-meta">
                              <span className="text-ellipsis">포트 {printer.port_name || '-'}</span>
                              <span className="text-ellipsis">{printer.driver_name || '-'}</span>
                            </div>
                          </div>
                        ))}
                      </div>
                    ) : (
                      <div className="history-row-sub">표시 가능한 프린터가 없으면 이 영역이 비어 있습니다.</div>
                    )}
                  </div>
                </div>

                <div className="print-card">
                  <div className="section-header compact">
                    <h3>세션 마감</h3>
                  </div>
                  <div className="print-sidebar-stack">
                    <button
                      className="btn-primary printer-primary-action"
                      disabled={!['result_ready', 'completed'].includes(selectedSession.phase) || !selectedPrintWasSent}
                      onClick={handleComplete}
                    >
                      인화 완료 처리 후 다음 팀으로
                    </button>
                    {!selectedPrintWasSent && selectedPrintOutput ? (
                      <div className="history-row-sub">완료 처리 전, 현재 선택된 인화본을 프린터로 한 번 보내야 합니다.</div>
                    ) : null}
                  </div>
                </div>
              </div>
            </div>
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
    </div>
  )
}
