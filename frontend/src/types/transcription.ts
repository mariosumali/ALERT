export type TranscriptionStatusState = 'idle' | 'processing' | 'processing_transcription' | 'processing_audio' | 'ready' | 'error' | 'empty'

export interface TranscriptionStatusPayload {
  state: TranscriptionStatusState
  detail?: string
}
