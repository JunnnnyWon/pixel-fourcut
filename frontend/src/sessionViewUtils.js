export const PHASE_LABEL = {
  idle: '대기 중',
  capturing: '촬영 중',
  reviewing: '사진 고르기',
  queued: 'AI 대기',
  processing: 'AI 만드는 중',
  result_ready: '인화 대기',
  completed: '완료',
  error: '오류',
}

export function sessionHeroImage(session) {
  if (!session) return null
  return session.result_url || session.selected_generated_result?.url || session.selected_shot?.url || session.preview_shot?.url || session.shots?.[0]?.url || null
}

export function sessionSummaryText(session) {
  return `사진 ${session.shots?.length || 0}장 · AI 결과 ${(session.generated_results || []).length}개 · 인화본 ${(session.print_outputs || []).length}개`
}
