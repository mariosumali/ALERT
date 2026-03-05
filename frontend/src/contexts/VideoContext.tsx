import { createContext, useContext, useRef, useState, useCallback, useEffect, ReactNode } from 'react'

interface VideoContextType {
  setVideoElement: (el: HTMLVideoElement | null) => void
  currentTime: number
  duration: number
  isPlaying: boolean
  seekTo: (time: number) => void
  play: () => void
  pause: () => void
  togglePlay: () => void
  skipForward: (seconds?: number) => void
  skipBackward: (seconds?: number) => void
  setPlaybackRate: (rate: number) => void
}

const VideoContext = createContext<VideoContextType | null>(null)

export function VideoProvider({ children }: { children: ReactNode }) {
  const elRef = useRef<HTMLVideoElement | null>(null)
  const [videoEl, setVideoEl] = useState<HTMLVideoElement | null>(null)
  const [currentTime, setCurrentTime] = useState(0)
  const [duration, setDuration] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)

  const setVideoElement = useCallback((el: HTMLVideoElement | null) => {
    elRef.current = el
    setVideoEl(el)
  }, [])

  const seekTo = useCallback((time: number) => {
    const v = elRef.current
    if (v) {
      v.currentTime = time
      v.play().catch(() => {})
    }
  }, [])

  const play = useCallback(() => {
    elRef.current?.play().catch(() => {})
  }, [])

  const pause = useCallback(() => {
    elRef.current?.pause()
  }, [])

  const togglePlay = useCallback(() => {
    const v = elRef.current
    if (!v) return
    if (v.paused) v.play().catch(() => {})
    else v.pause()
  }, [])

  const skipForward = useCallback((seconds = 5) => {
    const v = elRef.current
    if (v) v.currentTime = Math.min(v.currentTime + seconds, v.duration || Infinity)
  }, [])

  const skipBackward = useCallback((seconds = 5) => {
    const v = elRef.current
    if (v) v.currentTime = Math.max(v.currentTime - seconds, 0)
  }, [])

  const setPlaybackRate = useCallback((rate: number) => {
    const v = elRef.current
    if (v) v.playbackRate = rate
  }, [])

  useEffect(() => {
    const video = videoEl
    if (!video) {
      setCurrentTime(0)
      setDuration(0)
      setIsPlaying(false)
      return
    }

    const onTimeUpdate = () => setCurrentTime(video.currentTime)
    const onDurationChange = () => setDuration(video.duration || 0)
    const onPlay = () => setIsPlaying(true)
    const onPause = () => setIsPlaying(false)
    const onLoadedMetadata = () => {
      setDuration(video.duration || 0)
      setCurrentTime(video.currentTime)
    }

    video.addEventListener('timeupdate', onTimeUpdate)
    video.addEventListener('durationchange', onDurationChange)
    video.addEventListener('play', onPlay)
    video.addEventListener('pause', onPause)
    video.addEventListener('loadedmetadata', onLoadedMetadata)
    video.addEventListener('ended', onPause)

    if (video.readyState >= 1) {
      setDuration(video.duration || 0)
      setCurrentTime(video.currentTime)
      setIsPlaying(!video.paused)
    }

    return () => {
      video.removeEventListener('timeupdate', onTimeUpdate)
      video.removeEventListener('durationchange', onDurationChange)
      video.removeEventListener('play', onPlay)
      video.removeEventListener('pause', onPause)
      video.removeEventListener('loadedmetadata', onLoadedMetadata)
      video.removeEventListener('ended', onPause)
    }
  }, [videoEl])

  return (
    <VideoContext.Provider
      value={{
        setVideoElement,
        currentTime,
        duration,
        isPlaying,
        seekTo,
        play,
        pause,
        togglePlay,
        skipForward,
        skipBackward,
        setPlaybackRate,
      }}
    >
      {children}
    </VideoContext.Provider>
  )
}

export function useVideo() {
  const ctx = useContext(VideoContext)
  if (!ctx) throw new Error('useVideo must be used within VideoProvider')
  return ctx
}
