import { useRef, useState, useCallback } from 'react'
import { useVideo } from '../contexts/VideoContext'
import type { DetectedEvent } from '../types/events'
import { getTimelineColor, formatTimestamp } from '../types/events'

interface EventTimelineProps {
  events: DetectedEvent[]
  visible: boolean
}

export default function EventTimeline({ events, visible }: EventTimelineProps) {
  const { currentTime, duration, seekTo } = useVideo()
  const trackRef = useRef<HTMLDivElement>(null)
  const [hoveredEvent, setHoveredEvent] = useState<DetectedEvent | null>(null)
  const [hoverX, setHoverX] = useState(0)
  const [hoverTime, setHoverTime] = useState<number | null>(null)

  const handleTrackClick = useCallback((e: React.MouseEvent) => {
    if (!trackRef.current || duration <= 0) return
    const rect = trackRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const ratio = x / rect.width
    seekTo(ratio * duration)
  }, [duration, seekTo])

  const handleTrackHover = useCallback((e: React.MouseEvent) => {
    if (!trackRef.current || duration <= 0) return
    const rect = trackRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const ratio = Math.max(0, Math.min(1, x / rect.width))
    setHoverX(x)
    setHoverTime(ratio * duration)
  }, [duration])

  if (!visible) return null

  const hasDuration = duration > 0
  const playheadPercent = hasDuration ? (currentTime / duration) * 100 : 0

  const eventsByType: Record<string, DetectedEvent[]> = {}
  events.forEach((ev) => {
    const mainType = ev.type[0] || 'Unknown'
    if (!eventsByType[mainType]) eventsByType[mainType] = []
    eventsByType[mainType].push(ev)
  })
  const lanes = Object.entries(eventsByType)

  return (
    <div className="card px-4 py-2.5 flex-shrink-0">
      <div className="flex items-center justify-between mb-1.5">
        <div className="flex items-center gap-3">
          <span className="section-label">Timeline</span>
          {hasDuration && (
            <span className="text-[11px] text-gray-400 dark:text-gray-500 font-mono tabular-nums">
              {formatTimestamp(currentTime)} / {formatTimestamp(duration)}
            </span>
          )}
        </div>
        {lanes.length > 0 && (
          <div className="flex items-center gap-2.5 flex-wrap">
            {lanes.map(([type]) => (
              <div key={type} className="flex items-center gap-1">
                <div
                  className="w-2 h-2 rounded-sm"
                  style={{ backgroundColor: getTimelineColor(type) }}
                />
                <span className="text-[10px] text-gray-500 dark:text-gray-500">{type}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      {/* Track */}
      <div
        ref={trackRef}
        className={`relative h-8 rounded overflow-hidden select-none group ${
          hasDuration
            ? 'bg-gray-100 dark:bg-gray-800/60 cursor-pointer'
            : 'bg-gray-100 dark:bg-gray-800/40'
        }`}
        onClick={hasDuration ? handleTrackClick : undefined}
        onMouseMove={hasDuration ? handleTrackHover : undefined}
        onMouseLeave={() => { setHoveredEvent(null); setHoverTime(null) }}
      >
        {!hasDuration && (
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-[10px] text-gray-400 dark:text-gray-600">
              Loading timeline...
            </span>
          </div>
        )}

        {/* Event segments */}
        {hasDuration && events.map((ev) => {
          const left = (ev.timestamp / duration) * 100
          const width = Math.max(((ev.endTime - ev.timestamp) / duration) * 100, 0.4)
          const color = getTimelineColor(ev.type[0] || '')
          const laneIdx = lanes.findIndex(([t]) => t === (ev.type[0] || 'Unknown'))
          const laneCount = Math.max(lanes.length, 1)
          const laneHeight = 100 / laneCount
          const top = laneIdx * laneHeight

          return (
            <div
              key={ev.id}
              className="absolute rounded-sm transition-opacity duration-75"
              style={{
                left: `${left}%`,
                width: `${width}%`,
                top: `${top}%`,
                height: `${laneHeight}%`,
                backgroundColor: color,
                opacity: hoveredEvent === ev ? 1 : 0.65,
              }}
              onMouseEnter={() => setHoveredEvent(ev)}
              onMouseLeave={() => setHoveredEvent(null)}
            />
          )
        })}

        {/* Playhead */}
        {hasDuration && (
          <div
            className="timeline-playhead pointer-events-none"
            style={{ left: `${playheadPercent}%` }}
          />
        )}

        {/* Hover tooltip */}
        {hoverTime !== null && (
          <div
            className="absolute -top-6 -translate-x-1/2 px-1.5 py-0.5 rounded bg-gray-900 dark:bg-gray-100 text-[10px] font-mono text-white dark:text-gray-900 pointer-events-none z-30 opacity-0 group-hover:opacity-100 transition-opacity"
            style={{ left: `${hoverX}px` }}
          >
            {formatTimestamp(hoverTime)}
          </div>
        )}
      </div>

      {/* Event detail on hover */}
      {hoveredEvent && (
        <div className="mt-1 flex items-center gap-2 text-[11px] animate-fade-in">
          <div
            className="w-1.5 h-1.5 rounded-sm flex-shrink-0"
            style={{ backgroundColor: getTimelineColor(hoveredEvent.type[0] || '') }}
          />
          <span className="font-medium text-gray-700 dark:text-gray-300">
            {hoveredEvent.type.join(', ')}
          </span>
          <span className="font-mono text-gray-400 tabular-nums">
            {formatTimestamp(hoveredEvent.timestamp)}
          </span>
          <span className="text-gray-500 dark:text-gray-500 truncate">
            {hoveredEvent.description}
          </span>
          <span className="text-gray-400 ml-auto flex-shrink-0 tabular-nums">
            {(hoveredEvent.confidence * 100).toFixed(0)}%
          </span>
        </div>
      )}
    </div>
  )
}
