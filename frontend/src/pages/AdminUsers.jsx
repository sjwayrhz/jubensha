import { useEffect, useState } from 'react';
import { api } from '../api';

export default function AdminUsers() {
  const [users, setUsers] = useState([]);
  const [err, setErr] = useState('');
  const [ok, setOk] = useState('');

  const load = () => api('/admin/users').then(setUsers).catch((e) => setErr(e.message));
  useEffect(load, []);

  const setRole = async (u, role) => {
    setErr(''); setOk('');
    try {
      await api(`/admin/users/${u.id}/role`, { method: 'PUT', body: { role } });
      setOk(`${u.email} 已设为 ${role}`);
      load();
    } catch (e) {
      setErr(e.message);
    }
  };

  return (
    <div className="card">
      <h3>用户管理（熟人邀请制开 DM 权限）</h3>
      {err && <div className="err">{err}</div>}
      {ok && <div className="okmsg">{ok}</div>}
      <ul className="list">
        {users.map((u) => (
          <li key={u.id} className="row space">
            <span>
              <b>{u.nickname || u.email}</b> <span className="muted">{u.email}</span>
              <span className="badge">{u.role}</span>
            </span>
            <select value={u.role} onChange={(e) => setRole(u, e.target.value)}>
              <option value="player">player</option>
              <option value="dm">dm</option>
              <option value="admin">admin</option>
            </select>
          </li>
        ))}
      </ul>
      {users.length === 0 && <p className="muted">暂无用户</p>}
    </div>
  );
}
