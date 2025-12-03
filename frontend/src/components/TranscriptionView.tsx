import { useEffect, useRef, useState } from 'react'
import { getTranscription, TranscriptionSegment } from '../utils/api'
import type { TranscriptionStatusPayload, TranscriptionStatusState } from '../types/transcription'

interface TranscriptionViewProps {
  fileId: string | null
  onStatusChange?: (payload: TranscriptionStatusPayload) => void
}

const statusStyles: Record<TranscriptionStatusState, { label: string; className: string }> = {
  idle: { label: 'Idle', className: 'bg-gray-200 text-gray-700' },
  processing: { label: 'Processing', className: 'bg-blue-100 text-blue-700' },
  ready: { label: 'Ready', className: 'bg-green-100 text-green-700' },
  error: { label: 'Error', className: 'bg-red-100 text-red-700' },
  empty: { label: 'No Speech', className: 'bg-amber-100 text-amber-700' },
}

export default function TranscriptionView({ fileId, onStatusChange }: TranscriptionViewProps) {
  const [segments, setSegments] = useState<TranscriptionSegment[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasTranscription, setHasTranscription] = useState(false)
  const [status, setStatus] = useState<TranscriptionStatusState>('idle')
  const [lastUpdated, setLastUpdated] = useState<Date | null>(null)
  const pollerRef = useRef<number | null>(null)
  const lastStatusRef = useRef<TranscriptionStatusState>('idle')

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const updateStatus = (next: TranscriptionStatusState, detail?: string) => {
    const shouldNotify = lastStatusRef.current !== next || Boolean(detail)
    lastStatusRef.current = next
    setStatus(next)
    if (shouldNotify && onStatusChange) {
      onStatusChange({ state: next, detail })
    }
  }

  const clearPoller = () => {
    if (pollerRef.current) {
      clearInterval(pollerRef.current)
      pollerRef.current = null
    }
  }

  const loadTranscription = async (suppressLoading = false) => {
    if (!fileId) return

    if (!suppressLoading) {
      setLoading(true)
    }
    setError(null)
    try {
      const data = await getTranscription(fileId)
      setSegments(data.segments || [])
      setHasTranscription(data.has_transcription)
      setLastUpdated(new Date())

      if (data.segments && data.segments.length > 0) {
        updateStatus('ready')
        clearPoller()
      } else if (data.has_transcription) {
        updateStatus('empty')
      } else {
        updateStatus('processing')
      }
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to load transcription'
      setError(message)
      updateStatus('error', message)
    } finally {
      if (!suppressLoading) {
        setLoading(false)
      }
    }
  }

  useEffect(() => {
    if (!fileId) {
      setSegments([])
      setHasTranscription(false)
      setError(null)
      setLastUpdated(null)
      clearPoller()
      updateStatus('idle')
      return
    }

    setSegments([])
    setHasTranscription(false)
    setError(null)
    setLastUpdated(null)
    updateStatus('processing', 'Waiting for the transcription worker to respond.')
    loadTranscription()
    clearPoller()
    pollerRef.current = window.setInterval(() => {
      loadTranscription(true)
    }, 3000)

    return () => {
      clearPoller()
    }
  }, [fileId])

  const handleSegmentClick = (startTime: number) => {
    const event = new CustomEvent('seekTo', { detail: startTime })
    window.dispatchEvent(event)
  }

  const statusMeta = statusStyles[status]
  const lastUpdatedLabel = lastUpdated ? lastUpdated.toLocaleTimeString() : null

  if (!fileId) {
    return (
      <div className="rounded-lg bg-gray-50 p-6 text-center text-gray-500">
        Upload a file to see transcription
      </div>
    )
  }

  return (
    <div className="rounded-lg bg-white p-6 shadow-md">
      <div className="mb-4 flex flex-col gap-3 sm:flex-row sm:items-center sm:justify-between">
        <div>
          <div className="flex items-center gap-2">
            <span className={`rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-wide ${statusMeta.className}`}>
              {statusMeta.label}
            </span>
            {loading && (
              <span className="inline-flex h-3 w-3 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"></span>
            )}
            {lastUpdatedLabel && (
              <span className="text-xs text-gray-500">Updated {lastUpdatedLabel}</span>
            )}
          </div>
          {status === 'processing' && (
            <p className="mt-1 text-sm text-gray-500">
              We are polling every few seconds and will update this view automatically.
            </p>
          )}
          {status === 'error' && error && (
            <p className="mt-1 text-sm text-red-600">{error}</p>
          )}
          {status === 'empty' && (
            <p className="mt-1 text-sm text-gray-500">
              No speech was detected in the processed audio. You can retry if you believe this is incorrect.
            </p>
          )}
        </div>
        <div className="flex gap-2">
          <button
            onClick={() => loadTranscription()}
            className="rounded-lg bg-gray-200 px-3 py-1 text-sm text-gray-700 transition hover:bg-gray-300"
          >
            Refresh now
          </button>
          {status === 'ready' && segments.length > 0 && (
            <span className="self-center text-xs text-gray-500">{segments.length} segments</span>
          )}
        </div>
      </div>

      {status === 'processing' && segments.length === 0 && !error && (
        <div className="flex flex-col items-center justify-center rounded-lg bg-gray-50 py-8 text-center text-gray-600">
          <span className="mb-3 inline-block h-10 w-10 animate-spin rounded-full border-2 border-blue-500 border-t-transparent"></span>
          <p className="font-medium">Transcription in progress...</p>
          <p className="mt-1 text-sm text-gray-500">This may take a few minutes for longer files.</p>
        </div>
      )}

      {status === 'error' && (!segments.length || !hasTranscription) && (
        <div className="rounded-lg bg-red-50 p-4 text-sm text-red-700">
          Unable to load a transcript right now. Please try again or inspect the backend worker logs.
        </div>
      )}

      {status === 'ready' && segments.length === 0 && (
        <div className="rounded-lg bg-amber-50 p-4 text-sm text-amber-700">
          The transcription completed but no text was returned.
        </div>
      )}

      {segments.length > 0 && (
        <div className="max-h-96 space-y-2 overflow-y-auto">
          {segments.map((segment, idx) => (
            <button
              type="button"
              key={`${segment.start}-${segment.end}-${idx}`}
              onClick={() => handleSegmentClick(segment.start)}
              className="w-full rounded-lg border border-transparent bg-gray-50 p-3 text-left transition hover:border-blue-200 hover:bg-blue-50"
            >
              <div className="mb-1 flex items-center justify-between">
                <span className="text-sm font-mono font-semibold text-blue-600">
                  {formatTime(segment.start)} - {formatTime(segment.end)}
                </span>
              </div>
              <p className="text-gray-800">{segment.text}</p>
            </button>
          ))}
        </div>
      )}

      {status !== 'ready' && segments.length === 0 && status !== 'processing' && status !== 'error' && (
        <div className="rounded-lg bg-gray-50 p-4 text-center text-gray-500">
          No transcription available yet. Click "Transcribe" to generate one.
        </div>
      )}
    </div>
  )
}

