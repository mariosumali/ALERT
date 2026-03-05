import { useState, useMemo, useRef, useEffect, useCallback } from 'react'
import { useVideo } from '../contexts/VideoContext'
import type { DetectedEvent } from '../types/events'
import { getEventColor, formatTimestamp } from '../types/events'

interface EventPanelProps {
  events: DetectedEvent[]
  isProcessing: boolean
  selectedEventId: string | null
  onSelectEvent: (ev: DetectedEvent) => void
}

export default function EventPanel({ events, isProcessing, selectedEventId, onSelectEvent }: EventPanelProps) {
  const { currentTime } = useVideo()
  const [activeFilter, setActiveFilter] = useState<string>('all')
  const [search, setSearch] = useState('')
  const [expandedId, setExpandedId] = useState<string | null>(null)
  const listRef = useRef<HTMLDivElement>(null)
  const selectedRef = useRef<HTMLButtonElement>(null)

  const eventTypes = useMemo(() => {
    const types = new Set<string>()
    events.forEach((ev) => ev.type.forEach((t) => types.add(t)))
    return Array.from(types).sort()
  }, [events])

  const filtered = useMemo(() => {
    let list = activeFilter === 'all'
      ? events
      : events.filter((ev) => ev.type.includes(activeFilter))
    if (search.trim()) {
      const q = search.toLowerCase()
      list = list.filter((ev) =>
        ev.description.toLowerCase().includes(q) ||
        ev.type.some((t) => t.toLowerCase().includes(q))
      )
    }
    return list.sort((a, b) => a.timestamp - b.timestamp)
  }, [events, activeFilter, search])

  const typeCounts = useMemo(() => {
    const counts: Record<string, number> = {}
    events.forEach((ev) => ev.type.forEach((t) => { counts[t] = (counts[t] || 0) + 1 }))
    return counts
  }, [events])

  const activeEventId = useMemo(() => {
    const active = events.find(
      (ev) => currentTime >= ev.timestamp && currentTime <= ev.endTime
    )
    return active?.id ?? null
  }, [events, currentTime])

  useEffect(() => {
    if (selectedRef.current) {
      selectedRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [selectedEventId])

  const handleKeyDown = useCallback((e: React.KeyboardEvent) => {
    if (filtered.length === 0) return
    const currentIdx = filtered.findIndex((ev) => ev.id === selectedEventId)

    if (e.key === 'ArrowDown') {
      e.preventDefault()
      const next = currentIdx < filtered.length - 1 ? currentIdx + 1 : 0
      onSelectEvent(filtered[next])
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      const prev = currentIdx > 0 ? currentIdx - 1 : filtered.length - 1
      onSelectEvent(filtered[prev])
    } else if (e.key === 'Enter' && currentIdx >= 0) {
      onSelectEvent(filtered[currentIdx])
    }
  }, [filtered, selectedEventId, onSelectEvent])

  return (
    <div className="flex flex-col h-full" onKeyDown={handleKeyDown} tabIndex={-1}>
      {/* Header */}
      <div className="px-3 py-3 flex-shrink-0" style={{ borderBottom: '1px solid hsl(var(--border))' }}>
        <div className="flex items-center justify-between mb-2">
          <span className="section-label">Detected Events</span>
          <span className="text-[11px] text-muted-2 tabular-nums">
            {filtered.length}{filtered.length !== events.length ? ` / ${events.length}` : ''}
          </span>
        </div>

        {/* Search */}
        <div className="relative mb-2">
          <svg className="absolute left-2.5 top-1/2 -translate-y-1/2 w-3 h-3 text-muted-2 pointer-events-none" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
          </svg>
          <input
            type="text"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            placeholder="Search events..."
            className="input-base pl-7 pr-3 py-1.5 text-xs"
          />
        </div>

        {/* Filter chips */}
        <div className="flex gap-1 flex-wrap">
          <button
            onClick={() => setActiveFilter('all')}
            className={`event-badge transition-colors text-[10px] ${
              activeFilter === 'all'
                ? 'bg-primary/15 text-primary'
                : 'text-muted-2 hover:text-muted'
            }`}
            style={activeFilter !== 'all' ? { background: 'hsl(var(--surface-3))' } : {}}
          >
            All ({events.length})
          </button>
          {eventTypes.map((type) => {
            const color = getEventColor(type)
            const isActive = activeFilter === type
            return (
              <button
                key={type}
                onClick={() => setActiveFilter(type)}
                className={`event-badge transition-colors text-[10px] ${
                  isActive
                    ? `${color.bg} ${color.text}`
                    : 'text-muted-2 hover:text-muted'
                }`}
                style={!isActive ? { background: 'hsl(var(--surface-3))' } : {}}
              >
                <span className={`w-1.5 h-1.5 rounded-sm ${color.dot}`} />
                {type} ({typeCounts[type] || 0})
              </button>
            )
          })}
        </div>
      </div>

      {/* Event list */}
      <div ref={listRef} className="flex-1 overflow-y-auto">
        {isProcessing && events.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center px-4">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mb-3" />
            <p className="text-sm font-medium text-muted">Analyzing footage…</p>
            <p className="text-[11px] text-muted-2 mt-1">Detecting audio and visual events</p>
          </div>
        ) : filtered.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-center px-4">
            <p className="text-sm text-muted-2">
              {events.length === 0 ? 'No events detected' : search ? 'No matching events' : `No ${activeFilter} events`}
            </p>
          </div>
        ) : (
          <div>
            {filtered.map((ev) => {
              const isSelected = ev.id === selectedEventId
              const isActive = ev.id === activeEventId
              const isExpanded = ev.id === expandedId

              return (
                <button
                  key={ev.id}
                  ref={isSelected ? selectedRef : undefined}
                  onClick={() => onSelectEvent(ev)}
                  className="w-full text-left px-3 py-2.5 transition-colors"
                  style={{
                    background: isSelected
                      ? 'hsl(var(--primary) / 0.1)'
                      : isActive
                      ? 'hsl(var(--primary) / 0.05)'
                      : 'transparent',
                    borderLeft: isSelected ? '2px solid hsl(var(--primary))' : isActive ? '2px solid hsl(var(--primary) / 0.4)' : '2px solid transparent',
                    borderBottom: '1px solid hsl(var(--border) / 0.5)',
                  }}
                  onMouseEnter={(e) => { if (!isSelected && !isActive) e.currentTarget.style.background = 'hsl(var(--surface-3) / 0.5)' }}
                  onMouseLeave={(e) => {
                    if (!isSelected && !isActive) e.currentTarget.style.background = 'transparent'
                  }}
                >
                  <div className="flex items-start justify-between gap-2">
                    <div className="flex-1 min-w-0">
                      <div className="flex items-center gap-1 flex-wrap mb-1">
                        {ev.type.map((t) => {
                          const c = getEventColor(t)
                          return (
                            <span key={t} className={`event-badge ${c.bg} ${c.text} text-[10px]`}>
                              {t}
                            </span>
                          )
                        })}
                      </div>
                      <span className="text-[11px] font-mono text-muted-2 tabular-nums">
                        {formatTimestamp(ev.timestamp)} – {formatTimestamp(ev.endTime)}
                      </span>
                      {ev.description && (
                        <p className={`text-[12px] text-muted mt-0.5 leading-snug ${isExpanded ? '' : 'line-clamp-1'}`}>
                          {ev.description}
                        </p>
                      )}
                    </div>

                    <div className="flex flex-col items-end flex-shrink-0 pt-0.5 gap-1">
                      <span className={`text-[11px] font-semibold tabular-nums ${
                        ev.confidence >= 0.8 ? 'text-success' :
                        ev.confidence >= 0.6 ? 'text-warning' :
                        'text-muted-2'
                      }`}>
                        {(ev.confidence * 100).toFixed(0)}%
                      </span>
                      <div className="w-8 h-1 rounded-full overflow-hidden" style={{ background: 'hsl(var(--surface-3))' }}>
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${ev.confidence * 100}%`,
                            background: ev.confidence >= 0.8
                              ? 'hsl(var(--success))'
                              : ev.confidence >= 0.6
                              ? 'hsl(var(--warning))'
                              : 'hsl(var(--muted-2))',
                          }}
                        />
                      </div>
                      {ev.description && (
                        <button
                          onClick={(e) => { e.stopPropagation(); setExpandedId(isExpanded ? null : ev.id) }}
                          className="text-muted-2 hover:text-muted transition-colors mt-0.5"
                        >
                          <svg className={`w-3 h-3 transition-transform ${isExpanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                            <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                          </svg>
                        </button>
                      )}
                    </div>
                  </div>
                </button>
              )
            })}
          </div>
        )}
      </div>
    </div>
  )
}
