export type TranscriptionStatusState = 'idle' | 'processing' | 'ready' | 'error' | 'empty'

export interface TranscriptionStatusPayload {
  state: TranscriptionStatusState
  detail?: string
}
