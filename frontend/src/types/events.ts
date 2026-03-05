export type EventType =
  | 'LoudSound'
  | 'Gunshot'
  | 'Profanity'
  | 'Silence'
  | 'SuddenChange'
  | 'FrequencyAnomaly'
  | 'Distortion'
  | string

export interface DetectedEvent {
  id: string
  fileId: string
  type: EventType[]
  timestamp: number
  endTime: number
  duration: number
  description: string
  confidence: number
}

export interface TranscriptSegment {
  start: number
  end: number
  text: string
}

export interface CaseMetadata {
  fileId: string
  filename: string
  deviceId?: string | null
  deviceModel?: string | null
  badgeNumber?: string | null
  officerId?: string | null
  recordedAt?: string | null
  duration?: number
  status: ProcessingStatus | null
}

export type ProcessingStatus =
  | 'pending'
  | 'processing_transcription'
  | 'processing_audio'
  | 'processing_video_analysis'
  | 'completed'
  | 'failed'

export type ProcessingStage = {
  id: string
  label: string
  status: 'pending' | 'active' | 'done' | 'failed'
}

export const EVENT_COLORS: Record<string, { bg: string; text: string; dot: string; darkBg: string; darkText: string }> = {
  Gunshot:                  { bg: 'bg-red-50',      text: 'text-red-700',     dot: 'bg-red-600',     darkBg: 'dark:bg-red-950/40',      darkText: 'dark:text-red-400' },
  LoudSound:                { bg: 'bg-orange-50',   text: 'text-orange-700',  dot: 'bg-orange-600',  darkBg: 'dark:bg-orange-950/40',   darkText: 'dark:text-orange-400' },
  Profanity:                { bg: 'bg-violet-50',   text: 'text-violet-700',  dot: 'bg-violet-600',  darkBg: 'dark:bg-violet-950/40',   darkText: 'dark:text-violet-400' },
  Silence:                  { bg: 'bg-gray-50',     text: 'text-gray-500',    dot: 'bg-gray-400',    darkBg: 'dark:bg-gray-800/40',     darkText: 'dark:text-gray-500' },
  SuddenChange:             { bg: 'bg-amber-50',    text: 'text-amber-700',   dot: 'bg-amber-600',   darkBg: 'dark:bg-amber-950/40',    darkText: 'dark:text-amber-400' },
  FrequencyAnomaly:         { bg: 'bg-pink-50',     text: 'text-pink-700',    dot: 'bg-pink-600',    darkBg: 'dark:bg-pink-950/40',     darkText: 'dark:text-pink-400' },
  Distortion:               { bg: 'bg-amber-50',    text: 'text-amber-700',   dot: 'bg-amber-500',   darkBg: 'dark:bg-amber-950/40',    darkText: 'dark:text-amber-400' },
  UseOfForce:               { bg: 'bg-rose-50',     text: 'text-rose-700',    dot: 'bg-rose-600',    darkBg: 'dark:bg-rose-950/40',     darkText: 'dark:text-rose-400' },
  PotentialExcessiveForce:  { bg: 'bg-red-100',     text: 'text-red-800',     dot: 'bg-red-700',     darkBg: 'dark:bg-red-950/60',      darkText: 'dark:text-red-300' },
  CameraObfuscation:        { bg: 'bg-slate-50',    text: 'text-slate-600',   dot: 'bg-slate-500',   darkBg: 'dark:bg-slate-800/40',    darkText: 'dark:text-slate-400' },
}

export const DEFAULT_EVENT_COLOR = {
  bg: 'bg-indigo-50', text: 'text-indigo-700', dot: 'bg-indigo-500',
  darkBg: 'dark:bg-indigo-950/40', darkText: 'dark:text-indigo-400',
}

export const EVENT_TIMELINE_COLORS: Record<string, string> = {
  Gunshot:                  '#DC2626',
  LoudSound:                '#EA580C',
  Profanity:                '#7C3AED',
  Silence:                  '#6B7280',
  SuddenChange:             '#D97706',
  FrequencyAnomaly:         '#DB2777',
  Distortion:               '#D97706',
  UseOfForce:               '#E11D48',
  PotentialExcessiveForce:  '#991B1B',
  CameraObfuscation:        '#475569',
}

export const DEFAULT_TIMELINE_COLOR = '#6366F1'

export function getEventColor(type: string) {
  return EVENT_COLORS[type] ?? DEFAULT_EVENT_COLOR
}

export function getTimelineColor(type: string) {
  return EVENT_TIMELINE_COLORS[type] ?? DEFAULT_TIMELINE_COLOR
}

export function formatTimestamp(seconds: number): string {
  const h = Math.floor(seconds / 3600)
  const m = Math.floor((seconds % 3600) / 60)
  const s = Math.floor(seconds % 60)
  if (h > 0) return `${h}:${m.toString().padStart(2, '0')}:${s.toString().padStart(2, '0')}`
  return `${m}:${s.toString().padStart(2, '0')}`
}

export function eventFromMoment(moment: {
  moment_id: string
  file_id: string
  start_time: number
  end_time: number
  event_types: string[]
  interest_score: number
  description: string
}): DetectedEvent {
  return {
    id: moment.moment_id,
    fileId: moment.file_id,
    type: moment.event_types,
    timestamp: moment.start_time,
    endTime: moment.end_time,
    duration: moment.end_time - moment.start_time,
    description: moment.description,
    confidence: moment.interest_score,
  }
}
