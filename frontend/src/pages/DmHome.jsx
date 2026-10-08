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
    api('/scripts').then((ss) => {
      setScripts(ss);
      if (ss.length && !scriptId) setScriptId(String(ss[0].id));
    }).catch(() => {});
  };
  useEffect(load, []);

  const removeRoom = async (r) => {
    if (!window.confirm(`确定删除房间 ${r.code}（${r.script_title}）吗？房间内的聊天、语音、投票记录会一并删除。`)) return;
    setErr(''); setOk('');
    try {
      await api(`/dm/rooms/${r.id}`, { method: 'DELETE' });
      setOk(`房间 ${r.code} 已删除`);
      load();
    } catch (ex) {
      setErr(ex.message);
    }
  };

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
                <span>
                  <Link className="btn small" to={`/dm/rooms/${r.id}`}>控场</Link>
                  <button className="btn small danger" style={{ marginLeft: 8 }} onClick={() => removeRoom(r)}>删除</button>
                </span>
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
