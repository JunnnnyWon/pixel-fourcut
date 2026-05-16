export function getScalePercent(scale) {
  return Math.max(0, Math.min(100, Math.round((scale - 1) * 100)))
}

export function scaleFromPercent(percent) {
  return Number((1 + percent / 100).toFixed(2))
}

export function clampScale(scale) {
  return Math.max(1, Math.min(2, Number(scale.toFixed(2))))
}

export function getCoverSize(source, target) {
  if (!source?.width || !source?.height || !target?.width || !target?.height) {
    return { width: target.width, height: target.height }
  }

  const scale = Math.max(target.width / source.width, target.height / source.height)
  return {
    width: source.width * scale,
    height: source.height * scale,
  }
}

export function applyDragDelta(origin, deltaX, deltaY, previewScale) {
  return {
    offset_x: origin.offset_x + Math.round(deltaX / previewScale),
    offset_y: origin.offset_y + Math.round(deltaY / previewScale),
  }
}

export function applyResizeDelta({
  origin,
  handle,
  baseSize,
  startScale,
  deltaX,
  deltaY,
  previewScale,
}) {
  const startWidth = baseSize.width * startScale
  const startHeight = baseSize.height * startScale
  const logicalDeltaX = deltaX / previewScale
  const logicalDeltaY = deltaY / previewScale
  const nextWidth = Math.max(baseSize.width, startWidth + handle.sx * logicalDeltaX)
  const nextHeight = Math.max(baseSize.height, startHeight + handle.sy * logicalDeltaY)
  const nextScale = clampScale(Math.max(nextWidth / baseSize.width, nextHeight / baseSize.height))
  const effectiveWidth = baseSize.width * nextScale
  const effectiveHeight = baseSize.height * nextScale
  const widthDelta = effectiveWidth - startWidth
  const heightDelta = effectiveHeight - startHeight

  return {
    scale: nextScale,
    offset_x: Math.round(origin.offset_x + (handle.sx * widthDelta) / 2),
    offset_y: Math.round(origin.offset_y + (handle.sy * heightDelta) / 2),
  }
}
