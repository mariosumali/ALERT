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

