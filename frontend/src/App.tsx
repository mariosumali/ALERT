import { useState } from 'react'
import UploadForm from './components/UploadForm'
import VideoPlayer from './components/VideoPlayer'
import MomentDropdown from './components/MomentDropdown'

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

  const handleUploadSuccess = (newFileId: string, fileUrl: string) => {
    setFileId(newFileId)
    setVideoUrl(fileUrl)
    // Poll for moments after upload
    setTimeout(() => {
      fetchMoments(newFileId)
    }, 2000)
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

