import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth.jsx';
import loginBg from '../assets/login-bg.webp';

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
    <div className="login-page" style={{ backgroundImage: `url(${loginBg})` }}>
      <div className="login-in">
        <h1 className="login-title">剧本<em>杀</em></h1>
        <p className="login-sub">走进故事 · 成为故事</p>
        {err && <div className="err">{err}</div>}
        <form onSubmit={submit}>
          <input type="email" placeholder="邮箱" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <input type="password" placeholder="密码" value={password} onChange={(e) => setPassword(e.target.value)} required />
          <button className="btn block" disabled={busy}>{busy ? '推门中…' : '进 入'}</button>
        </form>
        <p className="login-alt">还没有账号？<Link to="/register">去注册</Link></p>
      </div>
    </div>
  );
}
