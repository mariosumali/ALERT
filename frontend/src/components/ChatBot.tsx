import { useState, useRef, useEffect } from 'react'
import { chatWithTranscript, ChatMessage } from '../utils/api'

interface ChatBotProps {
  fileId: string | null
}

interface MessageWithMetadata {
  role: 'user' | 'assistant'
  content: string
  visualAnalysis?: boolean
  timestamps?: number[]
}

export default function ChatBot({ fileId }: ChatBotProps) {
  const [messages, setMessages] = useState<MessageWithMetadata[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Clear chat when fileId changes (new video uploaded)
  useEffect(() => {
    setMessages([])
    setError(null)
  }, [fileId])

  const handleSend = async () => {
    if (!input.trim() || !fileId || loading) return

    const userMessage: ChatMessage = {
      role: 'user',
      content: input.trim(),
    }

    // Add user message immediately
    setMessages((prev) => [...prev, userMessage])
    setInput('')
    setLoading(true)
    setError(null)

    try {
      // Get current conversation history
      const conversationHistory = [...messages, userMessage]

      const response = await chatWithTranscript(fileId, conversationHistory)

      // Add assistant response with metadata
      setMessages((prev) => [...prev, {
        role: response.message.role,
        content: response.message.content,
        visualAnalysis: response.visual_analysis_used,
        timestamps: response.analyzed_timestamps
      }])
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Failed to get response')
      console.error('Chat error:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  const handleClear = () => {
    setMessages([])
    setError(null)
  }

  if (!fileId) {
    return (
      <div className="rounded-lg bg-white p-6 shadow-md">
        <h2 className="mb-4 text-2xl font-semibold">Chat</h2>
        <p className="text-gray-500">Upload and transcribe a video to start chatting about it.</p>
      </div>
    )
  }

  return (
    <div className="flex h-[600px] flex-col rounded-lg bg-white shadow-md">
      <div className="flex items-center justify-between border-b p-4">
        <h2 className="text-2xl font-semibold">Chat</h2>
        {messages.length > 0 && (
          <button
            onClick={handleClear}
            className="rounded px-3 py-1 text-sm text-gray-600 hover:bg-gray-100"
          >
            Clear
          </button>
        )}
      </div>

      {/* Messages area */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && (
          <div className="text-center text-gray-500 mt-8">
            <p className="mb-2">Ask me anything about the video transcript!</p>
            <p className="text-sm">Try questions like:</p>
            <ul className="text-sm mt-2 space-y-1">
              <li>"What is this video about?"</li>
              <li>"Summarize the key points"</li>
              <li>"What happened at 2:30?" <span className="text-blue-500">(✨ with visual analysis)</span></li>
            </ul>
          </div>
        )}

        {messages.map((msg, idx) => (
          <div
            key={idx}
            className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-[80%] rounded-lg px-4 py-2 ${msg.role === 'user'
                  ? 'bg-blue-500 text-white'
                  : 'bg-gray-100 text-gray-800'
                }`}
            >
              <div className="whitespace-pre-wrap break-words">{msg.content}</div>
              {msg.visualAnalysis && msg.timestamps && msg.timestamps.length > 0 && (
                <div className="mt-2 pt-2 border-t border-gray-300 text-xs text-gray-600 flex items-center gap-1">
                  <svg className="w-4 h-4" fill="currentColor" viewBox="0 0 20 20">
                    <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                    <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
                  </svg>
                  <span>Visual analysis performed</span>
                </div>
              )}
            </div>
          </div>
        ))}

        {loading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 rounded-lg px-4 py-2">
              <div className="flex items-center space-x-2">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '0ms' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '150ms' }}></div>
                  <div className="w-2 h-2 bg-gray-400 rounded-full animate-bounce" style={{ animationDelay: '300ms' }}></div>
                </div>
                <span className="text-xs text-gray-500">Analyzing...</span>
              </div>
            </div>
          </div>
        )}

        {error && (
          <div className="bg-red-50 border border-red-200 rounded-lg p-3 text-red-700 text-sm">
            {error}
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Input area */}
      <div className="border-t p-4">
        <div className="flex space-x-2">
          <textarea
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyPress={handleKeyPress}
            placeholder="Ask a question about the transcript..."
            className="flex-1 rounded-lg border border-gray-300 px-4 py-2 resize-none focus:outline-none focus:ring-2 focus:ring-blue-500"
            rows={2}
            disabled={loading}
          />
          <button
            onClick={handleSend}
            disabled={loading || !input.trim()}
            className="rounded-lg bg-blue-600 px-6 py-2 text-white transition-colors hover:bg-blue-700 disabled:cursor-not-allowed disabled:bg-gray-400"
          >
            Send
          </button>
        </div>
      </div>
    </div>
  )
}

