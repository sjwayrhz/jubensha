import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth.jsx';

export default function Register() {
  const [email, setEmail] = useState('');
  const [nickname, setNickname] = useState('');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const { register } = useAuth();
  const nav = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setErr('');
    setBusy(true);
    try {
      await register(email.trim(), password, nickname.trim());
      nav('/', { replace: true });
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card" style={{ marginTop: 40 }}>
      <h3>注册</h3>
      {err && <div className="err">{err}</div>}
      <form onSubmit={submit}>
        <label className="f">邮箱</label>
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <label className="f">昵称</label>
        <input type="text" value={nickname} onChange={(e) => setNickname(e.target.value)} required />
        <label className="f">密码</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} />
        <div className="mt">
          <button className="btn block" disabled={busy}>{busy ? '注册中…' : '注册'}</button>
        </div>
      </form>
      <p className="muted center">已有账号？<Link to="/login">去登录</Link></p>
    </div>
  );
}
