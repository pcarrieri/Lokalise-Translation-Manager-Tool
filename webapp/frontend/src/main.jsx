import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'

// ✅ Importa entrambi i CSS
import './index.css'
import './App.css'

import App from './App.jsx'

createRoot(document.getElementById('root')).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
