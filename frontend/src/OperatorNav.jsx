import { NavLink } from 'react-router-dom'

export default function OperatorNav() {
  return (
    <nav className="operator-nav">
      <NavLink to="/admin" className={({ isActive }) => `operator-nav-link ${isActive ? 'active' : ''}`}>
        촬영 관리
      </NavLink>
      <NavLink to="/print" className={({ isActive }) => `operator-nav-link ${isActive ? 'active' : ''}`}>
        인화 / 지난 팀
      </NavLink>
      <NavLink to="/" className={({ isActive }) => `operator-nav-link ${isActive ? 'active' : ''}`}>
        공용 화면
      </NavLink>
    </nav>
  )
}
