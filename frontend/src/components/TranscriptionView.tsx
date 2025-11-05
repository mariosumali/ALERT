import { useState, useEffect } from 'react'
import { getTranscription, TranscriptionSegment } from '../utils/api'

interface TranscriptionViewProps {
  fileId: string | null
}

export default function TranscriptionView({ fileId }: TranscriptionViewProps) {
  const [segments, setSegments] = useState<TranscriptionSegment[]>([])
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [hasTranscription, setHasTranscription] = useState(false)
  const [processing, setProcessing] = useState(false)

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const loadTranscription = async () => {
    if (!fileId) return

    setLoading(true)
    setError(null)
    try {
      const data = await getTranscription(fileId)
      setSegments(data.segments || [])
      setHasTranscription(data.has_transcription)
      
      // If we have segments, we're done processing
      if (data.segments && data.segments.length > 0) {
        setProcessing(false)
      } else if (!data.has_transcription) {
        // If no transcription yet, it might be processing
        setProcessing(true)
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load transcription')
      setProcessing(false)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (fileId) {
      loadTranscription()
      // Poll for transcription updates
      const interval = setInterval(() => {
        loadTranscription()
      }, 3000)
      return () => clearInterval(interval)
    }
  }, [fileId])

  const handleSegmentClick = (startTime: number) => {
    const event = new CustomEvent('seekTo', { detail: startTime })
    window.dispatchEvent(event)
  }

  if (!fileId) {
    return (
      <div className="bg-gray-100 rounded-lg p-6 text-center text-gray-500">
        Upload a file to see transcription
      </div>
    )
  }

  if (loading && segments.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="text-center text-gray-500">Loading transcription...</div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="text-red-600">Error: {error}</div>
      </div>
    )
  }

  if (processing && segments.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="text-center">
          <div className="inline-block animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600 mb-2"></div>
          <div className="text-gray-600">Transcription in progress... This may take a few minutes.</div>
          <div className="text-sm text-gray-500 mt-2">Note: Whisper transcription may fail on some systems. If it doesn't complete, check the backend logs.</div>
        </div>
      </div>
    )
  }

  if (!hasTranscription || segments.length === 0) {
    return (
      <div className="bg-white rounded-lg shadow-md p-6">
        <div className="text-center text-gray-500">
          {error ? (
            <div>
              <div className="text-red-600 mb-2">Error: {error}</div>
              <div className="text-sm">Transcription may have failed. Check backend logs for details.</div>
            </div>
          ) : (
            <div>No transcription available yet. Click "Transcribe" to generate one.</div>
          )}
        </div>
      </div>
    )
  }

  return (
    <div className="bg-white rounded-lg shadow-md p-6">
      <div className="flex justify-between items-center mb-4">
        <h3 className="text-lg font-semibold">Transcription with Timestamps</h3>
        <button
          onClick={loadTranscription}
          className="px-3 py-1 text-sm bg-gray-200 text-gray-700 rounded hover:bg-gray-300"
        >
          Refresh
        </button>
      </div>
      <div className="space-y-2 max-h-96 overflow-y-auto">
        {segments.map((segment, idx) => (
          <div
            key={idx}
            onClick={() => handleSegmentClick(segment.start)}
            className="p-3 bg-gray-50 rounded-lg hover:bg-gray-100 cursor-pointer transition-colors border-l-4 border-blue-500"
          >
            <div className="flex items-start justify-between mb-1">
              <span className="text-sm font-mono text-blue-600 font-semibold">
                {formatTime(segment.start)} - {formatTime(segment.end)}
              </span>
            </div>
            <p className="text-gray-800">{segment.text}</p>
          </div>
        ))}
      </div>
    </div>
  )
}

