import { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api } from '../api';
import coverDefault from '../assets/cover-default.webp';
import emptyState from '../assets/empty-state.webp';

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
      <h2 className="page-title">剧本<span>馆</span></h2>
      <p className="page-sub">选一个故事 · 走进去</p>

      <div className="card">
        <h3>加入房间</h3>
        {err && <div className="err">{err}</div>}
        <form onSubmit={join} className="codejoin">
          <input
            type="text" placeholder="6 位房间码" value={code}
            onChange={(e) => setCode(e.target.value.toUpperCase())}
            maxLength={6} style={{ textTransform: 'uppercase' }}
          />
          <button className="btn" type="submit">进入</button>
        </form>
      </div>

      {loading ? <p className="muted">上架中…</p> : scripts.length === 0 ? (
        <div className="empty">
          <img src={emptyState} alt="" />
          <p>书架还是空的，等管理员上架剧本。</p>
        </div>
      ) : (
        scripts.map((s) => (
          <div className="scard" key={s.id}>
            <img className="cover" src={coverDefault} alt="" />
            <div>
              <div className="ti">{s.title}</div>
              {s.description && <div className="ds">{s.description.slice(0, 60)}</div>}
              <div className="tags">
                <span className="badge">{s.player_min}–{s.player_max} 人</span>
              </div>
            </div>
          </div>
        ))
      )}
      <p className="muted center">开房请找 DM</p>
    </>
  );
}
