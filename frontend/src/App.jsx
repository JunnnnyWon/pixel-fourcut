import { Routes, Route } from 'react-router-dom'
import UserScreen from './UserScreen'
import AdminScreen from './AdminScreen'
import PrintScreen from './PrintScreen'

export default function App() {
  return (
    <Routes>
      <Route path="/" element={<UserScreen />} />
      <Route path="/admin" element={<AdminScreen />} />
      <Route path="/print" element={<PrintScreen />} />
    </Routes>
  )
}
