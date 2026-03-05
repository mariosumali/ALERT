import { useState, useMemo, useEffect } from 'react'
import { useVideo } from '../contexts/VideoContext'
import { getSegments, type VideoSegment } from '../utils/api'
import { formatTimestamp } from '../types/events'

interface SegmentPanelProps {
  fileId: string | null
}

const SCENE_ICONS: Record<string, string> = {
  indoor: 'M2.25 12l8.954-8.955a1.126 1.126 0 011.591 0L21.75 12M4.5 9.75v10.125c0 .621.504 1.125 1.125 1.125H9.75v-4.875c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125V21h4.125c.621 0 1.125-.504 1.125-1.125V9.75M8.25 21h8.25',
  outdoor: 'M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z',
  vehicle: 'M8.25 18.75a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h6m-9 0H3.375a1.125 1.125 0 01-1.125-1.125V14.25m17.25 4.5a1.5 1.5 0 01-3 0m3 0a1.5 1.5 0 00-3 0m3 0h1.125c.621 0 1.125-.504 1.125-1.125v-1.5c0-1.036-.84-1.875-1.875-1.875H15M2.25 14.25V5.625c0-.621.504-1.125 1.125-1.125h11.25c.621 0 1.125.504 1.125 1.125v5.25',
  unknown: 'M9.879 7.519c1.171-1.025 3.071-1.025 4.242 0 1.172 1.025 1.172 2.687 0 3.712-.203.179-.43.326-.67.442-.745.361-1.45.999-1.45 1.827v.75M21 12a9 9 0 11-18 0 9 9 0 0118 0zm-9 5.25h.008v.008H12v-.008z',
}

export default function SegmentPanel({ fileId }: SegmentPanelProps) {
  const { seekTo, currentTime } = useVideo()
  const [segments, setSegments] = useState<VideoSegment[]>([])
  const [loading, setLoading] = useState(false)
  const [expandedId, setExpandedId] = useState<number | null>(null)

  useEffect(() => {
    if (!fileId) {
      setSegments([])
      return
    }
    setLoading(true)
    getSegments(fileId)
      .then((res) => setSegments(res.segments))
      .catch(() => setSegments([]))
      .finally(() => setLoading(false))
  }, [fileId])

  const activeIdx = useMemo(() => {
    return segments.find(
      (s) => currentTime >= s.start_sec && currentTime < s.end_sec
    )?.segment_idx ?? null
  }, [segments, currentTime])

  if (!fileId) return null

  if (loading) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center px-4">
        <div className="w-6 h-6 border-2 border-primary border-t-transparent rounded-full animate-spin mb-3" />
        <p className="text-sm font-medium text-muted">Loading segments...</p>
      </div>
    )
  }

  if (segments.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center py-16 text-center px-4">
        <p className="text-sm text-muted-2">No video analysis segments available</p>
        <p className="text-[11px] text-muted-2 mt-1">Enable Gemini analysis to generate segment metadata</p>
      </div>
    )
  }

  return (
    <div className="flex flex-col h-full">
      <div className="px-3 py-3 flex-shrink-0" style={{ borderBottom: '1px solid hsl(var(--border))' }}>
        <div className="flex items-center justify-between">
          <span className="section-label">Video Analysis</span>
          <span className="text-[11px] text-muted-2 tabular-nums">{segments.length} segments</span>
        </div>
      </div>

      <div className="flex-1 overflow-y-auto">
        {segments.map((seg) => {
          const isActive = seg.segment_idx === activeIdx
          const isExpanded = seg.id === expandedId
          const sceneIcon = SCENE_ICONS[seg.scene_type || 'unknown'] || SCENE_ICONS.unknown

          return (
            <div
              key={seg.id}
              className="transition-colors"
              style={{
                background: isActive ? 'hsl(var(--primary) / 0.05)' : 'transparent',
                borderLeft: isActive ? '2px solid hsl(var(--primary))' : '2px solid transparent',
                borderBottom: '1px solid hsl(var(--border) / 0.5)',
              }}
            >
              <button
                onClick={() => seekTo(seg.start_sec)}
                className="w-full text-left px-3 py-2.5"
              >
                <div className="flex items-center justify-between mb-1.5">
                  <div className="flex items-center gap-1.5">
                    <svg className="w-3.5 h-3.5 text-muted-2" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d={sceneIcon} />
                    </svg>
                    <span className="text-[11px] font-mono text-muted-2 tabular-nums">
                      {formatTimestamp(seg.start_sec)} – {formatTimestamp(seg.end_sec)}
                    </span>
                  </div>
                  <button
                    onClick={(e) => { e.stopPropagation(); setExpandedId(isExpanded ? null : seg.id) }}
                    className="text-muted-2 hover:text-muted transition-colors"
                  >
                    <svg className={`w-3 h-3 transition-transform ${isExpanded ? 'rotate-180' : ''}`} fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="m19.5 8.25-7.5 7.5-7.5-7.5" />
                    </svg>
                  </button>
                </div>

                {/* Tags row */}
                <div className="flex gap-1 flex-wrap mb-1">
                  <span className="event-badge text-[10px] bg-blue-50 text-blue-600 dark:bg-blue-950/40 dark:text-blue-400">
                    {seg.scene_type || 'unknown'}
                  </span>
                  <span className="event-badge text-[10px] bg-slate-50 text-slate-600 dark:bg-slate-800/40 dark:text-slate-400">
                    {seg.lighting || 'unknown'}
                  </span>
                  {seg.officers_count > 0 && (
                    <span className="event-badge text-[10px] bg-cyan-50 text-cyan-600 dark:bg-cyan-950/40 dark:text-cyan-400">
                      {seg.officers_count} officer{seg.officers_count !== 1 ? 's' : ''}
                    </span>
                  )}
                  {seg.civilians_count > 0 && (
                    <span className="event-badge text-[10px] bg-emerald-50 text-emerald-600 dark:bg-emerald-950/40 dark:text-emerald-400">
                      {seg.civilians_count} civilian{seg.civilians_count !== 1 ? 's' : ''}
                    </span>
                  )}
                  {seg.use_of_force_present && (
                    <span className="event-badge text-[10px] bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400 font-semibold">
                      Use of Force
                    </span>
                  )}
                  {seg.potential_excessive_force && (
                    <span className="event-badge text-[10px] bg-red-100 text-red-800 dark:bg-red-950/60 dark:text-red-300 font-bold">
                      Excessive Force
                    </span>
                  )}
                  {seg.camera_obfuscation_present && (
                    <span className="event-badge text-[10px] bg-gray-50 text-gray-500 dark:bg-gray-800/40 dark:text-gray-500">
                      Camera Issue
                    </span>
                  )}
                </div>

                {seg.key_moments_summary && (
                  <p className={`text-[12px] text-muted mt-0.5 leading-snug ${isExpanded ? '' : 'line-clamp-2'}`}>
                    {seg.key_moments_summary}
                  </p>
                )}
              </button>

              {isExpanded && (
                <div className="px-3 pb-3 space-y-2">
                  <div className="grid grid-cols-2 gap-1.5 text-[11px]">
                    <div className="px-2 py-1.5 rounded" style={{ background: 'hsl(var(--surface-3))' }}>
                      <span className="text-muted-2 block">Time of Day</span>
                      <span className="text-txt font-medium">{seg.time_of_day || 'Unknown'}</span>
                    </div>
                    <div className="px-2 py-1.5 rounded" style={{ background: 'hsl(var(--surface-3))' }}>
                      <span className="text-muted-2 block">Weather</span>
                      <span className="text-txt font-medium">{seg.weather || 'Unknown'}</span>
                    </div>
                    <div className="px-2 py-1.5 rounded" style={{ background: 'hsl(var(--surface-3))' }}>
                      <span className="text-muted-2 block">Camera</span>
                      <span className="text-txt font-medium">{seg.camera_motion || 'Unknown'}</span>
                    </div>
                    <div className="px-2 py-1.5 rounded" style={{ background: 'hsl(var(--surface-3))' }}>
                      <span className="text-muted-2 block">Scene</span>
                      <span className="text-txt font-medium">{seg.scene_type || 'Unknown'}</span>
                    </div>
                  </div>

                  {seg.use_of_force_present && seg.use_of_force_types.length > 0 && (
                    <div className="px-2 py-1.5 rounded" style={{ background: 'hsl(var(--danger) / 0.06)' }}>
                      <span className="text-[10px] text-muted-2 block mb-1">Force Types</span>
                      <div className="flex flex-wrap gap-1">
                        {seg.use_of_force_types.map((t) => (
                          <span key={t} className="event-badge text-[10px] bg-rose-50 text-rose-700 dark:bg-rose-950/40 dark:text-rose-400">
                            {t.replace(/_/g, ' ')}
                          </span>
                        ))}
                      </div>
                    </div>
                  )}

                  {seg.summary && (
                    <div className="px-2 py-1.5 rounded text-[11px] text-muted leading-snug" style={{ background: 'hsl(var(--surface-3))' }}>
                      {seg.summary.split('\n').slice(0, 8).map((line, i) => (
                        <p key={i} className="mb-0.5">{line}</p>
                      ))}
                    </div>
                  )}
                </div>
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
