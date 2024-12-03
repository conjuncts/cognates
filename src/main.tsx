import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
// import App from './App.tsx'
import EtymologyVisualizer from './EtymologyVisualizer.tsx'
import './index.css'
// import CytoExample from './CytoExample.tsx'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <EtymologyVisualizer />
    {/* <CytoExample /> */}
  </StrictMode>,
)
