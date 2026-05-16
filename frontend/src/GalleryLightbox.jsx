import { useEffect } from 'react'

export default function GalleryLightbox({ items, index, title, onClose, onPrev, onNext, onSelect }) {
  const activeItem = items[index] || null

  useEffect(() => {
    const handleKeyDown = (event) => {
      if (event.key === 'Escape') onClose()
      if (event.key === 'ArrowLeft') onPrev()
      if (event.key === 'ArrowRight') onNext()
    }
    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [onClose, onNext, onPrev])

  if (!activeItem) return null

  return (
    <div className="gallery-lightbox" onClick={onClose} role="dialog" aria-modal="true">
      <div className="gallery-lightbox-inner" onClick={(event) => event.stopPropagation()}>
        <div className="gallery-lightbox-head">
          <div>
            <div className="summary-label">{title}</div>
            <strong>{activeItem.label}</strong>
          </div>
          <div className="action-row">
            <span className="gallery-lightbox-count">{index + 1} / {items.length}</span>
            <button className="btn-primary secondary" onClick={onClose} type="button">닫기</button>
          </div>
        </div>

        <div className="gallery-lightbox-stage">
          <button className="gallery-nav" onClick={onPrev} type="button" aria-label="이전 이미지">‹</button>
          <img src={activeItem.url} alt={activeItem.label} className="gallery-lightbox-image" />
          <button className="gallery-nav" onClick={onNext} type="button" aria-label="다음 이미지">›</button>
        </div>

        <div className="gallery-lightbox-strip">
          {items.map((item, itemIndex) => (
            <button
              key={`${item.url}-${itemIndex}`}
              className={`gallery-thumb ${itemIndex === index ? 'selected' : ''}`}
              onClick={() => onSelect(itemIndex)}
              type="button"
            >
              <img src={item.url} alt={item.label} />
            </button>
          ))}
        </div>
      </div>
    </div>
  )
}
