import { Navigate, Routes, Route } from 'react-router-dom'
import AdminScreen from './AdminScreen'
import PrintScreen from './PrintScreen'
import HistoryScreen from './HistoryScreen'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<Navigate to="/admin" replace />} />
      <Route path="/admin" element={<AdminScreen />} />
      <Route path="/print" element={<PrintScreen />} />
      <Route path="/history" element={<HistoryScreen />} />
      <Route path="*" element={<Navigate to="/admin" replace />} />
    </Routes>
  )
}
