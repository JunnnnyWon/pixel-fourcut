import { Routes, Route } from 'react-router-dom'
import UserScreen from './UserScreen'
import AdminScreen from './AdminScreen'
import PrintScreen from './PrintScreen'
import HistoryScreen from './HistoryScreen'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<UserScreen />} />
      <Route path="/admin" element={<AdminScreen />} />
      <Route path="/print" element={<PrintScreen />} />
      <Route path="/history" element={<HistoryScreen />} />
    </Routes>
  )
}
