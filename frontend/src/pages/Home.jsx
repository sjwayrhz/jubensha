import { useEffect, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api } from '../api';

export default function Home() {
  const [scripts, setScripts] = useState([]);
  const [code, setCode] = useState('');
  const [err, setErr] = useState('');
  const [loading, setLoading] = useState(true);
  const nav = useNavigate();

  useEffect(() => {
    api('/scripts')
      .then(setScripts)
      .catch((e) => setErr(e.message))
      .finally(() => setLoading(false));
  }, []);

  const join = async (e) => {
    e.preventDefault();
    setErr('');
    const c = code.trim().toUpperCase();
    if (!c) return;
    try {
      const r = await api(`/rooms/join?code=${encodeURIComponent(c)}`, { method: 'POST' });
      nav(`/rooms/${r.id}`);
    } catch (ex) {
      setErr(ex.message);
    }
  };

  return (
    <>
      <div className="card">
        <h3>加入房间</h3>
        {err && <div className="err">{err}</div>}
        <form onSubmit={join} className="row">
          <input
            type="text" placeholder="输入 6 位房间码" value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            maxLength={6} style={{ flex: 1, minWidth: 140, textTransform: 'uppercase' }}
          />
          <button className="btn" type="submit">进入</button>
        </form>
      </div>

      <div className="card">
        <h3>剧本</h3>
        {loading ? <p className="muted">加载中…</p> : scripts.length === 0 ? (
          <p className="muted">暂无已发布剧本，等管理员上架。</p>
        ) : (
          <ul className="list">
            {scripts.map((s) => (
              <li key={s.id}>
                <b>{s.title}</b>
                <div className="muted">
                  {s.player_min}–{s.player_max} 人{s.description ? ` · ${s.description.slice(0, 60)}` : ''}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
      <p className="muted center">开房请找 DM · <Link to="/dm" style={{ display: 'none' }}>dm</Link></p>
    </>
  );
}
