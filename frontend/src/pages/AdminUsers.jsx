import { useEffect, useState } from 'react';
import { api } from '../api';

const roleName = { admin: '管理员', dm: 'DM', player: '玩家' };
const roleBadge = { admin: 'warn', dm: 'stage', player: '' };

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
      setOk(`${u.email} 已设为 ${roleName[role] || role}`);
      load();
    } catch (e) {
      setErr(e.message);
    }
  };

  return (
    <>
      <h2 className="page-title">用户<span>管理</span></h2>
      <p className="page-sub">熟人邀请制 · 开通 DM 权限</p>
      <div className="card">
        {err && <div className="err">{err}</div>}
        {ok && <div className="okmsg">{ok}</div>}
        <ul className="list">
          {users.map((u) => (
            <li key={u.id} className="row space">
              <span>
                <b>{u.nickname || u.email}</b> <span className="muted">{u.email}</span>{' '}
                <span className={`badge ${roleBadge[u.role] || ''}`}>{roleName[u.role] || u.role}</span>
              </span>
              <select value={u.role} onChange={(e) => setRole(u, e.target.value)} style={{ width: 'auto' }}>
                <option value="player">玩家</option>
                <option value="dm">DM</option>
                <option value="admin">管理员</option>
              </select>
            </li>
          ))}
        </ul>
        {users.length === 0 && <p className="muted">暂无用户</p>}
      </div>
    </>
  );
}
