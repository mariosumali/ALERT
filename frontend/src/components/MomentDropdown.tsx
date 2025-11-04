import { useState, useEffect } from 'react'
import { Moment } from '../App'

interface MomentDropdownProps {
  moments: Moment[]
  onMomentSelect: (moment: Moment) => void
  onRefresh: () => void
}

export default function MomentDropdown({
  moments,
  onMomentSelect,
  onRefresh,
}: MomentDropdownProps) {
  const [selectedEventType, setSelectedEventType] = useState<string>('all')
  const [filteredMoments, setFilteredMoments] = useState<Moment[]>(moments)

  // Get unique event types
  const eventTypes = Array.from(
    new Set(moments.flatMap((m) => m.event_types))
  )

  useEffect(() => {
    if (selectedEventType === 'all') {
      setFilteredMoments(moments)
    } else {
      setFilteredMoments(
        moments.filter((m) => m.event_types.includes(selectedEventType))
      )
    }
  }, [selectedEventType, moments])

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
          <option value="all">All Events</option>
          {eventTypes.map((type) => (
            <option key={type} value={type}>
              {type}
            </option>
          ))}
        </select>
        <button
          onClick={onRefresh}
          className="px-4 py-2 bg-gray-200 text-gray-700 rounded-lg hover:bg-gray-300 transition-colors"
        >
          Refresh
        </button>
      </div>

      <div className="space-y-2 max-h-96 overflow-y-auto">
        {filteredMoments.length === 0 ? (
          <p className="text-sm text-gray-500 text-center py-4">
            {moments.length === 0
              ? 'No moments detected yet. Processing may take a few moments...'
              : 'No moments match the selected filter.'}
          </p>
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

      <div className="text-sm text-gray-500 text-center">
        Showing {filteredMoments.length} of {moments.length} moments
      </div>
    </div>
  )
}

