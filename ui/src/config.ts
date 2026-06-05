// Copyright (C) 2025 AIDC-AI
// Licensed under the MIT License.

const isDevelopment = import.meta.env.MODE === 'development'

// All API routes are served by the ComfyUI plugin on the same origin.
const defaultApiBaseUrl = typeof window !== 'undefined' ? window.location.origin : ''

export const github_url = 'https://github.com/AIDC-AI/ComfyUI-Copilot'

export const config = {
  apiBaseUrl: isDevelopment
    ? defaultApiBaseUrl
    : (import.meta.env.VITE_API_BASE_URL || defaultApiBaseUrl)
}
