import { useState, useEffect, useRef } from 'react'
import { Moment } from '../App'

interface MomentDropdownProps {
  moments: Moment[]
  onMomentSelect: (moment: Moment) => void
  onRefresh: () => void
  fileId?: string | null
}

export default function MomentDropdown({
  moments,
  onMomentSelect,
  onRefresh,
  fileId,
}: MomentDropdownProps) {
  const [selectedEventType, setSelectedEventType] = useState<string>('all')
  const [filteredMoments, setFilteredMoments] = useState<Moment[]>(moments)
  const [isProcessing, setIsProcessing] = useState(false)
  const [hasCompleted, setHasCompleted] = useState(false)
  const [lastMomentCount, setLastMomentCount] = useState(0)
  const [lastFileId, setLastFileId] = useState<string | null | undefined>(fileId)
  const [loudSoundCount, setLoudSoundCount] = useState(0)
  const processingTimeoutRef = useRef<number | null>(null)

  // Reset processing state when file changes
  useEffect(() => {
    if (fileId !== lastFileId) {
      setIsProcessing(false)
      setHasCompleted(false)
      setLastMomentCount(0)
      setLastFileId(fileId)
      if (processingTimeoutRef.current) {
        clearTimeout(processingTimeoutRef.current)
        processingTimeoutRef.current = null
      }
    }
  }, [fileId, lastFileId])

  // Get unique event types - sorted for better UX
  // Handle various data formats and ensure we get all event types
  const eventTypes = Array.from(
    new Set(
      moments.flatMap((m) => {
        const types = m.event_types
        if (!types) return []
        if (Array.isArray(types)) return types
        if (typeof types === 'string') {
          try {
            const parsed = JSON.parse(types)
            return Array.isArray(parsed) ? parsed : []
          } catch {
            return []
          }
        }
        return []
      })
    )
  ).sort()
  
  // Count loud sound moments
  const loudSoundMoments = moments.filter((m) => {
    const types = m.event_types
    if (!types) return false
    let typeArray: string[] = []
    if (Array.isArray(types)) {
      typeArray = types
    } else if (typeof types === 'string') {
      try {
        const parsed = JSON.parse(types)
        typeArray = Array.isArray(parsed) ? parsed : []
      } catch {
        typeArray = []
      }
    }
    return typeArray.includes('LoudSound')
  })
  
  // Debug logging
  useEffect(() => {
    console.log('MomentDropdown render:', {
      momentsCount: moments.length,
      eventTypesCount: eventTypes.length,
      eventTypes: eventTypes,
      sampleMoment: moments[0] ? {
        moment_id: moments[0].moment_id,
        event_types: moments[0].event_types,
        event_types_type: typeof moments[0].event_types,
        is_array: Array.isArray(moments[0].event_types)
      } : null
    })
  }, [moments, eventTypes])

  useEffect(() => {
    if (selectedEventType === 'all') {
      setFilteredMoments(moments)
    } else {
      setFilteredMoments(
        moments.filter((m) => m.event_types.includes(selectedEventType))
      )
    }
    
    // Track processing state
    const hadMoments = lastMomentCount > 0
    const hasMoments = moments.length > 0
    
    // If we have moments now but didn't before, processing is complete
    if (hasMoments && !hadMoments) {
      setIsProcessing(false)
      setHasCompleted(true)
      if (processingTimeoutRef.current) {
        clearTimeout(processingTimeoutRef.current)
        processingTimeoutRef.current = null
      }
    }
    // If we still have no moments and haven't completed, we're processing
    else if (!hasMoments && !hadMoments && !hasCompleted && fileId) {
      // Start processing state if we have a file but no moments yet
      if (!isProcessing) {
        setIsProcessing(true)
      }
      // Set a timeout to mark as complete if no moments appear after 90 seconds
      if (processingTimeoutRef.current === null) {
        processingTimeoutRef.current = window.setTimeout(() => {
          setIsProcessing(false)
          setHasCompleted(true)
          processingTimeoutRef.current = null
        }, 90000) // 90 seconds - give more time for processing
      }
    }
    // If moments count increased, we're done processing
    else if (hasMoments && moments.length > lastMomentCount) {
      setIsProcessing(false)
      setHasCompleted(true)
      if (processingTimeoutRef.current) {
        clearTimeout(processingTimeoutRef.current)
        processingTimeoutRef.current = null
      }
    }
    
    setLastMomentCount(moments.length)
    setLoudSoundCount(loudSoundMoments.length)
    
    // Cleanup timeout on unmount
    return () => {
      if (processingTimeoutRef.current) {
        clearTimeout(processingTimeoutRef.current)
      }
    }
  }, [selectedEventType, moments, lastMomentCount, isProcessing, hasCompleted, fileId, loudSoundMoments.length])

  const formatTime = (seconds: number) => {
    const mins = Math.floor(seconds / 60)
    const secs = Math.floor(seconds % 60)
    return `${mins}:${secs.toString().padStart(2, '0')}`
  }

  return (
    <div className="space-y-4">
      <div className="flex items-center gap-2">
        <label htmlFor="event-filter" className="text-sm font-medium text-gray-700">
          Filter by Event Type:
        </label>
        <select
          id="event-filter"
          value={selectedEventType}
          onChange={(e) => setSelectedEventType(e.target.value)}
          className="flex-1 px-3 py-2 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500"
        >
          <option value="all">All Events {moments.length > 0 && `(${eventTypes.length} types)`}</option>
          {eventTypes.includes('LoudSound') && (
            <option value="LoudSound">
              🔊 Loud Sounds {loudSoundCount > 0 && `(${loudSoundCount})`}
            </option>
          )}
          {eventTypes.length > 0 ? (
            eventTypes.filter(type => type !== 'LoudSound').map((type) => (
              <option key={type} value={type}>
                {type}
              </option>
            ))
          ) : moments.length > 0 ? (
            <option value="all" disabled>Loading event types...</option>
          ) : (
            <option value="all" disabled>No event types available</option>
          )}
        </select>
        <button
          onClick={onRefresh}
          className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
        >
          Refresh
        </button>
      </div>

      {/* Processing indicator */}
      {isProcessing && moments.length === 0 && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
          <div className="flex items-center gap-2">
            <div className="flex space-x-1">
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
              <div className="w-2 h-2 bg-blue-500 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
            </div>
            <p className="text-sm text-blue-700 font-medium">Processing events...</p>
          </div>
          <p className="text-xs text-blue-600 mt-1 ml-6">
            Analyzing audio (including loud sound detection), video, and transcript features. This may take a minute.
          </p>
        </div>
      )}

      {/* Completion indicator */}
      {hasCompleted && moments.length === 0 && !isProcessing && (
        <div className="bg-amber-50 border border-amber-200 rounded-lg p-3 mb-4">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-amber-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
            </svg>
            <p className="text-sm text-amber-700 font-medium">No events found</p>
          </div>
          <p className="text-xs text-amber-600 mt-1 ml-7">
            Event detection completed. No moments of interest were detected in this video.
          </p>
        </div>
      )}

      {/* Loud sound indicator */}
      {hasCompleted && moments.length > 0 && loudSoundCount === 0 && !isProcessing && (
        <div className="bg-blue-50 border border-blue-200 rounded-lg p-3 mb-4">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
            </svg>
            <p className="text-sm text-blue-700 font-medium">No loud sounds detected</p>
          </div>
          <p className="text-xs text-blue-600 mt-1 ml-7">
            Audio analysis completed. No loud sounds (gunshots, yelling, sudden noises) were detected in this video.
          </p>
        </div>
      )}

      {/* Loud sounds found indicator */}
      {hasCompleted && loudSoundCount > 0 && !isProcessing && (
        <div className="bg-orange-50 border border-orange-200 rounded-lg p-3 mb-4">
          <div className="flex items-center gap-2">
            <svg className="w-5 h-5 text-orange-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.536 8.464a5 5 0 010 7.072m2.828-9.9a9 9 0 010 12.728M5.586 15H4a1 1 0 01-1-1v-4a1 1 0 011-1h1.586l4.707-4.707C10.923 3.663 12 4.109 12 5v14c0 .891-1.077 1.337-1.707.707L5.586 15z" />
            </svg>
            <p className="text-sm text-orange-700 font-medium">🔊 {loudSoundCount} loud sound{loudSoundCount !== 1 ? 's' : ''} detected</p>
          </div>
          <p className="text-xs text-orange-600 mt-1 ml-7">
            {loudSoundCount === 1 
              ? 'A loud sound event was detected. Use the "Loud Sounds" filter to view it.'
              : `${loudSoundCount} loud sound events were detected. Use the "Loud Sounds" filter to view them.`}
          </p>
        </div>
      )}

      {/* Success indicator */}
      {hasCompleted && moments.length > 0 && (
        <div className="bg-green-50 border border-green-200 rounded-lg p-2 mb-4">
          <p className="text-xs text-green-700 text-center">
            ✓ Event detection complete - {moments.length} moment{moments.length !== 1 ? 's' : ''} found
          </p>
        </div>
      )}

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {filteredMoments.length === 0 ? (
          <div className="text-sm text-gray-500 text-center py-4">
            {moments.length === 0 ? (
              <div>
                {isProcessing ? (
                  <p>Detecting moments of interest... Please wait.</p>
                ) : (
                  <p>No moments detected yet. Processing may take a few moments...</p>
                )}
              </div>
            ) : (
              <div>
                <p className="font-medium mb-1">No moments found</p>
                <p className="text-xs">
                  {selectedEventType === 'all'
                    ? 'No moments have been detected for this video.'
                    : `No moments match the "${selectedEventType}" filter.`}
                </p>
              </div>
            )}
          </div>
        ) : (
          filteredMoments.map((moment) => (
            <div
              key={moment.moment_id}
              className="p-4 bg-gray-50 rounded-lg border border-gray-200 hover:bg-gray-100 cursor-pointer transition-colors"
              onClick={() => onMomentSelect(moment)}
            >
              <div className="flex justify-between items-start mb-2">
                <div>
                  <div className="font-semibold text-gray-800">
                    {formatTime(moment.start_time)} - {formatTime(moment.end_time)}
                  </div>
                  <div className="text-sm text-gray-600 mt-1">
                    {moment.event_types.map((type, idx) => (
                      <span
                        key={idx}
                        className="inline-block px-2 py-1 bg-blue-100 text-blue-800 rounded mr-1 mb-1"
                      >
                        {type}
                      </span>
                    ))}
                  </div>
                </div>
                <div className="text-right">
                  <div className="text-sm font-semibold text-gray-700">
                    {(moment.interest_score * 100).toFixed(0)}%
                  </div>
                  <div className="text-xs text-gray-500">interest</div>
                </div>
              </div>
              {moment.description && (
                <div className="text-sm text-gray-600 mt-2">
                  {moment.description}
                </div>
              )}
            </div>
          ))
        )}
      </div>

      <div className="text-sm text-gray-500 text-center pt-2 border-t">
        {moments.length > 0 ? (
          <p>
            Showing {filteredMoments.length} of {moments.length} moment{filteredMoments.length !== 1 ? 's' : ''}
            {selectedEventType !== 'all' && ` (filtered by: ${selectedEventType})`}
          </p>
        ) : isProcessing ? (
          <p className="text-blue-600">Event detection in progress...</p>
        ) : hasCompleted ? (
          <p className="text-amber-600">Event detection complete - No events found</p>
        ) : null}
      </div>
    </div>
  )
}

