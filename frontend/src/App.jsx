import { BrowserRouter, Routes, Route } from 'react-router-dom'
import { Sidebar } from './components/Sidebar.jsx'
import Dashboard from './pages/Dashboard.jsx'
import LiveStream from './pages/LiveStream.jsx'
import Capture from './pages/Capture.jsx'
import Schedule from './pages/Schedule.jsx'
import Library from './pages/Library.jsx'

export default function App() {
  return (
    <BrowserRouter>
      <div className="flex h-screen overflow-hidden bg-zinc-950">
        <Sidebar />
        <div className="flex-1 flex flex-col overflow-hidden">
          <Routes>
            <Route path="/" element={<Dashboard />} />
            <Route path="/live" element={<LiveStream />} />
            <Route path="/capture" element={<Capture />} />
            <Route path="/schedule" element={<Schedule />} />
            <Route path="/library" element={<Library />} />
          </Routes>
        </div>
      </div>
    </BrowserRouter>
  )
}
