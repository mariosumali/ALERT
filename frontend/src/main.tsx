import React from 'react'
import ReactDOM from 'react-dom/client'
import App from './App.tsx'
import { ThemeProvider } from './contexts/ThemeContext.tsx'
import { VideoProvider } from './contexts/VideoContext.tsx'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <ThemeProvider>
      <VideoProvider>
        <App />
      </VideoProvider>
    </ThemeProvider>
  </React.StrictMode>,
)
