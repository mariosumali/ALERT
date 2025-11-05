import { useState } from 'react'
import UploadForm from './components/UploadForm'
import VideoPlayer from './components/VideoPlayer'
import MomentDropdown from './components/MomentDropdown'
import TranscriptionView from './components/TranscriptionView'
import { transcribeFile } from './utils/api'

export interface Moment {
  moment_id: string
  file_id: string
  start_time: number
  end_time: number
  event_types: string[]
  interest_score: number
  description: string
}

function App() {
  const [fileId, setFileId] = useState<string | null>(null)
  const [videoUrl, setVideoUrl] = useState<string | null>(null)
  const [moments, setMoments] = useState<Moment[]>([])
  const [transcribing, setTranscribing] = useState(false)

  const handleUploadSuccess = (newFileId: string, fileUrl: string) => {
    setFileId(newFileId)
    setVideoUrl(fileUrl)
    // Poll for moments after upload (poll multiple times until moments appear)
    let pollCount = 0
    const maxPolls = 10
    const pollInterval = setInterval(() => {
      pollCount++
      fetchMoments(newFileId)
      if (pollCount >= maxPolls) {
        clearInterval(pollInterval)
      }
    }, 2000)
  }

  const handleTranscribe = async () => {
    if (!fileId) return

    setTranscribing(true)
    try {
      const result = await transcribeFile(fileId)
      console.log('Transcription started:', result)
      // Show success message
      alert('Transcription started! This may take a few minutes. The transcription will appear automatically when ready.')
    } catch (error) {
      console.error('Failed to start transcription:', error)
      const errorMsg = error instanceof Error ? error.message : 'Unknown error'
      alert(`Failed to start transcription: ${errorMsg}`)
    } finally {
      setTranscribing(false)
    }
  }

  const fetchMoments = async (id: string) => {
    try {
      const response = await fetch(`/api/moments?file_id=${id}`)
      const data = await response.json()
      setMoments(data.moments || [])
    } catch (error) {
      console.error('Failed to fetch moments:', error)
    }
  }

  return (
    <div className="min-h-screen bg-gray-100">
      <div className="container mx-auto px-4 py-8">
        <h1 className="text-4xl font-bold text-gray-800 mb-8 text-center">
          Multimedia Event Parsing Platform
        </h1>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Left Column: Upload and Controls */}
          <div className="space-y-6">
            <div className="bg-white rounded-lg shadow-md p-6">
              <h2 className="text-2xl font-semibold mb-4">Upload Media</h2>
              <UploadForm onUploadSuccess={handleUploadSuccess} />
            </div>

            {fileId && (
              <>
                <div className="bg-white rounded-lg shadow-md p-6">
                  <div className="flex justify-between items-center mb-4">
                    <h2 className="text-2xl font-semibold">Transcription</h2>
                    <button
                      onClick={handleTranscribe}
                      disabled={transcribing}
                      className="px-4 py-2 bg-green-600 text-white rounded-lg hover:bg-green-700 disabled:bg-gray-400 disabled:cursor-not-allowed transition-colors"
                    >
                      {transcribing ? 'Transcribing...' : 'Transcribe'}
                    </button>
                  </div>
                  <TranscriptionView fileId={fileId} />
                </div>

                <div className="bg-white rounded-lg shadow-md p-6">
                  <h2 className="text-2xl font-semibold mb-4">Detected Moments</h2>
                  <MomentDropdown
                    moments={moments}
                    onMomentSelect={(moment) => {
                      // Video player will handle seeking
                      const event = new CustomEvent('seekTo', { detail: moment.start_time })
                      window.dispatchEvent(event)
                    }}
                    onRefresh={() => fetchMoments(fileId)}
                  />
                </div>
              </>
            )}
          </div>

          {/* Right Column: Video Player */}
          <div className="bg-white rounded-lg shadow-md p-6">
            <h2 className="text-2xl font-semibold mb-4">Video Player</h2>
            <VideoPlayer
              videoUrl={videoUrl}
              moments={moments}
            />
          </div>
        </div>
      </div>
    </div>
  )
}

export default App

