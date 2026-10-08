import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth.jsx';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [err, setErr] = useState('');
  const [busy, setBusy] = useState(false);
  const { login } = useAuth();
  const nav = useNavigate();

  const submit = async (e) => {
    e.preventDefault();
    setErr('');
    setBusy(true);
    try {
      const u = await login(email.trim(), password);
      nav(u.role === 'admin' ? '/admin/scripts' : u.role === 'dm' ? '/dm' : '/', { replace: true });
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="card" style={{ marginTop: 40 }}>
      <h3>登录</h3>
      {err && <div className="err">{err}</div>}
      <form onSubmit={submit}>
        <label className="f">邮箱</label>
        <input type="email" value={email} onChange={(e) => setEmail(e.target.value)} required />
        <label className="f">密码</label>
        <input type="password" value={password} onChange={(e) => setPassword(e.target.value)} required />
        <div className="mt">
          <button className="btn block" disabled={busy}>{busy ? '登录中…' : '登录'}</button>
        </div>
      </form>
      <p className="muted center">没有账号？<Link to="/register">去注册</Link></p>
    </div>
  );
}
