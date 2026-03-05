import { useState, useCallback, useRef, useEffect } from 'react'
import { useTheme } from '../contexts/ThemeContext'
import { uploadFile } from '../utils/api'
import { formatTimestamp } from '../types/events'
import type { CaseMetadata } from '../types/events'

interface CaseHeaderProps {
  caseInfo: CaseMetadata | null
  onUploadSuccess: (fileId: string, fileUrl: string) => void
}

function InfoPopover({ caseInfo, onClose }: { caseInfo: CaseMetadata; onClose: () => void }) {
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    const handler = (e: MouseEvent) => {
      if (ref.current && !ref.current.contains(e.target as Node)) onClose()
    }
    document.addEventListener('mousedown', handler)
    return () => document.removeEventListener('mousedown', handler)
  }, [onClose])

  const rows: { label: string; value: string }[] = []
  if (caseInfo.filename && caseInfo.filename !== 'Processing...') rows.push({ label: 'Filename', value: caseInfo.filename })
  if (caseInfo.deviceModel) rows.push({ label: 'Camera Model', value: caseInfo.deviceModel })
  if (caseInfo.deviceId) rows.push({ label: 'Device ID', value: caseInfo.deviceId })
  if (caseInfo.badgeNumber) rows.push({ label: 'Badge Number', value: caseInfo.badgeNumber })
  if (caseInfo.officerId) rows.push({ label: 'Officer ID', value: caseInfo.officerId })
  if (caseInfo.recordedAt) rows.push({ label: 'Recorded', value: caseInfo.recordedAt })
  if (caseInfo.duration && caseInfo.duration > 0) rows.push({ label: 'Duration', value: formatTimestamp(caseInfo.duration) })

  return (
    <div ref={ref} className="absolute right-0 top-full mt-2 z-50 w-72 panel-elevated p-4 animate-fade-in">
      <h3 className="text-xs font-semibold text-txt mb-3">File Information</h3>
      {rows.length === 0 ? (
        <p className="text-xs text-muted-2">No metadata available yet.</p>
      ) : (
        <div className="space-y-2.5">
          {rows.map((r) => (
            <div key={r.label}>
              <dt className="text-[10px] uppercase tracking-wider font-semibold text-muted-2">{r.label}</dt>
              <dd className="text-[13px] text-txt mt-0.5">{r.value}</dd>
            </div>
          ))}
        </div>
      )}
      <p className="text-[10px] text-muted-2 mt-3 pt-2" style={{ borderTop: '1px solid hsl(var(--border))' }}>
        Extracted via OCR from video frames
      </p>
    </div>
  )
}

export default function CaseHeader({ caseInfo, onUploadSuccess }: CaseHeaderProps) {
  const { theme, toggle } = useTheme()
  const [uploading, setUploading] = useState(false)
  const [dragOver, setDragOver] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [showInfo, setShowInfo] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)

  const processFile = useCallback(async (file: File) => {
    setUploading(true)
    setError(null)
    try {
      const result = await uploadFile(file)
      const fileUrl = URL.createObjectURL(file)
      onUploadSuccess(result.file_id, fileUrl)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Upload failed')
    } finally {
      setUploading(false)
    }
  }, [onUploadSuccess])

  const handleDrop = useCallback((e: React.DragEvent) => {
    e.preventDefault()
    setDragOver(false)
    const file = e.dataTransfer.files[0]
    if (file && (file.type.startsWith('video/') || file.type.startsWith('audio/'))) {
      processFile(file)
    } else {
      setError('Please drop a video or audio file')
    }
  }, [processFile])

  const handleFileSelect = (e: React.ChangeEvent<HTMLInputElement>) => {
    const file = e.target.files?.[0]
    if (file) processFile(file)
  }

  return (
    <header className="flex-shrink-0" style={{ background: 'hsl(var(--surface-1))', borderBottom: '1px solid hsl(var(--border))' }}>
      <div className="px-4 flex items-center justify-between h-12">
        {/* Left: branding + inline metadata */}
        <div className="flex items-center gap-3 min-w-0">
          <div className="flex items-center gap-2 flex-shrink-0">
            <div className="w-6 h-6 rounded-md bg-primary flex items-center justify-center">
              <svg className="w-3.5 h-3.5 text-white" fill="none" viewBox="0 0 24 24" strokeWidth={2.5} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M9.348 14.652a3.75 3.75 0 010-5.304m5.304 0a3.75 3.75 0 010 5.304m-7.425 2.121a6.75 6.75 0 010-9.546m9.546 0a6.75 6.75 0 010 9.546M5.106 18.894c-3.808-3.807-3.808-9.98 0-13.788m13.788 0c3.808 3.807 3.808 9.98 0 13.788M12 12h.008v.008H12V12zm.375 0a.375.375 0 11-.75 0 .375.375 0 01.75 0z" />
              </svg>
            </div>
            <span className="text-sm font-bold tracking-tight text-txt">ALERT</span>
          </div>

          {caseInfo && (
            <div className="hidden md:flex items-center gap-3 pl-3 min-w-0" style={{ borderLeft: '1px solid hsl(var(--border))' }}>
              <span className="text-xs text-muted truncate max-w-[200px]" title={caseInfo.filename}>
                {caseInfo.filename}
              </span>
              {caseInfo.recordedAt && (
                <span className="text-[11px] text-muted-2 flex-shrink-0 font-mono tabular-nums">{caseInfo.recordedAt}</span>
              )}
              {caseInfo.duration && caseInfo.duration > 0 && (
                <span className="text-[11px] text-muted-2 flex-shrink-0 font-mono tabular-nums">{formatTimestamp(caseInfo.duration)}</span>
              )}
              {caseInfo.deviceModel && (
                <span className="text-[11px] text-muted-2 flex-shrink-0">{caseInfo.deviceModel}</span>
              )}
              {caseInfo.deviceId && (
                <span className="text-[11px] text-muted-2 flex-shrink-0 font-mono">{caseInfo.deviceId}</span>
              )}
            </div>
          )}
        </div>

        {/* Right: actions */}
        <div className="flex items-center gap-1.5">
          {error && <span className="text-[11px] text-danger mr-1">{error}</span>}

          {caseInfo && (
            <div className="relative">
              <button
                onClick={() => setShowInfo((v) => !v)}
                className="btn-ghost p-1.5 h-7 w-7"
                title="File info"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" />
                </svg>
              </button>
              {showInfo && <InfoPopover caseInfo={caseInfo} onClose={() => setShowInfo(false)} />}
            </div>
          )}

          <div
            className={`relative ${dragOver ? 'ring-2 ring-primary ring-offset-1 rounded-md' : ''}`}
            style={dragOver ? { '--tw-ring-offset-color': 'hsl(var(--surface-1))' } as React.CSSProperties : undefined}
            onDragOver={(e) => { e.preventDefault(); setDragOver(true) }}
            onDragLeave={() => setDragOver(false)}
            onDrop={handleDrop}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept="video/*,audio/*"
              onChange={handleFileSelect}
              className="hidden"
            />
            <button
              onClick={() => fileInputRef.current?.click()}
              disabled={uploading}
              className="btn-primary text-xs h-7 px-3"
            >
              {uploading ? (
                <>
                  <svg className="w-3 h-3 animate-spin" fill="none" viewBox="0 0 24 24">
                    <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                    <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                  </svg>
                  Processing…
                </>
              ) : (
                <>
                  <svg className="w-3 h-3" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" d="M12 16.5V9.75m0 0l3 3m-3-3l-3 3M6.75 19.5a4.5 4.5 0 01-1.41-8.775 5.25 5.25 0 0110.233-2.33 3 3 0 013.758 3.848A3.752 3.752 0 0118 19.5H6.75z" />
                  </svg>
                  {caseInfo ? 'New File' : 'Upload Footage'}
                </>
              )}
            </button>
          </div>

          <button
            onClick={toggle}
            className="btn-ghost p-1.5 h-7 w-7"
            title={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`}
          >
            {theme === 'dark' ? (
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M12 3v2.25m6.364.386l-1.591 1.591M21 12h-2.25m-.386 6.364l-1.591-1.591M12 18.75V21m-4.773-4.227l-1.591 1.591M5.25 12H3m4.227-4.773L5.636 5.636M15.75 12a3.75 3.75 0 11-7.5 0 3.75 3.75 0 017.5 0z" />
              </svg>
            ) : (
              <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" strokeWidth={2} stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" d="M21.752 15.002A9.718 9.718 0 0118 15.75c-5.385 0-9.75-4.365-9.75-9.75 0-1.33.266-2.597.748-3.752A9.753 9.753 0 003 11.25C3 16.635 7.365 21 12.75 21a9.753 9.753 0 009.002-5.998z" />
              </svg>
            )}
          </button>
        </div>
      </div>
    </header>
  )
}
