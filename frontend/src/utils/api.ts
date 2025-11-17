import axios from 'axios'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL || '/api'

export interface UploadResponse {
  file_id: string
  message: string
  status: string
}

export interface MomentsResponse {
  moments: Moment[]
  count: number
}

export interface Moment {
  moment_id: string
  file_id: string
  start_time: number
  end_time: number
  event_types: string[]
  interest_score: number
  description: string
}

export async function uploadFile(file: File): Promise<UploadResponse> {
  const formData = new FormData()
  formData.append('file', file)

  const response = await axios.post<UploadResponse>(
    `${API_BASE_URL}/upload`,
    formData,
    {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    }
  )

  return response.data
}

export async function getMoments(fileId?: string): Promise<MomentsResponse> {
  const url = fileId
    ? `${API_BASE_URL}/moments?file_id=${fileId}`
    : `${API_BASE_URL}/moments`

  const response = await axios.get<MomentsResponse>(url)
  return response.data
}

export interface TranscriptionResponse {
  file_id: string
  transcript: string
  segments: TranscriptionSegment[]
  has_transcription: boolean
}

export interface TranscriptionSegment {
  start: number
  end: number
  text: string
}

export async function transcribeFile(fileId: string): Promise<{ file_id: string; message: string; status: string }> {
  const response = await axios.post<{ file_id: string; message: string; status: string }>(
    `${API_BASE_URL}/transcribe?file_id=${fileId}`
  )
  return response.data
}

export async function getTranscription(fileId: string): Promise<TranscriptionResponse> {
  const response = await axios.get<TranscriptionResponse>(
    `${API_BASE_URL}/transcribe?file_id=${fileId}`
  )
  return response.data
}

export async function downloadTranscript(fileId: string): Promise<void> {
  const url = `${API_BASE_URL}/transcribe/download?file_id=${fileId}`
  const response = await axios.get(url, {
    responseType: 'blob',
  })
  
  // Create a blob URL and trigger download
  const blob = new Blob([response.data], { type: 'text/plain' })
  const blobUrl = window.URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = blobUrl
  link.download = `transcript_${fileId}.txt`
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  window.URL.revokeObjectURL(blobUrl)
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

export interface ChatResponse {
  message: ChatMessage
  usage?: {
    prompt_tokens: number
    completion_tokens: number
    total_tokens: number
  }
}

export async function chatWithTranscript(
  fileId: string,
  messages: ChatMessage[]
): Promise<ChatResponse> {
  const response = await axios.post<ChatResponse>(
    `${API_BASE_URL}/chat`,
    {
      file_id: fileId,
      messages: messages,
    }
  )
  return response.data
}

