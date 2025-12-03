import { useEffect, useRef, useState } from 'react'
import { Moment } from '../App'

interface VideoPlayerProps {
  videoUrl: string | null
  moments: Moment[]
}

export default function VideoPlayer({ videoUrl, moments }: VideoPlayerProps) {
  const videoRef = useRef<HTMLVideoElement>(null)
  const [currentTime, setCurrentTime] = useState(0)

  useEffect(() => {
    const handleSeek = (e: CustomEvent) => {
      const time = e.detail as number
      if (videoRef.current) {
        videoRef.current.currentTime = time
        videoRef.current.play()
      }
    }

    window.addEventListener('seekTo', handleSeek as EventListener)
    return () => {
      window.removeEventListener('seekTo', handleSeek as EventListener)
    }
  }, [])

  useEffect(() => {
    const video = videoRef.current
    if (!video) return

    const updateTime = () => setCurrentTime(video.currentTime)
    video.addEventListener('timeupdate', updateTime)

    return () => {
      video.removeEventListener('timeupdate', updateTime)
    }
  }, [videoUrl])

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  const getMomentAtTime = (time: number) => {
    return moments.find(
      (m) => time >= m.start_time && time <= m.end_time
    )
  }

  const currentMoment = getMomentAtTime(currentTime)

  if (!videoUrl) {
    return (
      <div className="bg-gray-100 rounded-lg aspect-video flex items-center justify-center text-gray-500">
        <p>Upload a video to get started</p>
      </div>
    )
  }

  return (
    <div className="space-y-4">
      <div className="relative">
        <video
          ref={videoRef}
          src={videoUrl}
          controls
          className="w-full rounded-lg"
        />
        {/* Moment markers overlay */}
        <div className="absolute bottom-0 left-0 right-0 h-2 bg-gray-800 bg-opacity-50 rounded-b-lg">
          {moments.map((moment) => {
            const duration = videoRef.current?.duration || 0
            if (duration === 0) return null

            const leftPercent = (moment.start_time / duration) * 100
            const widthPercent = ((moment.end_time - moment.start_time) / duration) * 100

            return (
              <div
                key={moment.moment_id}
                className="absolute h-full bg-yellow-400 bg-opacity-70 cursor-pointer hover:bg-opacity-100 transition-opacity"
                style={{
                  left: `${leftPercent}%`,
                  width: `${widthPercent}%`,
                }}
                title={moment.description}
              />
            )
          })}
        </div>
      </div>

      <div className="text-sm text-gray-600">
        Current time: {formatTime(currentTime)}
        {currentMoment && (
          <div className="mt-2 p-2 bg-yellow-50 border border-yellow-200 rounded">
            <strong>Current Event:</strong> {currentMoment.event_types.join(', ')}
            <br />
            <span className="text-xs">{currentMoment.description}</span>
          </div>
        )}
      </div>

      <div className="space-y-2">
        <h3 className="font-semibold text-gray-700">Detected Moments:</h3>
        {moments.length === 0 ? (
          <p className="text-sm text-gray-500">No moments detected yet. Processing...</p>
        ) : (
          <div className="space-y-1 max-h-48 overflow-y-auto">
            {moments.map((moment) => (
              <div
                key={moment.moment_id}
                className="p-2 bg-gray-50 rounded text-xs hover:bg-gray-100 cursor-pointer"
                onClick={() => {
                  if (videoRef.current) {
                    videoRef.current.currentTime = moment.start_time
                    videoRef.current.play()
                  }
                }}
              >
                <div className="flex justify-between">
                  <span className="font-medium">
                    {formatTime(moment.start_time)} - {formatTime(moment.end_time)}
                  </span>
                  <span className="text-blue-600">
                    {moment.interest_score > 0 ? `${(moment.interest_score * 100).toFixed(0)}%` : ''}
                  </span>
                </div>
                <div className="text-gray-600">
                  {moment.event_types.join(', ')}
                </div>
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

