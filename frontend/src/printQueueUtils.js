function toTimestamp(session) {
  return Date.parse(session?.created_at || '') || 0
}

export function orderSessionsByCreatedAt(sessions = [], direction = 'asc') {
  const factor = direction === 'desc' ? -1 : 1
  return [...sessions].sort((a, b) => {
    const timeDiff = (toTimestamp(a) - toTimestamp(b)) * factor
    if (timeDiff !== 0) return timeDiff
    return String(a?.session_id || '').localeCompare(String(b?.session_id || '')) * factor
  })
}

export function buildPrintSessionPool({
  printReadySessions = [],
  processingSessions = [],
  completedSessions = [],
  erroredSessions = [],
} = {}) {
  const ready = orderSessionsByCreatedAt(printReadySessions, 'asc')
  const processing = orderSessionsByCreatedAt(processingSessions, 'asc')
  const errored = orderSessionsByCreatedAt(erroredSessions, 'desc')
  const completed = orderSessionsByCreatedAt(completedSessions, 'desc')
  return [...ready, ...processing, ...errored, ...completed]
}

export function nextPrintSessionIdAfterComplete(currentSessionId, sessions = []) {
  return sessions.find((session) => session.session_id !== currentSessionId)?.session_id || null
}
