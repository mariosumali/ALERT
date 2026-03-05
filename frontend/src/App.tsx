import { useEffect, useRef, useState, useCallback, useMemo } from 'react'
import { Panel, Group, Separator } from 'react-resizable-panels'
import { useVideo } from './contexts/VideoContext'
import CaseHeader from './components/CaseHeader'
import ProcessingPipeline from './components/ProcessingPipeline'
import VideoPlayer from './components/VideoPlayer'
import EventPanel from './components/EventPanel'
import SegmentPanel from './components/SegmentPanel'
import TranscriptPanel from './components/TranscriptPanel'
import AIAssistant from './components/AIAssistant'
import type { DetectedEvent, CaseMetadata, ProcessingStatus } from './types/events'
import { eventFromMoment } from './types/events'

function useMediaQuery(query: string) {
  const [matches, setMatches] = useState(() =>
    typeof window !== 'undefined' ? window.matchMedia(query).matches : false
  )
  useEffect(() => {
    const mql = window.matchMedia(query)
    const handler = (e: MediaQueryListEvent) => setMatches(e.matches)
    mql.addEventListener('change', handler)
    return () => mql.removeEventListener('change', handler)
  }, [query])
  return matches
}

interface RawMoment {
  moment_id: string
  file_id: string
  start_time: number
  end_time: number
  event_types: string[]
  interest_score: number
  description: string
}

function App() {
  const { currentTime, seekTo } = useVideo()
  const [fileId, setFileId] = useState<string | null>(null)
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const [events, setEvents] = useState<DetectedEvent[]>([])
  const [caseInfo, setCaseInfo] = useState<CaseMetadata | null>(null)
  const [processingStatus, setProcessingStatus] = useState<ProcessingStatus | null>(null)
  const [selectedEventId, setSelectedEventId] = useState<string | null>(null)

  const pollRef = useRef<number | null>(null)

  const stopPolling = useCallback(() => {
    if (pollRef.current) {
      clearInterval(pollRef.current)
      pollRef.current = null
    }
  }, [])

  const fetchMoments = useCallback(async (fid: string) => {
    try {
      const res = await fetch(`/api/moments?file_id=${fid}`)
      if (!res.ok) return
      const data = await res.json()
      const moments: RawMoment[] = data.moments || []
      setEvents(moments.map(eventFromMoment))
    } catch { /* noop */ }
  }, [])

  const fetchMetadata = useCallback(async (fid: string): Promise<ProcessingStatus | null> => {
    try {
      const res = await fetch(`/api/files/${fid}/metadata`)
      if (!res.ok) return null
      const data = await res.json()
      const status: ProcessingStatus = data.status || null
      setProcessingStatus(status)
      setCaseInfo({
        fileId: fid,
        filename: data.original_filename || 'Unknown file',
        deviceId: data.ocr_metadata?.device_id ?? null,
        deviceModel: data.ocr_metadata?.device_model ?? null,
        badgeNumber: data.ocr_metadata?.badge_number ?? null,
        officerId: data.ocr_metadata?.officer_id ?? null,
        recordedAt: data.ocr_metadata?.timestamp ?? null,
        duration: data.duration ?? undefined,
        status,
      })
      return status
    } catch {
      return null
    }
  }, [])

  const handleUploadSuccess = useCallback((newFileId: string, fileUrl: string) => {
    stopPolling()
    setFileId(newFileId)
    setVideoUrl(fileUrl)
    setEvents([])
    setSelectedEventId(null)
    setCaseInfo({
      fileId: newFileId,
      filename: 'Processing...',
      status: 'pending',
    })
    setProcessingStatus('pending')
  }, [stopPolling])

  useEffect(() => {
    if (!fileId) {
      setEvents([])
      setCaseInfo(null)
      setProcessingStatus(null)
      return
    }

    stopPolling()
    fetchMoments(fileId)
    fetchMetadata(fileId)

    pollRef.current = window.setInterval(async () => {
      await fetchMoments(fileId)
      const status = await fetchMetadata(fileId)
      if (status === 'completed' || status === 'failed') {
        stopPolling()
      }
    }, 3000)

    return stopPolling
  }, [fileId, stopPolling, fetchMoments, fetchMetadata])

  const sortedEvents = useMemo(
    () => [...events].sort((a, b) => a.timestamp - b.timestamp),
    [events]
  )

  const selectedEvent = useMemo(
    () => sortedEvents.find((e) => e.id === selectedEventId) ?? null,
    [sortedEvents, selectedEventId]
  )

  const handleSelectEvent = useCallback((ev: DetectedEvent) => {
    setSelectedEventId(ev.id)
    seekTo(ev.timestamp)
  }, [seekTo])

  const handleJumpToNextEvent = useCallback(() => {
    const next = sortedEvents.find((ev) => ev.timestamp > currentTime + 0.5)
    if (next) {
      setSelectedEventId(next.id)
      seekTo(next.timestamp)
    }
  }, [sortedEvents, currentTime, seekTo])

  const handleJumpToPrevEvent = useCallback(() => {
    const prev = [...sortedEvents].reverse().find((ev) => ev.timestamp < currentTime - 0.5)
    if (prev) {
      setSelectedEventId(prev.id)
      seekTo(prev.timestamp)
    }
  }, [sortedEvents, currentTime, seekTo])

  const isDesktop = useMediaQuery('(min-width: 1024px)')
  const [mobileTab, setMobileTab] = useState<'video' | 'events' | 'transcript' | 'ai'>('video')
  const [leftTab, setLeftTab] = useState<'events' | 'segments'>('events')

  const isProcessing = processingStatus !== null &&
    processingStatus !== 'completed' &&
    processingStatus !== 'failed'

  if (!fileId) {
    return (
      <div className="h-screen flex flex-col" style={{ background: 'hsl(var(--bg))' }}>
        <CaseHeader caseInfo={null} onUploadSuccess={handleUploadSuccess} />
        <div className="flex-1 flex items-center justify-center">
          <div className="text-center max-w-md px-6">
            <div className="w-16 h-16 rounded-2xl flex items-center justify-center mx-auto mb-5" style={{ background: 'hsl(var(--primary) / 0.1)' }}>
              <svg className="w-8 h-8" style={{ color: 'hsl(var(--primary))' }} fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="m15.75 10.5 4.72-4.72a.75.75 0 0 1 1.28.53v11.38a.75.75 0 0 1-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 0 0 2.25-2.25v-9a2.25 2.25 0 0 0-2.25-2.25h-9A2.25 2.25 0 0 0 2.25 7.5v9a2.25 2.25 0 0 0 2.25 2.25Z" />
              </svg>
            </div>
            <h2 className="text-xl font-semibold mb-2" style={{ color: 'hsl(var(--text))' }}>Upload Body Camera Footage</h2>
            <p className="text-sm leading-relaxed" style={{ color: 'hsl(var(--muted))' }}>
              Drag and drop or click "Upload Footage" to begin automated analysis of audio, video, and transcript data.
            </p>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col overflow-hidden" style={{ background: 'hsl(var(--bg))' }}>
      <CaseHeader caseInfo={caseInfo} onUploadSuccess={handleUploadSuccess} />

      {isProcessing && (
        <div className="px-3 py-1.5 flex-shrink-0">
          <ProcessingPipeline status={processingStatus} eventCount={events.length} />
        </div>
      )}

      {isDesktop ? (
        /* Desktop: resizable layout */
        <div className="flex-1 min-h-0 p-1.5">
          <Group orientation="horizontal" id="alert-h" className="h-full">
            <Panel defaultSize="22%" minSize="16%" maxSize="32%" id="p-events">
              <div className="h-full panel-elevated overflow-hidden flex flex-col">
                <div className="flex flex-shrink-0" style={{ borderBottom: '1px solid hsl(var(--border))' }}>
                  {(['events', 'segments'] as const).map((tab) => (
                    <button
                      key={tab}
                      onClick={() => setLeftTab(tab)}
                      className="flex-1 py-1.5 text-[11px] font-semibold uppercase tracking-wider transition-colors"
                      style={{
                        background: leftTab === tab ? 'hsl(var(--primary) / 0.1)' : 'transparent',
                        color: leftTab === tab ? 'hsl(var(--primary))' : 'hsl(var(--muted-2))',
                      }}
                    >
                      {tab === 'events' ? 'Events' : 'Video Analysis'}
                    </button>
                  ))}
                </div>
                <div className="flex-1 min-h-0 overflow-hidden">
                  {leftTab === 'events' ? (
                    <EventPanel
                      events={sortedEvents}
                      isProcessing={isProcessing}
                      selectedEventId={selectedEventId}
                      onSelectEvent={handleSelectEvent}
                    />
                  ) : (
                    <SegmentPanel fileId={fileId} />
                  )}
                </div>
              </div>
            </Panel>

            <Separator style={{ width: 8, cursor: 'col-resize' }} id="s1" />

            <Panel defaultSize="52%" minSize="30%" id="p-center">
              <Group orientation="vertical" id="alert-v" className="h-full">
                <Panel defaultSize="62%" minSize="30%" id="p-video">
                  <div className="h-full flex flex-col gap-1.5 overflow-hidden">
                    <VideoPlayer
                      videoUrl={videoUrl}
                      events={sortedEvents}
                      onJumpToNextEvent={handleJumpToNextEvent}
                      onJumpToPrevEvent={handleJumpToPrevEvent}
                    />
                  </div>
                </Panel>

                <Separator style={{ height: 8, cursor: 'row-resize' }} id="s2" />

                <Panel defaultSize="38%" minSize="12%" id="p-transcript">
                  <div className="h-full panel-elevated overflow-hidden">
                    <TranscriptPanel fileId={fileId} selectedEvent={selectedEvent} />
                  </div>
                </Panel>
              </Group>
            </Panel>

            <Separator style={{ width: 8, cursor: 'col-resize' }} id="s3" />

            <Panel defaultSize="26%" minSize="18%" maxSize="36%" id="p-ai">
              <div className="h-full panel-elevated overflow-hidden">
                <AIAssistant
                  fileId={fileId}
                  caseInfo={caseInfo}
                  selectedEvent={selectedEvent}
                />
              </div>
            </Panel>
          </Group>
        </div>
      ) : (
        /* Mobile/Tablet: tabbed layout */
        <div className="flex-1 min-h-0 flex flex-col overflow-hidden">
          <div className="flex-1 min-h-0 overflow-hidden p-1.5">
            {mobileTab === 'video' && (
              <div className="h-full flex flex-col gap-1.5 overflow-auto">
                <VideoPlayer
                  videoUrl={videoUrl}
                  events={sortedEvents}
                  onJumpToNextEvent={handleJumpToNextEvent}
                  onJumpToPrevEvent={handleJumpToPrevEvent}
                />
              </div>
            )}
            {mobileTab === 'events' && (
              <div className="h-full panel-elevated overflow-hidden">
                <EventPanel
                  events={sortedEvents}
                  isProcessing={isProcessing}
                  selectedEventId={selectedEventId}
                  onSelectEvent={(ev) => { handleSelectEvent(ev); setMobileTab('video') }}
                />
              </div>
            )}
            {mobileTab === 'transcript' && (
              <div className="h-full panel-elevated overflow-hidden">
                <TranscriptPanel fileId={fileId} selectedEvent={selectedEvent} />
              </div>
            )}
            {mobileTab === 'ai' && (
              <div className="h-full panel-elevated overflow-hidden">
                <AIAssistant fileId={fileId} caseInfo={caseInfo} selectedEvent={selectedEvent} />
              </div>
            )}
          </div>

          {/* Bottom tab bar */}
          <div className="flex-shrink-0 flex" style={{ background: 'hsl(var(--surface-1))', borderTop: '1px solid hsl(var(--border))' }}>
            {([
              { id: 'video' as const, label: 'Video', icon: 'M15.75 10.5l4.72-4.72a.75.75 0 011.28.53v11.38a.75.75 0 01-1.28.53l-4.72-4.72M4.5 18.75h9a2.25 2.25 0 002.25-2.25v-9a2.25 2.25 0 00-2.25-2.25h-9A2.25 2.25 0 002.25 7.5v9a2.25 2.25 0 002.25 2.25z' },
              { id: 'events' as const, label: 'Events', icon: 'M3.75 12h16.5m-16.5 3.75h16.5M3.75 19.5h16.5M5.625 4.5h12.75a1.875 1.875 0 010 3.75H5.625a1.875 1.875 0 010-3.75z' },
              { id: 'transcript' as const, label: 'Transcript', icon: 'M19.5 14.25v-2.625a3.375 3.375 0 00-3.375-3.375h-1.5A1.125 1.125 0 0113.5 7.125v-1.5a3.375 3.375 0 00-3.375-3.375H8.25m0 12.75h7.5m-7.5 3H12M10.5 2.25H5.625c-.621 0-1.125.504-1.125 1.125v17.25c0 .621.504 1.125 1.125 1.125h12.75c.621 0 1.125-.504 1.125-1.125V11.25a9 9 0 00-9-9z' },
              { id: 'ai' as const, label: 'AI', icon: 'M9.813 15.904L9 18.75l-.813-2.846a4.5 4.5 0 00-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 003.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 003.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 00-3.09 3.09z' },
            ]).map((tab) => (
              <button
                key={tab.id}
                onClick={() => setMobileTab(tab.id)}
                className="flex-1 flex flex-col items-center gap-0.5 py-2 transition-colors"
                style={{ color: mobileTab === tab.id ? 'hsl(var(--primary))' : 'hsl(var(--muted-2))' }}
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d={tab.icon} />
                </svg>
                <span className="text-[10px] font-medium">{tab.label}</span>
              </button>
            ))}
          </div>
        </div>
      )}
    </div>
  )
}

export default App
