import type { ProcessingStatus } from '../types/events'

interface ProcessingPipelineProps {
  status: ProcessingStatus | null
  eventCount: number
}

interface Stage {
  id: string
  label: string
  state: 'pending' | 'active' | 'done' | 'failed'
}

function deriveStages(status: ProcessingStatus | null, eventCount: number): Stage[] {
  const stages: Stage[] = [
    { id: 'upload', label: 'Upload', state: 'done' },
    { id: 'transcription', label: 'Transcription', state: 'pending' },
    { id: 'audio', label: 'Audio Analysis', state: 'pending' },
    { id: 'events', label: 'Event Detection', state: 'pending' },
    { id: 'video_analysis', label: 'Video Analysis', state: 'pending' },
  ]

  if (!status || status === 'pending') {
    stages[1].state = 'active'
    return stages
  }

  if (status === 'processing_transcription') {
    stages[1].state = 'active'
    return stages
  }

  if (status === 'processing_audio') {
    stages[1].state = 'done'
    stages[2].state = 'active'
    return stages
  }

  if (status === 'processing_video_analysis') {
    stages[1].state = 'done'
    stages[2].state = 'done'
    stages[3].state = 'done'
    stages[4].state = 'active'
    return stages
  }

  if (status === 'completed') {
    stages.forEach((s) => (s.state = 'done'))
    return stages
  }

  if (status === 'failed') {
    const failIdx = stages.findIndex((s) => s.state === 'active' || s.state === 'pending')
    if (failIdx >= 0) stages[failIdx].state = 'failed'
    return stages
  }

  if (eventCount > 0) {
    stages[1].state = 'done'
    stages[2].state = 'done'
    stages[3].state = 'active'
  }

  return stages
}

const stateColors: Record<string, { bg: string; text: string; line: string }> = {
  done:    { bg: 'hsl(var(--success))',    text: '#fff',                   line: 'hsl(var(--success) / 0.4)' },
  active:  { bg: 'hsl(var(--primary))',    text: '#fff',                   line: 'hsl(var(--border))' },
  pending: { bg: 'hsl(var(--surface-3))',  text: 'hsl(var(--muted-2))',    line: 'hsl(var(--border))' },
  failed:  { bg: 'hsl(var(--danger))',     text: '#fff',                   line: 'hsl(var(--border))' },
}

export default function ProcessingPipeline({ status, eventCount }: ProcessingPipelineProps) {
  if (!status || status === 'completed') return null

  const stages = deriveStages(status, eventCount)

  return (
    <div className="panel px-4 py-2.5 animate-slide-up">
      <div className="flex items-center gap-1">
        {stages.map((stage, i) => {
          const c = stateColors[stage.state]
          return (
            <div key={stage.id} className="flex items-center gap-1 flex-1">
              <div className="flex items-center gap-1.5 flex-1">
                <div
                  className={`w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 text-[10px] font-medium ${stage.state === 'active' ? 'animate-pulse' : ''}`}
                  style={{ background: c.bg, color: c.text }}
                >
                  {stage.state === 'done' ? (
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 12.75l6 6 9-13.5" />
                    </svg>
                  ) : stage.state === 'failed' ? (
                    <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={3} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  ) : (
                    <span>{i + 1}</span>
                  )}
                </div>
                <span className="text-[11px] font-medium truncate" style={{ color: stage.state === 'pending' ? 'hsl(var(--muted-2))' : c.bg === 'hsl(var(--surface-3))' ? 'hsl(var(--muted-2))' : c.bg }}>
                  {stage.label}
                </span>
              </div>
              {i < stages.length - 1 && (
                <div className="h-px flex-1 min-w-[12px]" style={{ background: c.line }} />
              )}
            </div>
          )
        })}
      </div>
    </div>
  )
}
