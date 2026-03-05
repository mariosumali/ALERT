import { useEffect, useCallback, useRef, useState } from 'react'
import { useVideo } from '../contexts/VideoContext'
import type { DetectedEvent } from '../types/events'
import { formatTimestamp, getTimelineColor, getEventColor } from '../types/events'

interface VideoPlayerProps {
  videoUrl: string | null
  events: DetectedEvent[]
  onJumpToNextEvent: () => void
  onJumpToPrevEvent: () => void
}

const SPEEDS = [0.5, 1.0, 1.25, 1.5, 2.0]

export default function VideoPlayer({ videoUrl, events, onJumpToNextEvent, onJumpToPrevEvent }: VideoPlayerProps) {
  const { setVideoElement, currentTime, duration, isPlaying, togglePlay, seekTo, skipForward, skipBackward, setPlaybackRate } = useVideo()
  const [speed, setSpeed] = useState(1.0)
  const [showSpeedMenu, setShowSpeedMenu] = useState(false)
  const timelineRef = useRef<HTMLDivElement>(null)
  const [hoverTime, setHoverTime] = useState<number | null>(null)
  const [hoverX, setHoverX] = useState(0)
  const speedMenuRef = useRef<HTMLDivElement>(null)

  const videoRefCallback = useCallback((node: HTMLVideoElement | null) => {
    setVideoElement(node)
  }, [setVideoElement])

  const currentEvent = events.find(
    (ev) => currentTime >= ev.timestamp && currentTime <= ev.endTime
  )

  const handleKeyboard = useCallback((e: KeyboardEvent) => {
    const target = e.target as HTMLElement
    if (target.tagName === 'INPUT' || target.tagName === 'TEXTAREA' || target.isContentEditable) return

    switch (e.key.toLowerCase()) {
      case 'k':
      case ' ':
        e.preventDefault()
        togglePlay()
        break
      case 'j':
        e.preventDefault()
        skipBackward(5)
        break
      case 'l':
        e.preventDefault()
        skipForward(5)
        break
      case 'e':
        e.preventDefault()
        onJumpToNextEvent()
        break
      case 'q':
        e.preventDefault()
        onJumpToPrevEvent()
        break
    }
  }, [togglePlay, skipForward, skipBackward, onJumpToNextEvent, onJumpToPrevEvent])

  useEffect(() => {
    window.addEventListener('keydown', handleKeyboard)
    return () => window.removeEventListener('keydown', handleKeyboard)
  }, [handleKeyboard])

  const handleSpeedChange = useCallback((s: number) => {
    setSpeed(s)
    setPlaybackRate(s)
    setShowSpeedMenu(false)
  }, [setPlaybackRate])

  useEffect(() => {
    if (!showSpeedMenu) return
    const handler = (e: MouseEvent) => {
      if (speedMenuRef.current && !speedMenuRef.current.contains(e.target as Node)) setShowSpeedMenu(false)
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [showSpeedMenu])

  const handleTimelineClick = useCallback((e: React.MouseEvent) => {
    if (!timelineRef.current || duration <= 0) return
    const rect = timelineRef.current.getBoundingClientRect()
    const ratio = Math.max(0, Math.min(1, (e.clientX - rect.left) / rect.width))
    seekTo(ratio * duration)
  }, [duration, seekTo])

  const handleTimelineHover = useCallback((e: React.MouseEvent) => {
    if (!timelineRef.current || duration <= 0) return
    const rect = timelineRef.current.getBoundingClientRect()
    const x = e.clientX - rect.left
    const ratio = Math.max(0, Math.min(1, x / rect.width))
    setHoverX(x)
    setHoverTime(ratio * duration)
  }, [duration])

  if (!videoUrl) return null

  const hasDuration = duration > 0
  const playheadPct = hasDuration ? (currentTime / duration) * 100 : 0

  return (
    <div className="flex flex-col h-full gap-1.5">
      {/* Video */}
      <div className="flex-1 min-h-0 relative group panel-elevated overflow-hidden" style={{ background: '#000' }}>
        <video
          ref={videoRefCallback}
          src={videoUrl}
          className="w-full h-full object-contain"
          onClick={togglePlay}
        />

        {currentEvent && (
          <div className="absolute top-3 left-3 animate-fade-in pointer-events-none">
            <div className="inline-flex items-center gap-1.5 rounded-lg px-2.5 py-1.5" style={{ background: 'rgba(0,0,0,0.7)', backdropFilter: 'blur(8px)' }}>
              {currentEvent.type.map((t) => {
                const c = getEventColor(t)
                return <span key={t} className={`event-badge ${c.bg} ${c.text}`}>{t}</span>
              })}
              <span className="text-[11px] font-mono tabular-nums ml-1" style={{ color: 'rgba(255,255,255,0.6)' }}>
                {formatTimestamp(currentTime)}
              </span>
            </div>
          </div>
        )}

        {!isPlaying && videoUrl && (
          <div className="absolute bottom-3 left-3 pointer-events-none">
            <span className="text-[10px] uppercase tracking-widest font-medium" style={{ color: 'rgba(255,255,255,0.25)' }}>Paused</span>
          </div>
        )}

        <div className="absolute bottom-3 right-3 opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none">
          <div className="flex gap-1 text-[9px] font-mono" style={{ color: 'rgba(255,255,255,0.4)' }}>
            <kbd className="px-1.5 py-0.5 rounded" style={{ background: 'rgba(0,0,0,0.5)' }}>Q</kbd>
            <kbd className="px-1.5 py-0.5 rounded" style={{ background: 'rgba(0,0,0,0.5)' }}>J</kbd>
            <kbd className="px-1.5 py-0.5 rounded" style={{ background: 'rgba(0,0,0,0.5)' }}>K</kbd>
            <kbd className="px-1.5 py-0.5 rounded" style={{ background: 'rgba(0,0,0,0.5)' }}>L</kbd>
            <kbd className="px-1.5 py-0.5 rounded" style={{ background: 'rgba(0,0,0,0.5)' }}>E</kbd>
          </div>
        </div>
      </div>

      {/* Mini timeline + controls */}
      <div className="flex-shrink-0 panel px-3 py-2" style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
        {/* Scrubber bar with event markers */}
        <div
          ref={timelineRef}
          className="relative rounded cursor-pointer"
          style={{ height: '20px', background: 'hsl(var(--surface-3))' }}
          onClick={handleTimelineClick}
          onMouseMove={handleTimelineHover}
          onMouseLeave={() => setHoverTime(null)}
        >
          {hasDuration && events.map((ev) => {
            const left = (ev.timestamp / duration) * 100
            const width = Math.max(((ev.endTime - ev.timestamp) / duration) * 100, 0.5)
            return (
              <div
                key={ev.id}
                className="absolute top-0 bottom-0 rounded-sm"
                style={{
                  left: `${left}%`,
                  width: `${width}%`,
                  backgroundColor: getTimelineColor(ev.type[0] || ''),
                  opacity: 0.6,
                }}
              />
            )
          })}

          {hasDuration && (
            <div className="timeline-playhead pointer-events-none" style={{ left: `${playheadPct}%` }} />
          )}

          {hoverTime !== null && (
            <div
              className="absolute -translate-x-1/2 px-2 py-0.5 rounded text-[10px] font-mono pointer-events-none z-30"
              style={{ left: `${hoverX}px`, top: '-24px', background: 'hsl(var(--surface-1))', color: 'hsl(var(--text))' }}
            >
              {formatTimestamp(hoverTime)}
            </div>
          )}
        </div>

        {/* Controls row */}
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-1">
            <button onClick={onJumpToPrevEvent} className="btn-ghost p-1 h-6 w-6" title="Previous event (Q)">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 16.811c0 .864-.933 1.405-1.683.977l-7.108-4.062a1.125 1.125 0 010-1.953l7.108-4.062A1.125 1.125 0 0121 8.688v8.123zM11.25 16.811c0 .864-.933 1.405-1.683.977l-7.108-4.062a1.125 1.125 0 010-1.953l7.108-4.062a1.125 1.125 0 011.683.977v8.123z" />
              </svg>
            </button>
            <button onClick={() => skipBackward(5)} className="btn-ghost p-1 h-6 w-6" title="Back 5s (J)">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9 15L3 9m0 0l6-6M3 9h12a6 6 0 010 12h-3" />
              </svg>
            </button>
            <button onClick={togglePlay} className="btn-ghost p-1 h-7 w-7" title={isPlaying ? 'Pause (K)' : 'Play (K)'}>
              {isPlaying ? (
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M6 4h4v16H6V4zm8 0h4v16h-4V4z" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 24 24">
                  <path d="M8 5v14l11-7z" />
                </svg>
              )}
            </button>
            <button onClick={() => skipForward(5)} className="btn-ghost p-1 h-6 w-6" title="Forward 5s (L)">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M15 15l6-6m0 0l-6-6m6 6H9a6 6 0 000 12h3" />
              </svg>
            </button>
            <button onClick={onJumpToNextEvent} className="btn-ghost p-1 h-6 w-6" title="Next event (E)">
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M3 8.688c0-.864.933-1.405 1.683-.977l7.108 4.062a1.125 1.125 0 010 1.953l-7.108 4.062A1.125 1.125 0 013 16.811V8.688zM12.75 8.688c0-.864.933-1.405 1.683-.977l7.108 4.062a1.125 1.125 0 010 1.953l-7.108 4.062a1.125 1.125 0 01-1.683-.977V8.688z" />
              </svg>
            </button>
          </div>

          <div className="flex items-center gap-2">
            <span className="text-[11px] font-mono tabular-nums" style={{ color: 'hsl(var(--muted))' }}>
              {hasDuration ? `${formatTimestamp(currentTime)} / ${formatTimestamp(duration)}` : '—'}
            </span>

            <div className="relative" ref={speedMenuRef}>
              <button
                onClick={() => setShowSpeedMenu((v) => !v)}
                className="btn-ghost text-[11px] px-1.5 py-0.5 h-6 font-mono tabular-nums"
              >
                {speed}x
              </button>
              {showSpeedMenu && (
                <div className="absolute bottom-full mb-1 right-0 panel-elevated py-1 min-w-[64px] z-40 animate-fade-in">
                  {SPEEDS.map((s) => (
                    <button
                      key={s}
                      onClick={() => handleSpeedChange(s)}
                      className="w-full text-left px-3 py-1 text-[11px] font-mono tabular-nums transition-colors"
                      style={{
                        color: s === speed ? 'hsl(var(--primary))' : 'hsl(var(--muted))',
                        fontWeight: s === speed ? 600 : 400,
                        background: 'transparent',
                      }}
                      onMouseEnter={(e) => (e.currentTarget.style.background = 'hsl(var(--surface-3))')}
                      onMouseLeave={(e) => (e.currentTarget.style.background = 'transparent')}
                    >
                      {s}x
                    </button>
                  ))}
                </div>
              )}
            </div>

            <button className="btn-ghost text-[11px] px-2 py-0.5 h-6" title="Create clip (coming soon)">
              <svg className="w-3 h-3 mr-1" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="m7.848 8.25 1.536.887M7.848 8.25a3 3 0 1 1-5.196-3 3 3 0 0 1 5.196 3Zm1.536.887a2.165 2.165 0 0 1 1.083 1.839c.005.351.054.695.14 1.024M9.384 9.137l2.077 1.199M7.848 15.75l1.536-.887m-1.536.887a3 3 0 1 1-5.196 3 3 3 0 0 1 5.196-3Zm1.536-.887a2.165 2.165 0 0 0 1.083-1.838c.005-.352.054-.695.14-1.025m-1.223 2.863 2.077-1.199m0-3.328a4.323 4.323 0 0 1 2.068-1.379l5.325-1.628a4.5 4.5 0 0 1 2.48-.044l.803.215-7.794 4.5m-2.882-1.664A4.331 4.331 0 0 0 10.607 12m3.736 0 7.794 4.5-.802.215a4.5 4.5 0 0 1-2.48-.043l-5.326-1.629a4.324 4.324 0 0 1-2.068-1.379M14.343 12l-2.882 1.664" />
              </svg>
              Clip
            </button>
          </div>
        </div>
      </div>
    </div>
  )
}
