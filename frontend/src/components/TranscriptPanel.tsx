import { useEffect, useRef, useState, useMemo, useCallback } from 'react'
import { useVideo } from '../contexts/VideoContext'
import { getTranscription, downloadTranscript, type TranscriptionSegment } from '../utils/api'
import { formatTimestamp } from '../types/events'
import type { DetectedEvent } from '../types/events'
import type { TranscriptionStatusState } from '../types/transcription'

interface TranscriptPanelProps {
  fileId: string | null
  selectedEvent?: DetectedEvent | null
}

export default function TranscriptPanel({ fileId, selectedEvent }: TranscriptPanelProps) {
  const { currentTime, seekTo } = useVideo()
  const [segments, setSegments] = useState<TranscriptionSegment[]>([])
  const [status, setStatus] = useState<TranscriptionStatusState>('idle')
  const [downloading, setDownloading] = useState(false)
  const [autoFollow, setAutoFollow] = useState(true)
  const [search, setSearch] = useState('')
  const pollerRef = useRef<number | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)
  const activeRef = useRef<HTMLButtonElement>(null)
  const lastScrollTime = useRef(0)

  const activeIndex = useMemo(() => {
    return segments.findIndex((s) => currentTime >= s.start && currentTime < s.end)
  }, [segments, currentTime])

  const filteredSegments = useMemo(() => {
    if (!search.trim()) return segments.map((s, i) => ({ ...s, _idx: i }))
    const q = search.toLowerCase()
    return segments
      .map((s, i) => ({ ...s, _idx: i }))
      .filter((s) => s.text.toLowerCase().includes(q))
  }, [segments, search])

  useEffect(() => {
    if (!autoFollow || !activeRef.current || !scrollRef.current) return
    const now = Date.now()
    if (now - lastScrollTime.current > 500) {
      lastScrollTime.current = now
      activeRef.current.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
    }
  }, [activeIndex, autoFollow])

  useEffect(() => {
    if (selectedEvent && scrollRef.current && segments.length > 0) {
      const targetIdx = segments.findIndex(
        (s) => s.start >= selectedEvent.timestamp || (s.start <= selectedEvent.timestamp && s.end > selectedEvent.timestamp)
      )
      if (targetIdx >= 0) {
        const el = scrollRef.current.querySelectorAll('[data-seg]')[targetIdx] as HTMLElement
        if (el) el.scrollIntoView({ behavior: 'smooth', block: 'center' })
      }
    }
  }, [selectedEvent, segments])

  const clearPoller = () => {
    if (pollerRef.current) { clearInterval(pollerRef.current); pollerRef.current = null }
  }

  const loadTranscription = useCallback(async (fid: string, suppressUpdate = false) => {
    try {
      const data = await getTranscription(fid)
      setSegments(data.segments || [])
      if (data.segments && data.segments.length > 0) {
        if (!suppressUpdate) setStatus('ready')
        clearPoller()
      } else if (data.has_transcription) {
        setStatus('empty')
      } else {
        setStatus('processing')
      }
    } catch {
      setStatus('error')
    }
  }, [])

  useEffect(() => {
    if (!fileId) {
      setSegments([])
      setStatus('idle')
      clearPoller()
      return
    }
    setSegments([])
    setStatus('processing')
    loadTranscription(fileId)
    clearPoller()
    pollerRef.current = window.setInterval(() => loadTranscription(fileId, true), 3000)
    return () => clearPoller()
  }, [fileId, loadTranscription])

  const handleDownload = async () => {
    if (!fileId) return
    setDownloading(true)
    try { await downloadTranscript(fileId) } catch { /* noop */ }
    finally { setDownloading(false) }
  }

  if (!fileId) {
    return (
      <div className="flex items-center justify-center h-full text-sm text-muted-2">
        Upload footage to see transcript
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      {/* Header */}
      <div className="px-3 py-2 flex items-center justify-between flex-shrink-0 gap-2" style={{ borderBottom: '1px solid hsl(var(--border))' }}>
        <div className="flex items-center gap-2">
          <span className="section-label">Transcript</span>
          {status === 'processing' && (
            <span className="inline-flex h-1.5 w-1.5 animate-pulse rounded-full bg-primary" />
          )}
          {status === 'ready' && segments.length > 0 && (
            <span className="text-[10px] text-muted-2 tabular-nums">{segments.length} segments</span>
          )}
        </div>

        <div className="flex items-center gap-1">
          {segments.length > 0 && (
            <>
              <div className="relative">
                <svg className="absolute left-2 top-1/2 -translate-y-1/2 w-2.5 h-2.5 text-muted-2 pointer-events-none" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="m21 21-5.197-5.197m0 0A7.5 7.5 0 1 0 5.196 5.196a7.5 7.5 0 0 0 10.607 10.607Z" />
                </svg>
                <input
                  type="text"
                  value={search}
                  onChange={(e) => setSearch(e.target.value)}
                  placeholder="Search…"
                  className="input-base pl-6 pr-2 py-1 text-[11px] w-28"
                />
              </div>
              <button
                onClick={() => setAutoFollow((v) => !v)}
                className={`btn-ghost text-[10px] px-1.5 py-0.5 h-6 ${autoFollow ? 'text-primary' : 'text-muted-2'}`}
                title="Auto-follow playback"
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M19.5 13.5 12 21m0 0-7.5-7.5M12 21V3" />
                </svg>
              </button>
              <button
                onClick={handleDownload}
                disabled={downloading}
                className="btn-ghost text-[10px] px-1.5 py-0.5 h-6"
                title="Export transcript"
              >
                <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="M3 16.5v2.25A2.25 2.25 0 005.25 21h13.5A2.25 2.25 0 0021 18.75V16.5M16.5 12L12 16.5m0 0L7.5 12m4.5 4.5V3" />
                </svg>
              </button>
            </>
          )}
        </div>
      </div>

      {/* Content */}
      <div ref={scrollRef} className="flex-1 overflow-y-auto">
        {status === 'processing' && segments.length === 0 && (
          <div className="flex flex-col items-center justify-center py-16 text-center px-4">
            <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mb-3" />
            <p className="text-sm font-medium text-muted">Transcribing audio…</p>
            <p className="text-[11px] text-muted-2 mt-1">This may take a few minutes</p>
          </div>
        )}

        {status === 'error' && (
          <div className="px-4 py-8 text-center">
            <p className="text-sm text-danger">Unable to load transcript</p>
          </div>
        )}

        {status === 'empty' && (
          <div className="px-4 py-8 text-center">
            <p className="text-sm text-muted-2">No speech detected</p>
          </div>
        )}

        {filteredSegments.length > 0 && (
          <div>
            {filteredSegments.map((seg) => {
              const isActive = seg._idx === activeIndex
              const isEventHighlight = selectedEvent &&
                seg.start >= selectedEvent.timestamp - 0.5 &&
                seg.start <= selectedEvent.endTime + 0.5

              return (
                <button
                  key={`${seg.start}-${seg._idx}`}
                  ref={isActive ? activeRef : undefined}
                  data-seg
                  onClick={() => seekTo(seg.start)}
                  className="w-full text-left px-3 py-2 transition-colors"
                  style={{
                    background: isActive
                      ? 'hsl(var(--primary) / 0.08)'
                      : isEventHighlight
                      ? 'hsl(var(--warning) / 0.06)'
                      : 'transparent',
                    borderLeft: isActive ? '2px solid hsl(var(--primary))' : '2px solid transparent',
                    borderBottom: '1px solid hsl(var(--border) / 0.3)',
                  }}
                  onMouseEnter={(e) => { if (!isActive) e.currentTarget.style.background = 'hsl(var(--surface-3) / 0.4)' }}
                  onMouseLeave={(e) => {
                    if (!isActive && !isEventHighlight) e.currentTarget.style.background = 'transparent'
                    else if (isEventHighlight && !isActive) e.currentTarget.style.background = 'hsl(var(--warning) / 0.06)'
                  }}
                >
                  <div className="flex gap-3">
                    <span className={`text-[11px] font-mono flex-shrink-0 pt-0.5 tabular-nums ${
                      isActive ? 'text-primary font-semibold' : 'text-muted-2'
                    }`}>
                      {formatTimestamp(seg.start)}
                    </span>
                    <p className={`text-[15px] leading-relaxed ${
                      isActive ? 'text-txt font-medium' : 'text-muted'
                    }`}>
                      {seg.text}
                    </p>
                  </div>
                </button>
              )
            })}
          </div>
        )}

        {status === 'idle' && segments.length === 0 && (
          <div className="px-4 py-8 text-center">
            <p className="text-sm text-muted-2">Transcript will appear once processing completes</p>
          </div>
        )}
      </div>
    </div>
  )
}
