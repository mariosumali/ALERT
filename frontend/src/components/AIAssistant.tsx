import { useState, useRef, useEffect, useCallback } from 'react'
import { useVideo } from '../contexts/VideoContext'
import { chatWithTranscript, type ChatMessage } from '../utils/api'
import { formatTimestamp } from '../types/events'
import type { CaseMetadata, DetectedEvent } from '../types/events'

interface AIAssistantProps {
  fileId: string | null
  caseInfo?: CaseMetadata | null
  selectedEvent?: DetectedEvent | null
}

interface AssistantMessage {
  role: 'user' | 'assistant'
  content: string
  visualAnalysis?: boolean
  timestamps?: number[]
}

interface QuickAction {
  id: string
  label: string
  prompt: string
}

const QUICK_ACTIONS: QuickAction[] = [
  { id: 'summary60', label: 'Summarize last 60s', prompt: 'Summarize what happened in the last 60 seconds of footage.' },
  { id: 'flagged',   label: 'Explain why flagged', prompt: 'Explain why this segment was flagged as a notable event.' },
  { id: 'commands',  label: 'List commands given', prompt: 'List all officer commands and directives in chronological order with timestamps.' },
  { id: 'uof',       label: 'Use-of-force indicators?', prompt: 'Were there any use-of-force indicators? List all instances with timestamps.' },
]

const SUMMARY_ACTIONS: QuickAction[] = [
  { id: 'incident',  label: 'Incident Summary', prompt: 'Provide a concise summary of this incident. Include the key people involved, what happened, and the outcome.' },
  { id: 'timeline',  label: 'Event Timeline',   prompt: 'Create a detailed chronological timeline of all significant events with timestamps.' },
  { id: 'escalation',label: 'Escalation Points', prompt: 'Identify all escalation and de-escalation points in this incident.' },
  { id: 'report',    label: 'Generate Report',   prompt: 'Generate a structured incident report suitable for official documentation. Include: Incident Overview, Timeline of Events, Key Observations, Persons Involved.' },
  { id: 'weapons',   label: 'Weapons & Force',   prompt: 'Were any weapons mentioned, displayed, or used? Was any physical force applied? List all instances with timestamps.' },
]

function MessageContent({ content, onSeek }: { content: string; onSeek: (time: number) => void }) {
  const regex = /(\d{1,2}:\d{2}(?::\d{2})?)/g
  const parts: (string | { text: string; time: number })[] = []
  let last = 0
  let m: RegExpExecArray | null
  while ((m = regex.exec(content)) !== null) {
    if (m.index > last) parts.push(content.slice(last, m.index))
    const p = m[1].split(':').map(Number)
    let s = 0
    if (p.length === 3) s = p[0] * 3600 + p[1] * 60 + p[2]
    else if (p.length === 2) s = p[0] * 60 + p[1]
    parts.push({ text: m[1], time: s })
    last = m.index + m[0].length
  }
  if (last < content.length) parts.push(content.slice(last))

  if (parts.length === 0 || (parts.length === 1 && typeof parts[0] === 'string')) {
    return <span className="whitespace-pre-wrap break-words">{content}</span>
  }

  return (
    <span className="whitespace-pre-wrap break-words">
      {parts.map((p, i) =>
        typeof p === 'string' ? (
          <span key={i}>{p}</span>
        ) : (
          <button
            key={i}
            onClick={() => onSeek(p.time)}
            className="inline-flex items-center gap-0.5 font-mono text-[11px] px-1 py-0.5 rounded transition-colors"
            style={{
              color: 'hsl(var(--primary))',
              background: 'hsl(var(--primary) / 0.1)',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.background = 'hsl(var(--primary) / 0.2)')}
            onMouseLeave={(e) => (e.currentTarget.style.background = 'hsl(var(--primary) / 0.1)')}
          >
            <svg className="w-2.5 h-2.5" fill="currentColor" viewBox="0 0 20 20">
              <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM9.555 7.168A1 1 0 008 8v4a1 1 0 001.555.832l3-2a1 1 0 000-1.664l-3-2z" clipRule="evenodd" />
            </svg>
            [{p.text}]
          </button>
        )
      )}
    </span>
  )
}

export default function AIAssistant({ fileId, caseInfo, selectedEvent }: AIAssistantProps) {
  const { currentTime, seekTo } = useVideo()
  const [mode, setMode] = useState<'ask' | 'summary'>('ask')
  const [messages, setMessages] = useState<AssistantMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [activeAction, setActiveAction] = useState<string | null>(null)
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  useEffect(() => {
    setMessages([])
    setError(null)
    setActiveAction(null)
  }, [fileId])

  const sendMessage = useCallback(async (text: string, actionId?: string) => {
    if (!text.trim() || !fileId || loading) return

    if (actionId) setActiveAction(actionId)
    const userMsg: ChatMessage = { role: 'user', content: text.trim() }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)
    setError(null)

    try {
      const history = [...messages, userMsg]
      const response = await chatWithTranscript(fileId, history)
      setMessages((prev) => [...prev, {
        role: response.message.role,
        content: response.message.content,
        visualAnalysis: response.visual_analysis_used,
        timestamps: response.analyzed_timestamps ?? undefined,
      }])
    } catch (err: any) {
      setError(err.response?.data?.detail || err.message || 'Analysis failed')
    } finally {
      setLoading(false)
      setActiveAction(null)
    }
  }, [fileId, loading, messages])

  const handleUseSelection = () => {
    if (!selectedEvent) return
    const ctx = `[Selected event: ${selectedEvent.type.join(', ')} at ${formatTimestamp(selectedEvent.timestamp)}–${formatTimestamp(selectedEvent.endTime)}: "${selectedEvent.description}"]`
    setInput((prev) => prev ? `${prev}\n${ctx}` : ctx)
  }

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      sendMessage(input)
    }
  }

  if (!fileId) return null

  const hasConversation = messages.length > 0

  return (
    <div className="flex flex-col h-full">
      {/* Context header */}
      <div className="px-3 py-2.5 flex-shrink-0" style={{ borderBottom: '1px solid hsl(var(--border))' }}>
        <div className="flex items-center gap-2 mb-2">
          <div className="w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0" style={{ background: 'hsl(var(--primary))' }}>
            <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z" />
            </svg>
          </div>
          <span className="text-xs font-semibold text-txt">AI Assist</span>
        </div>
        <div className="flex items-center gap-2 text-[10px] text-muted-2">
          {caseInfo?.filename && caseInfo.filename !== 'Processing...' && (
            <span className="truncate max-w-[120px]">{caseInfo.filename}</span>
          )}
          <span className="font-mono tabular-nums">{formatTimestamp(currentTime)}</span>
          {selectedEvent && (
            <span className="truncate" style={{ color: 'hsl(var(--primary))' }}>
              {selectedEvent.type.join(', ')}
            </span>
          )}
        </div>

        {/* Mode tabs */}
        <div className="flex mt-2 rounded-lg overflow-hidden" style={{ background: 'hsl(var(--surface-3))' }}>
          {(['ask', 'summary'] as const).map((m) => (
            <button
              key={m}
              onClick={() => setMode(m)}
              className="flex-1 py-1.5 text-[11px] font-semibold uppercase tracking-wider transition-colors"
              style={{
                background: mode === m ? 'hsl(var(--primary) / 0.15)' : 'transparent',
                color: mode === m ? 'hsl(var(--primary))' : 'hsl(var(--muted-2))',
              }}
            >
              {m === 'ask' ? 'Ask' : 'Summary'}
            </button>
          ))}
        </div>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto">
        {mode === 'ask' ? (
          !hasConversation ? (
            <div className="p-3 space-y-3">
              <p className="text-[11px] text-muted-2">Quick prompts</p>
              <div className="flex flex-wrap gap-1.5">
                {QUICK_ACTIONS.map((a) => (
                  <button
                    key={a.id}
                    onClick={() => sendMessage(a.prompt, a.id)}
                    disabled={loading}
                    className="text-[11px] px-2.5 py-1.5 rounded-lg transition-colors"
                    style={{
                      background: 'hsl(var(--surface-2))',
                      color: loading && activeAction === a.id ? 'hsl(var(--primary))' : 'hsl(var(--muted))',
                      border: '1px solid hsl(var(--border))',
                    }}
                    onMouseEnter={(e) => {
                      e.currentTarget.style.borderColor = 'hsl(var(--primary) / 0.4)'
                      e.currentTarget.style.color = 'hsl(var(--text))'
                    }}
                    onMouseLeave={(e) => {
                      e.currentTarget.style.borderColor = 'hsl(var(--border))'
                      e.currentTarget.style.color = 'hsl(var(--muted))'
                    }}
                  >
                    {a.label}
                    {loading && activeAction === a.id && (
                      <span className="ml-1.5 inline-block w-2.5 h-2.5 border border-primary border-t-transparent rounded-full animate-spin" />
                    )}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            <div className="px-3 py-3 space-y-3">
              {messages.map((msg, idx) => (
                <div key={idx} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'} animate-fade-in`}>
                  {msg.role === 'assistant' && (
                    <div className="w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 mr-2 mt-0.5" style={{ background: 'hsl(var(--primary))' }}>
                      <svg className="w-3 h-3 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z" />
                      </svg>
                    </div>
                  )}
                  <div className={`max-w-[88%] text-[13px] leading-relaxed ${
                    msg.role === 'user'
                      ? 'rounded-xl rounded-br-sm px-3 py-2 text-white'
                      : 'text-txt'
                  }`}
                    style={msg.role === 'user' ? { background: 'hsl(var(--primary))' } : {}}
                  >
                    <MessageContent content={msg.content} onSeek={seekTo} />
                    {msg.visualAnalysis && msg.timestamps && msg.timestamps.length > 0 && (
                      <div className="mt-2 pt-1.5 flex items-center gap-1.5 text-[10px] text-muted-2" style={{ borderTop: '1px solid hsl(var(--border) / 0.3)' }}>
                        <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                          <path d="M10 12a2 2 0 100-4 2 2 0 000 4z" />
                          <path fillRule="evenodd" d="M.458 10C1.732 5.943 5.522 3 10 3s8.268 2.943 9.542 7c-1.274 4.057-5.064 7-9.542 7S1.732 14.057.458 10zM14 10a4 4 0 11-8 0 4 4 0 018 0z" clipRule="evenodd" />
                        </svg>
                        Analyzed frames at {msg.timestamps.map((t) => formatTimestamp(t)).join(', ')}
                      </div>
                    )}
                  </div>
                </div>
              ))}

              {loading && (
                <div className="flex items-start animate-fade-in">
                  <div className="w-5 h-5 rounded-md flex items-center justify-center flex-shrink-0 mr-2 mt-0.5" style={{ background: 'hsl(var(--primary))' }}>
                    <svg className="w-3 h-3 text-white animate-pulse" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="M9.813 15.904 9 18.75l-.813-2.846a4.5 4.5 0 0 0-3.09-3.09L2.25 12l2.846-.813a4.5 4.5 0 0 0 3.09-3.09L9 5.25l.813 2.846a4.5 4.5 0 0 0 3.09 3.09L15.75 12l-2.846.813a4.5 4.5 0 0 0-3.09 3.09Z" />
                    </svg>
                  </div>
                  <div className="flex items-center gap-1.5 text-xs text-muted-2">
                    <div className="flex gap-0.5">
                      <div className="w-1 h-1 rounded-full animate-bounce" style={{ background: 'hsl(var(--muted-2))', animationDelay: '0ms' }} />
                      <div className="w-1 h-1 rounded-full animate-bounce" style={{ background: 'hsl(var(--muted-2))', animationDelay: '100ms' }} />
                      <div className="w-1 h-1 rounded-full animate-bounce" style={{ background: 'hsl(var(--muted-2))', animationDelay: '200ms' }} />
                    </div>
                    Analyzing…
                  </div>
                </div>
              )}

              {error && (
                <div className="text-xs rounded-lg px-3 py-2" style={{ color: 'hsl(var(--danger))', background: 'hsl(var(--danger) / 0.1)' }}>
                  {error}
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>
          )
        ) : (
          /* Summary mode */
          <div className="p-3 space-y-3">
            <p className="text-[11px] text-muted-2">Generate structured analysis</p>
            <div className="space-y-1.5">
              {SUMMARY_ACTIONS.map((a) => (
                <button
                  key={a.id}
                  onClick={() => { setMode('ask'); sendMessage(a.prompt, a.id) }}
                  disabled={loading}
                  className="w-full text-left px-3 py-2.5 rounded-lg transition-colors flex items-center justify-between group"
                  style={{ background: 'hsl(var(--surface-2))', border: '1px solid hsl(var(--border))' }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.borderColor = 'hsl(var(--primary) / 0.3)'
                    e.currentTarget.style.background = 'hsl(var(--surface-3))'
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.borderColor = 'hsl(var(--border))'
                    e.currentTarget.style.background = 'hsl(var(--surface-2))'
                  }}
                >
                  <span className="text-xs font-medium text-muted group-hover:text-txt transition-colors">{a.label}</span>
                  {loading && activeAction === a.id ? (
                    <span className="w-3 h-3 border-2 border-primary border-t-transparent rounded-full animate-spin" />
                  ) : (
                    <svg className="w-3.5 h-3.5 text-muted-2 group-hover:text-muted transition-colors" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                      <path strokeLinecap="round" strokeLinejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                    </svg>
                  )}
                </button>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* Input bar */}
      <div className="px-3 py-2.5 flex-shrink-0" style={{ borderTop: '1px solid hsl(var(--border))' }}>
        {hasConversation && (
          <div className="flex items-center justify-between mb-2">
            <div className="flex gap-1 overflow-x-auto">
              {QUICK_ACTIONS.slice(0, 2).map((a) => (
                <button
                  key={a.id}
                  onClick={() => sendMessage(a.prompt, a.id)}
                  disabled={loading}
                  className="text-[10px] px-1.5 py-0.5 rounded transition-colors whitespace-nowrap disabled:opacity-50"
                  style={{
                    color: 'hsl(var(--muted-2))',
                    border: '1px solid hsl(var(--border))',
                  }}
                  onMouseEnter={(e) => (e.currentTarget.style.color = 'hsl(var(--muted))')}
                  onMouseLeave={(e) => (e.currentTarget.style.color = 'hsl(var(--muted-2))')}
                >
                  {a.label}
                </button>
              ))}
              {selectedEvent && (
                <button
                  onClick={handleUseSelection}
                  className="text-[10px] px-1.5 py-0.5 rounded transition-colors whitespace-nowrap"
                  style={{
                    color: 'hsl(var(--primary))',
                    border: '1px solid hsl(var(--primary) / 0.3)',
                    background: 'hsl(var(--primary) / 0.06)',
                  }}
                >
                  Use selection
                </button>
              )}
            </div>
            <button
              onClick={() => { setMessages([]); setError(null) }}
              className="text-[10px] transition-colors"
              style={{ color: 'hsl(var(--muted-2))' }}
              onMouseEnter={(e) => (e.currentTarget.style.color = 'hsl(var(--muted))')}
              onMouseLeave={(e) => (e.currentTarget.style.color = 'hsl(var(--muted-2))')}
            >
              Clear
            </button>
          </div>
        )}
        <div className="flex gap-2">
          <input
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            placeholder={hasConversation ? 'Follow-up question…' : 'Ask about the footage…'}
            className="input-base flex-1 px-3 py-1.5 text-sm"
            disabled={loading}
          />
          <button
            onClick={() => sendMessage(input)}
            disabled={loading || !input.trim()}
            className="btn-primary px-3 py-1.5"
          >
            <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 12L3.269 3.126A59.768 59.768 0 0121.485 12 59.77 59.77 0 013.27 20.876L5.999 12zm0 0h7.5" />
            </svg>
          </button>
        </div>
      </div>
    </div>
  )
}
