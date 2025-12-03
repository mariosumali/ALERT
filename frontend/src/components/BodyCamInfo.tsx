import React from 'react'

interface BodyCamInfoProps {
    metadata: {
        device_id?: string | null
        device_model?: string | null
        badge_number?: string | null
        timestamp?: string | null
        officer_id?: string | null
    } | null
    isLoading: boolean
}

export default function BodyCamInfo({ metadata, isLoading }: BodyCamInfoProps) {
    if (isLoading) {
        return (
            <div className="rounded-lg bg-white p-6 shadow-md animate-pulse">
                <div className="h-6 w-1/3 bg-gray-200 rounded mb-4"></div>
                <div className="grid grid-cols-2 gap-4">
                    <div className="h-4 bg-gray-200 rounded"></div>
                    <div className="h-4 bg-gray-200 rounded"></div>
                    <div className="h-4 bg-gray-200 rounded"></div>
                    <div className="h-4 bg-gray-200 rounded"></div>
                </div>
            </div>
        )
    }

    if (!metadata) {
        return null
    }

    // Check if we have any relevant data
    const hasData = metadata.device_id || metadata.device_model || metadata.badge_number || metadata.timestamp

    if (!hasData) {
        return (
            <div className="rounded-lg bg-white p-6 shadow-md">
                <h2 className="mb-4 text-2xl font-semibold">BodyCam Info</h2>
                <p className="text-gray-500 text-sm">No body camera metadata detected in video frames.</p>
            </div>
        )
    }

    return (
        <div className="rounded-lg bg-white p-6 shadow-md">
            <h2 className="mb-4 text-2xl font-semibold flex items-center gap-2">
                <svg className="w-6 h-6 text-blue-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M10 6H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V8a2 2 0 00-2-2h-5m-4 0V5a2 2 0 114 0v1m-4 0a2 2 0 104 0m-5 8a2 2 0 100-4 2 2 0 000 4zm0 0c1.306 0 2.417.835 2.83 2M9 14a3.001 3.001 0 00-2.83 2M15 11h3m-3 4h2" />
                </svg>
                BodyCam Info
            </h2>

            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                {metadata.device_model && (
                    <div className="bg-gray-50 p-3 rounded-lg border border-gray-100">
                        <p className="text-xs text-gray-500 uppercase font-semibold tracking-wider">Device Model</p>
                        <p className="text-lg font-medium text-gray-800">{metadata.device_model}</p>
                    </div>
                )}

                {metadata.device_id && (
                    <div className="bg-gray-50 p-3 rounded-lg border border-gray-100">
                        <p className="text-xs text-gray-500 uppercase font-semibold tracking-wider">Device ID</p>
                        <p className="text-lg font-medium text-gray-800 font-mono">{metadata.device_id}</p>
                    </div>
                )}

                {metadata.badge_number && (
                    <div className="bg-gray-50 p-3 rounded-lg border border-gray-100">
                        <p className="text-xs text-gray-500 uppercase font-semibold tracking-wider">Badge Number</p>
                        <p className="text-lg font-medium text-gray-800">{metadata.badge_number}</p>
                    </div>
                )}

                {metadata.timestamp && (
                    <div className="bg-gray-50 p-3 rounded-lg border border-gray-100">
                        <p className="text-xs text-gray-500 uppercase font-semibold tracking-wider">Recorded Timestamp</p>
                        <p className="text-lg font-medium text-gray-800">{metadata.timestamp}</p>
                    </div>
                )}
            </div>

            <div className="mt-4 text-xs text-gray-400 text-right">
                Extracted via OCR from video frames
            </div>
        </div>
    )
}
