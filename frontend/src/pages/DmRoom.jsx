import { useCallback, useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api';
import { useRoomSocket } from '../useRoomSocket';

const STAGE_NEXT = { waiting: 'selecting', selecting: 'reading', reading: 'investigating', investigating: 'discussing', discussing: 'voting', voting: 'reveal', reveal: 'ended' };
const stageName = { waiting: '等待', selecting: '选角', reading: '读本', investigating: '搜证', discussing: '讨论', voting: '投票', reveal: '复盘', ended: '结束' };

export default function DmRoom() {
  const { id } = useParams();
  const [room, setRoom] = useState(null);
  const [chars, setChars] = useState([]);
  const [clues, setClues] = useState([]);
  const [err, setErr] = useState('');
  const [ok, setOk] = useState('');
  const [assignPid, setAssignPid] = useState('');
  const [assignCid, setAssignCid] = useState('');
  const [clueId, setClueId] = useState('');
  const [clueScope, setClueScope] = useState('public');
  const [cluePid, setCluePid] = useState('');

  const load = useCallback(async () => {
    try {
      const r = await api(`/rooms/${id}`);
      setRoom(r);
      const [cs, cl] = await Promise.all([
        api(`/dm/rooms/${id}/characters`).catch(() => []),
        api(`/dm/rooms/${id}/clues`).catch(() => []),
      ]);
      setChars(cs);
      setClues(cl);
      if (r.players.length && !assignPid) setAssignPid(String(r.players[0].user_id));
      if (cs.length && !assignCid) setAssignCid(String(cs[0].id));
      if (cl.length && !clueId) setClueId(String(cl[0].id));
    } catch (e) {
      setErr(e.message);
    }
  }, [id]);

  useEffect(() => { load(); }, [load]);
  useRoomSocket(id, () => load());

  const act = async (fn, good) => {
    setErr(''); setOk('');
    try {
      await fn();
      setOk(good || '操作成功');
      load();
    } catch (e) {
      setErr(e.message);
    }
  };

  if (!room) return <p className="muted">正在入场…</p>;
  const next = STAGE_NEXT[room.stage];

  return (
    <>
      <h2 className="page-title">控场<span>台</span></h2>
      <p className="page-sub">{room.script ? room.script.title : ''} · <span className="badge code">{room.code}</span></p>
      {err && <div className="err">{err}</div>}
      {ok && <div className="okmsg">{ok}</div>}

      <div className="dm-layout">
      <div>
      <div className="card">
        <div className="row space">
          <h3 style={{ margin: 0 }}>当前阶段</h3>
          <span className="badge stage">{stageName[room.stage]}</span>
        </div>
        <div className="ctl-row">
          {room.stage === 'waiting' && (
            <button className="btn" onClick={() => act(() => api(`/dm/rooms/${id}/start`, { method: 'POST' }), '已开局，进入选角')}>开始游戏</button>
          )}
          {next && room.stage !== 'waiting' && room.stage !== 'voting' && (
            <button className="btn" onClick={() => act(() => api(`/dm/rooms/${id}/advance`, { method: 'POST', body: {} }), `已切到${stageName[next]}`)}>
              下一步：{stageName[next]}
            </button>
          )}
          {room.stage === 'discussing' && (
            <button className="btn" onClick={() => act(() => api(`/dm/rooms/${id}/vote/open`, { method: 'POST' }), '投票已开启')}>开启投票</button>
          )}
          {room.stage === 'voting' && (
            <button className="btn danger" onClick={() => act(() => api(`/dm/rooms/${id}/vote/close`, { method: 'POST' }), '投票已关闭，进入复盘')}>关闭投票</button>
          )}
          {room.stage === 'reveal' && (
            <button className="btn" onClick={() => act(() => api(`/dm/rooms/${id}/finish`, { method: 'POST' }), '真相已公布，本局结束')}>公布真相</button>
          )}
        </div>
      </div>

      <div className="card">
        <h3>在场 · {room.players.length} 人</h3>
        <ul className="list">
          {room.players.map((p) => (
            <li key={p.user_id}>{p.nickname || `玩家${p.user_id}`}
              {p.character_name && <span className="badge">{p.character_name}</span>}
            </li>
          ))}
        </ul>
      </div>
      </div>
      <div>

      <div className="card">
        <h3>分配角色</h3>
        <div className="row">
          <select value={assignPid} onChange={(e) => setAssignPid(e.target.value)} style={{ flex: 1 }}>
            {room.players.map((p) => <option key={p.user_id} value={p.user_id}>{p.nickname || p.user_id}</option>)}
          </select>
          <select value={assignCid} onChange={(e) => setAssignCid(e.target.value)} style={{ flex: 1 }}>
            {chars.map((c) => <option key={c.id} value={c.id}>{c.name}</option>)}
          </select>
          <button className="btn small" onClick={() => act(
            () => api(`/dm/rooms/${id}/assign`, { method: 'POST', body: { player_id: Number(assignPid), character_id: Number(assignCid) } }),
            '分配成功'
          )}>分配</button>
        </div>
      </div>

      <div className="card">
        <h3>投放线索</h3>
        <label className="f">线索</label>
        <select value={clueId} onChange={(e) => setClueId(e.target.value)}>
          {clues.map((c) => <option key={c.id} value={c.id}>{c.title}</option>)}
        </select>
        <div className="row mt">
          <select value={clueScope} onChange={(e) => setClueScope(e.target.value)} style={{ flex: 1 }}>
            <option value="public">公开（全体可见）</option>
            <option value="private">定向（指定玩家）</option>
          </select>
          {clueScope === 'private' && (
            <select value={cluePid} onChange={(e) => setCluePid(e.target.value)} style={{ flex: 1 }}>
              <option value="">选择玩家</option>
              {room.players.map((p) => <option key={p.user_id} value={p.user_id}>{p.nickname || p.user_id}</option>)}
            </select>
          )}
          <button className="btn small" onClick={() => act(
            () => api(`/dm/rooms/${id}/clues/reveal`, {
              method: 'POST',
              body: { clue_id: Number(clueId), scope: clueScope, player_id: clueScope === 'private' ? Number(cluePid) : null },
            }),
            '线索已投放'
          )}>投放</button>
        </div>
      </div>
      </div>
      </div>
    </>
  );
}
