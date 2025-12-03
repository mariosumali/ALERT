export type StatusBannerVariant = 'info' | 'success' | 'error'

export interface StatusBannerProps {
  variant: StatusBannerVariant
  title: string
  message?: string
  onClose?: () => void
}

const variantStyles: Record<StatusBannerVariant, { container: string; accent: string }> = {
  info: {
    container: 'bg-blue-50 border-blue-200 text-blue-900',
    accent: 'bg-blue-400',
  },
  success: {
    container: 'bg-green-50 border-green-200 text-green-900',
    accent: 'bg-green-400',
  },
  error: {
    container: 'bg-red-50 border-red-200 text-red-900',
    accent: 'bg-red-400',
  },
}

const variantIcon: Record<StatusBannerVariant, string> = {
  info: 'ℹ️',
  success: '✅',
  error: '⚠️',
}

export default function StatusBanner({ variant, title, message, onClose }: StatusBannerProps) {
  const classes = variantStyles[variant]

  return (
    <div
      className={`relative flex items-start gap-3 rounded-xl border px-4 py-3 shadow-sm transition-colors ${classes.container}`}
      role="status"
      aria-live="polite"
    >
      <span className={`flex h-8 w-8 items-center justify-center rounded-full text-lg ${classes.accent}`}>
        <span className="sr-only">{variant} status</span>
        <span>{variantIcon[variant]}</span>
      </span>
      <div className="flex-1">
        <p className="font-semibold leading-tight">{title}</p>
        {message && <p className="mt-1 text-sm leading-snug opacity-80">{message}</p>}
      </div>
      {onClose && (
        <button
          onClick={onClose}
          className="ml-2 rounded-full p-1 text-sm opacity-60 transition hover:bg-black/5 hover:opacity-100"
          aria-label="Dismiss status"
        >
          ✕
        </button>
      )}
    </div>
  )
}
