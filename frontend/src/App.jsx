import { Link, NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom';
import { useAuth } from './auth.jsx';
import Login from './pages/Login.jsx';
import Register from './pages/Register.jsx';
import Home from './pages/Home.jsx';
import Room from './pages/Room.jsx';
import DmHome from './pages/DmHome.jsx';
import DmRoom from './pages/DmRoom.jsx';
import AdminScripts from './pages/AdminScripts.jsx';
import AdminUsers from './pages/AdminUsers.jsx';

function Guard({ children }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="wrap"><p className="muted">加载中…</p></div>;
  if (!user) return <Navigate to="/login" replace />;
  return children;
}

function RoleGuard({ roles, children }) {
  const { user } = useAuth();
  if (!user) return <Navigate to="/login" replace />;
  if (!roles.includes(user.role)) return <Navigate to="/" replace />;
  return children;
}

function Topbar() {
  const { user, logout } = useAuth();
  const loc = useLocation();
  if (!user || loc.pathname === '/login' || loc.pathname === '/register') return null;
  return (
    <div className="topbar">
      <div className="in">
        <Link className="brand" to="/">剧本杀</Link>
        <div className="nav">
          {(user.role === 'dm' || user.role === 'admin') && (
            <NavLink to="/dm" className={({ isActive }) => isActive ? 'on' : ''}>DM</NavLink>
          )}
          {user.role === 'admin' && (
            <>
              <NavLink to="/admin/scripts" className={({ isActive }) => isActive ? 'on' : ''}>剧本管理</NavLink>
              <NavLink to="/admin/users" className={({ isActive }) => isActive ? 'on' : ''}>用户</NavLink>
            </>
          )}
          <span className="muted">{user.nickname}</span>
          <button className="link" onClick={logout}>退出</button>
        </div>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <>
      <Topbar />
      <div className="wrap">
        <Routes>
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/" element={<Guard><Home /></Guard>} />
          <Route path="/rooms/:id" element={<Guard><Room /></Guard>} />
          <Route path="/dm" element={<RoleGuard roles={['dm', 'admin']}><DmHome /></RoleGuard>} />
          <Route path="/dm/rooms/:id" element={<RoleGuard roles={['dm', 'admin']}><DmRoom /></RoleGuard>} />
          <Route path="/admin/scripts" element={<RoleGuard roles={['admin']}><AdminScripts /></RoleGuard>} />
          <Route path="/admin/users" element={<RoleGuard roles={['admin']}><AdminUsers /></RoleGuard>} />
          <Route path="*" element={<Navigate to="/" replace />} />
        </Routes>
      </div>
    </>
  );
}
