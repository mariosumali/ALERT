import { useEffect, useRef, useState } from 'react'
import UploadForm from './components/UploadForm'
import VideoPlayer from './components/VideoPlayer'
import MomentDropdown from './components/MomentDropdown'
import TranscriptionView from './components/TranscriptionView'
import ChatBot from './components/ChatBot'
import { transcribeFile, downloadTranscript } from './utils/api'
import StatusBanner, { StatusBannerVariant } from './components/StatusBanner'
import type { TranscriptionStatusPayload, TranscriptionStatusState } from './types/transcription'

export interface Moment {
  moment_id: string
  file_id: string
  start_time: number
  end_time: number
  event_types: string[]
  interest_score: number
  description: string
}

type BannerState = {
  variant: StatusBannerVariant
  title: string
  message?: string
}

function App() {
  const [fileId, setFileId] = useState<string | null>(null)
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const [moments, setMoments] = useState<Moment[]>([])
  const [transcribing, setTranscribing] = useState(false)
  const [downloading, setDownloading] = useState(false)
  const [statusBanner, setStatusBanner] = useState<BannerState | null>(null)
  const momentsPollRef = useRef<number | null>(null)
  const lastTranscriptionState = useRef<TranscriptionStatusState | null>(null)

  const handleUploadSuccess = (newFileId: string, fileUrl: string) => {
    if (momentsPollRef.current) {
      clearInterval(momentsPollRef.current)
      momentsPollRef.current = null
    }

    setFileId(newFileId)
    setVideoUrl(fileUrl)
    setMoments([])

    setStatusBanner({
      variant: 'success',
      title: 'Upload complete',
      message: 'We are processing your media. Detected moments and transcripts will populate automatically.',
    })

    // The useEffect hook will handle polling when fileId changes
    // No need to set up polling here as it's handled in useEffect
  }

  const handleTranscribe = async () => {
    if (!fileId) return

    setTranscribing(true)
    setStatusBanner({
      variant: 'info',
      title: 'Submitting transcription request',
      message: 'Your file is being queued for transcription. The results will update automatically.',
    })
    try {
      const result = await transcribeFile(fileId)
      console.log('Transcription started:', result)
      setStatusBanner({
        variant: 'success',
        title: 'Transcription job queued',
        message: 'We will refresh the transcript view as soon as the processing finishes.',
      })
    } catch (error) {
      console.error('Failed to start transcription:', error)
      const errorMsg = error instanceof Error ? error.message : 'Unknown error'
      setStatusBanner({
        variant: 'error',
        title: 'Unable to start transcription',
        message: errorMsg,
      })
    } finally {
      setTranscribing(false)
    }
  }

  const handleDownloadTranscript = async () => {
    if (!fileId) return

    setDownloading(true)
    try {
      await downloadTranscript(fileId)
      setStatusBanner({
        variant: 'success',
        title: 'Download started',
        message: 'The comprehensive transcript file is being downloaded.',
      })
    } catch (error) {
      console.error('Failed to download transcript:', error)
      const errorMsg = error instanceof Error ? error.message : 'Unknown error'
      setStatusBanner({
        variant: 'error',
        title: 'Unable to download transcript',
        message: errorMsg || 'Transcript file may not be available yet. Please wait for processing to complete.',
      })
    } finally {
      setDownloading(false)
    }
  }

  const fetchMoments = async (id: string) => {
    try {
      const response = await fetch(`/api/moments?file_id=${id}`)
      if (!response.ok) {
        console.error('Failed to fetch moments:', response.status, response.statusText)
        return
      }
      const data = await response.json()
      const moments = data.moments || []
      console.log(`Fetched ${moments.length} moments for file ${id}`)
      if (moments.length > 0) {
        // Log event types for debugging
        const eventTypes = Array.from(new Set(moments.flatMap((m: Moment) => m.event_types || [])))
        console.log('Event types found:', eventTypes)
      }
      setMoments(moments)

      // If we got moments, stop polling
      if (moments.length > 0 && momentsPollRef.current) {
        clearInterval(momentsPollRef.current)
        momentsPollRef.current = null
        console.log('Stopped polling - moments found')
      }
    } catch (error) {
      console.error('Failed to fetch moments:', error)
    }
  }

  const handleTranscriptionStatusChange = (payload: TranscriptionStatusPayload) => {
    if (lastTranscriptionState.current === payload.state && !payload.detail) {
      return
    }
    lastTranscriptionState.current = payload.state

    switch (payload.state) {
      case 'processing':
        setStatusBanner({
          variant: 'info',
          title: 'Transcription in progress',
          message:
            payload.detail || 'Hang tight while we generate the transcript. This can take a couple of minutes for longer clips.',
        })
        break
      case 'ready':
        setStatusBanner({
          variant: 'success',
          title: 'Transcription ready',
          message: 'Click a segment below to jump directly to that moment in the video player.',
        })
        break
      case 'error':
        setStatusBanner({
          variant: 'error',
          title: 'Transcription unavailable',
          message: payload.detail || 'We could not generate a transcript. Please retry or check the backend logs.',
        })
        break
      case 'empty':
        setStatusBanner({
          variant: 'info',
          title: 'No dialogue detected',
          message: 'We processed the media but did not detect any speech to transcribe.',
        })
        break
      case 'idle':
        setStatusBanner(null)
        break
    }
  }

  // Fetch moments when fileId changes
  useEffect(() => {
    if (!fileId) {
      setMoments([])
      return
    }

    // Clear any existing polling
    if (momentsPollRef.current) {
      clearInterval(momentsPollRef.current)
      momentsPollRef.current = null
    }

    // Initial fetch
    fetchMoments(fileId)

    // Set up continuous polling until moments are found
    let pollCount = 0
    const maxPolls = 60 // 2 minutes
    const pollInterval = window.setInterval(async () => {
      pollCount++
      await fetchMoments(fileId)
      if (pollCount >= maxPolls) {
        clearInterval(pollInterval)
        momentsPollRef.current = null
        console.log('Stopped polling for moments after maximum attempts')
      }
    }, 2000)
    momentsPollRef.current = pollInterval

    return () => {
      if (momentsPollRef.current) {
        clearInterval(momentsPollRef.current)
        momentsPollRef.current = null
      }
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [fileId])

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold text-gray-800 mb-8 text-center">
          Multimedia Event Parsing Platform
        </h1>

        {statusBanner && (
          <div className="mx-auto mb-6 max-w-3xl">
            <StatusBanner
              variant={statusBanner.variant}
              title={statusBanner.title}
              message={statusBanner.message}
              onClose={() => setStatusBanner(null)}
            />
          </div>
        )}

        <div className="grid grid-cols-1 gap-8 lg:grid-cols-2">
          {/* Left Column: Upload and Controls */}
          <div className="space-y-6">
            <div className="rounded-lg bg-white p-6 shadow-md">
              <h2 className="mb-4 text-2xl font-semibold">Upload Media</h2>
              <UploadForm onUploadSuccess={handleUploadSuccess} />
            </div>

            {fileId && (
              <>
                <div className="rounded-lg bg-white p-6 shadow-md">
                  <div className="mb-4 flex items-center justify-between">
                    <h2 className="text-2xl font-semibold">Transcription</h2>
                    <div className="flex gap-2">
                      <button
                        onClick={handleDownloadTranscript}
                        disabled={downloading || !fileId}
                        className="rounded-lg bg-blue-600 px-4 py-2 text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-400"
                      >
                        {downloading ? 'Downloading...' : 'Download Transcript'}
                      </button>
                      <button
                        onClick={handleTranscribe}
                        disabled={transcribing}
                        className="rounded-lg bg-green-600 px-4 py-2 text-white transition-colors hover:bg-green-700 disabled:cursor-not-allowed disabled:bg-gray-400"
                      >
                        {transcribing ? 'Transcribing...' : 'Transcribe'}
                      </button>
                    </div>
                  </div>
                  <TranscriptionView fileId={fileId} onStatusChange={handleTranscriptionStatusChange} />
                </div>

                <div className="rounded-lg bg-white p-6 shadow-md">
                  <h2 className="mb-4 text-2xl font-semibold">Detected Moments</h2>
                  <MomentDropdown
                    moments={moments}
                    onMomentSelect={(moment) => {
                      const event = new CustomEvent('seekTo', { detail: moment.start_time })
                      window.dispatchEvent(event)
                    }}
                    onRefresh={async () => {
                      if (fileId) {
                        await fetchMoments(fileId)
                      }
                    }}
                    fileId={fileId}
                  />
                </div>
              </>
            )}
          </div>

          {/* Right Column: Video Player */}
          <div className="space-y-6">
            <div className="rounded-lg bg-white p-6 shadow-md">
              <h2 className="mb-4 text-2xl font-semibold">Video Player</h2>
              <VideoPlayer videoUrl={videoUrl} moments={moments} />
            </div>

            {fileId && <ChatBot fileId={fileId} />}
          </div>
        </div>

        <footer className="mt-12 text-center text-sm text-gray-500">
          <p>
            Created by Mario Sumali (msumali@stanford.edu) and Shane Mion (smion@stanford.edu) in collaboration with Big
            Local News
          </p>
        </footer>
      </div>
    </div>
  )
}

export default App
