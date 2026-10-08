import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api';
import emptyState from '../assets/empty-state.webp';

const stageName = { waiting: '等待', selecting: '选角', reading: '读本', investigating: '搜证', discussing: '讨论', voting: '投票', reveal: '复盘', ended: '结束' };

export default function DmHome() {
  const [rooms, setRooms] = useState([]);
  const [scripts, setScripts] = useState([]);
  const [scriptId, setScriptId] = useState('');
  const [err, setErr] = useState('');
  const [ok, setOk] = useState('');

  const load = () => {
    api('/dm/rooms').then(setRooms).catch((e) => setErr(e.message));
    api('/admin/scripts').then((ss) => {
      const pub = ss.filter((s) => s.status === 'published');
      setScripts(pub);
      if (pub.length && !scriptId) setScriptId(String(pub[0].id));
    }).catch(() => {});
  };
  useEffect(load, []);

  const create = async (e) => {
    e.preventDefault();
    setErr(''); setOk('');
    try {
      const r = await api('/dm/rooms', { method: 'POST', body: { script_id: Number(scriptId) } });
      setOk(`建房成功，房间码：${r.code}`);
      load();
    } catch (ex) {
      setErr(ex.message);
    }
  };

  return (
    <>
      <h2 className="page-title">DM <span>控场</span></h2>
      <p className="page-sub">你是今晚的导演</p>

      <div className="dm-layout">
      <div>
      <div className="card">
        <h3>新建房间</h3>
        {err && <div className="err">{err}</div>}
        {ok && <div className="okmsg">{ok}</div>}
        {scripts.length === 0 ? (
          <p className="muted">暂无已发布剧本，先去剧本管理发布。</p>
        ) : (
          <form onSubmit={create} className="row">
            <select value={scriptId} onChange={(e) => setScriptId(e.target.value)} style={{ flex: 1 }}>
              {scripts.map((s) => <option key={s.id} value={s.id}>{s.title}</option>)}
            </select>
            <button className="btn" type="submit">建房</button>
          </form>
        )}
      </div>
      </div>
      <div>
      <div className="card">
        <h3>我的房间</h3>
        {rooms.length === 0 ? (
          <div className="empty">
            <img src={emptyState} alt="" />
            <p>还没有开过房，选个剧本开始吧。</p>
          </div>
        ) : (
          <ul className="list">
            {rooms.map((r) => (
              <li key={r.id} className="row space">
                <span>
                  <b>{r.script_title}</b> <span className="badge code">{r.code}</span>
                  <span className="badge stage">{stageName[r.stage] || r.stage}</span>
                  <span className="muted">{r.player_count} 人</span>
                </span>
                <Link className="btn small" to={`/dm/rooms/${r.id}`}>控场</Link>
              </li>
            ))}
          </ul>
        )}
      </div>
      </div>
      </div>
    </>
  );
}
