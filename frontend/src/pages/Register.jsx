import { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuth } from '../auth.jsx';
import loginBg from '../assets/login-bg.webp';

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
    <div className="login-page" style={{ backgroundImage: `url(${loginBg})` }}>
      <div className="login-in">
        <h1 className="login-title">剧本<em>杀</em></h1>
        <p className="login-sub">写下你的名字 · 入 戏</p>
        {err && <div className="err">{err}</div>}
        <form onSubmit={submit}>
          <input type="email" placeholder="邮箱" value={email} onChange={(e) => setEmail(e.target.value)} required />
          <input type="text" placeholder="昵称" value={nickname} onChange={(e) => setNickname(e.target.value)} required />
          <input type="password" placeholder="密码（至少 6 位）" value={password} onChange={(e) => setPassword(e.target.value)} required minLength={6} />
          <button className="btn block" disabled={busy}>{busy ? '注册中…' : '注 册'}</button>
        </form>
        <p className="login-alt">已有账号？<Link to="/login">去登录</Link></p>
      </div>
    </div>
  );
}
