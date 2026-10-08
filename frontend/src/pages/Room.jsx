import { useCallback, useEffect, useRef, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api, apiBlob } from '../api';
import { useAuth } from '../auth.jsx';
import { useRoomSocket } from '../useRoomSocket';

const STAGES = [
  ['waiting', '等待'], ['selecting', '选角'], ['reading', '读本'],
  ['investigating', '搜证'], ['discussing', '讨论'], ['voting', '投票'],
  ['reveal', '复盘'], ['ended', '结束'],
];
const stageName = (s) => (STAGES.find(([k]) => k === s) || [s, s])[1];

function StageBar({ stage }) {
  const idx = STAGES.findIndex(([k]) => k === stage);
  return (
    <div className="stagebar">
      {STAGES.map(([k, n], i) => (
        <span key={k} className={i === idx ? 'cur' : i < idx ? 'done' : ''}>{n}</span>
      ))}
    </div>
  );
}

export default function Room() {
  const { id } = useParams();
  const { user } = useAuth();
  const [room, setRoom] = useState(null);
  const [err, setErr] = useState('');
  const [myScript, setMyScript] = useState(null);
  const [clues, setClues] = useState([]);
  const [chat, setChat] = useState([]);
  const [voices, setVoices] = useState([]);
  const [counts, setCounts] = useState(null);
  const [result, setResult] = useState(null);
  const [chatInput, setChatInput] = useState('');
  const [recording, setRecording] = useState(false);
  const recRef = useRef(null);
  const [playingId, setPlayingId] = useState(null);
  const audioRef = useRef(null);

  const loadRoom = useCallback(async () => {
    try {
      const r = await api(`/rooms/${id}`);
      setRoom(r);
      return r;
    } catch (e) {
      setErr(e.message);
      return null;
    }
  }, [id]);

  const loadStage = useCallback(async (r) => {
    if (!r) return;
    try {
      if (['reading', 'investigating', 'discussing', 'voting', 'reveal', 'ended'].includes(r.stage)) {
        api(`/rooms/${id}/my-script`).then(setMyScript).catch(() => setMyScript(null));
      }
      if (['investigating', 'discussing', 'voting', 'reveal', 'ended'].includes(r.stage)) {
        api(`/rooms/${id}/clues`).then(setClues).catch(() => {});
      }
      if (['discussing', 'voting', 'reveal', 'ended'].includes(r.stage)) {
        api(`/rooms/${id}/chat?since=0`).then(setChat).catch(() => {});
        api(`/rooms/${id}/voice`).then(setVoices).catch(() => {});
      }
      if (['reveal', 'ended'].includes(r.stage)) {
        api(`/rooms/${id}/result`).then(setResult).catch(() => {});
      }
    } catch {
      /* 忽略分支加载失败 */
    }
  }, [id]);

  useEffect(() => {
    loadRoom().then(loadStage);
  }, [loadRoom, loadStage]);

  // WS 事件 → 刷新
  const onEvent = useCallback((ev) => {
    if (String(ev.room_id) !== String(id)) return;
    if (ev.type === 'stage_changed' || ev.type === 'player_joined' || ev.type === 'room_ended') {
      loadRoom().then(loadStage);
    } else if (ev.type === 'clue_revealed') {
      api(`/rooms/${id}/clues`).then(setClues).catch(() => {});
    } else if (ev.type === 'vote_update') {
      setCounts(ev.data);
    } else if (ev.type === 'chat_new') {
      setChat((c) => [...c, ev.data]);
    } else if (ev.type === 'voice_new') {
      api(`/rooms/${id}/voice`).then(setVoices).catch(() => {});
    }
  }, [id, loadRoom, loadStage]);
  const connected = useRoomSocket(id, onEvent);

  // waiting/selecting 阶段轮询兜底（分配角色无 WS 事件）
  useEffect(() => {
    if (!room || !['waiting', 'selecting'].includes(room.stage)) return;
    const t = setInterval(() => loadRoom(), 8000);
    return () => clearInterval(t);
  }, [room, loadRoom]);

  const sendChat = async (e) => {
    e.preventDefault();
    const c = chatInput.trim();
    if (!c) return;
    setChatInput('');
    try {
      const m = await api(`/rooms/${id}/chat`, { method: 'POST', body: { content: c } });
      setChat((list) => [...list, m]); // WS 也会推，去重靠 id
    } catch (ex) {
      setErr(ex.message);
    }
  };

  const startRec = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
      const mime = MediaRecorder.isTypeSupported('audio/mp4')
        ? 'audio/mp4'
        : MediaRecorder.isTypeSupported('audio/webm') ? 'audio/webm' : '';
      const mr = new MediaRecorder(stream, mime ? { mimeType: mime } : undefined);
      const chunks = [];
      mr.ondataavailable = (e) => e.data.size && chunks.push(e.data);
      mr.onstop = async () => {
        stream.getTracks().forEach((t) => t.stop());
        setRecording(false);
        const blob = new Blob(chunks, { type: mr.mimeType || 'audio/webm' });
        const ext = (mr.mimeType || '').includes('mp4') ? 'm4a' : 'webm';
        const fd = new FormData();
        fd.append('file', blob, `voice.${ext}`);
        try {
          await api(`/rooms/${id}/voice`, { method: 'POST', form: fd });
          api(`/rooms/${id}/voice`).then(setVoices).catch(() => {});
        } catch (ex) {
          setErr(ex.message);
        }
      };
      mr.start();
      recRef.current = mr;
      setRecording(true);
    } catch {
      setErr('无法打开麦克风，请检查浏览器权限');
    }
  };
  const stopRec = () => {
    try { recRef.current && recRef.current.stop(); } catch { setRecording(false); }
  };

  const playVoice = async (v) => {
    try {
      if (playingId === v.id && audioRef.current) {
        audioRef.current.pause();
        setPlayingId(null);
        return;
      }
      setPlayingId(v.id);
      const url = await apiBlob(`/rooms/${id}/voice/${v.id}/play`);
      const a = new Audio(url);
      audioRef.current = a;
      a.onended = () => setPlayingId(null);
      a.play();
    } catch (ex) {
      setErr(ex.message);
      setPlayingId(null);
    }
  };

  const vote = async (targetId) => {
    try {
      await api(`/rooms/${id}/vote`, { method: 'POST', body: { target_player_id: targetId } });
    } catch (ex) {
      setErr(ex.message);
    }
  };

  if (err && !room) return <div className="wrap"><div className="err">{err}</div></div>;
  if (!room) return <div className="wrap"><p className="muted">加载中…</p></div>;

  const me = room.players.find((p) => p.user_id === user.id);
  const others = room.players.filter((p) => p.user_id !== user.id);

  return (
    <>
      {err && <div className="err">{err}</div>}
      <div className="card">
        <div className="row space">
          <h3 style={{ margin: 0 }}>{room.script ? room.script.title : '房间'}</h3>
          <span className="badge stage">{stageName(room.stage)}</span>
        </div>
        <div className="muted">房间码 {room.code} · {connected ? '已连接' : '连接中…'}</div>
        <StageBar stage={room.stage} />
      </div>

      {(room.stage === 'waiting' || room.stage === 'selecting') && (
        <div className="card">
          <h3>成员（{room.players.length}）</h3>
          <ul className="list">
            {room.players.map((p) => (
              <li key={p.user_id}>
                {p.nickname || `玩家${p.user_id}`}
                {p.character_name && <span className="badge">{p.character_name}</span>}
                {p.user_id === user.id && <span className="badge ok">我</span>}
              </li>
            ))}
          </ul>
          <p className="muted">
            {room.stage === 'waiting' ? '等待 DM 开始游戏…' : 'DM 正在分配角色…'}
          </p>
        </div>
      )}

      {room.stage === 'reading' && (
        <div className="card">
          <h3>我的剧本{myScript ? ` · ${myScript.character_name}` : ''}</h3>
          {myScript ? (
            <div className="script-body">{myScript.description}</div>
          ) : (
            <p className="muted">DM 尚未给你分配角色，稍等…</p>
          )}
        </div>
      )}

      {['investigating', 'discussing', 'voting', 'reveal', 'ended'].includes(room.stage) && (
        <div className="card">
          <h3>线索（{clues.length}）</h3>
          {clues.length === 0 ? <p className="muted">DM 尚未投放线索</p> : (
            <ul className="list">
              {clues.map((c) => (
                <li key={c.id}>
                  <b>{c.title}</b>
                  {c.scope === 'private' && <span className="badge warn">定向</span>}
                  <div className="muted">{c.content}</div>
                </li>
              ))}
            </ul>
          )}
        </div>
      )}

      {['discussing', 'voting', 'reveal', 'ended'].includes(room.stage) && (
        <>
          <div className="card">
            <h3>讨论</h3>
            <div style={{ maxHeight: 260, overflowY: 'auto', marginBottom: 8 }}>
              {chat.length === 0 ? <p className="muted">还没有发言</p> : chat.map((m) => (
                <div className="msg" key={m.id}>
                  <span className="who">{m.sender_nickname}：</span>{m.content}
                </div>
              ))}
            </div>
            {room.stage !== 'ended' && (
              <form onSubmit={sendChat} className="row">
                <input type="text" value={chatInput} onChange={(e) => setChatInput(e.target.value)}
                  placeholder="说点什么…" maxLength={2000} style={{ flex: 1 }} />
                <button className="btn small" type="submit">发送</button>
              </form>
            )}
          </div>

          <div className="card">
            <h3>语音条（{voices.length}）</h3>
            {voices.map((v) => (
              <div className="voice" key={v.id}>
                <button className="btn small ghost" onClick={() => playVoice(v)}>
                  {playingId === v.id ? '暂停' : '播放'}
                </button>
                <span className="muted">{v.sender_nickname}{v.duration_sec ? ` · ${v.duration_sec}s` : ''}</span>
              </div>
            ))}
            {room.stage !== 'ended' && (
              <div className="rec">
                {recording ? (
                  <>
                    <span className="dot" />
                    <span className="muted">录音中…</span>
                    <button className="btn small danger" onClick={stopRec}>停止并发送</button>
                  </>
                ) : (
                  <button className="btn small ghost" onClick={startRec}>🎙 录语音条</button>
                )}
              </div>
            )}
          </div>
        </>
      )}

      {room.stage === 'voting' && (
        <div className="card">
          <h3>投票指凶（一人一票，不能投自己）</h3>
          <ul className="list">
            {others.map((p) => (
              <li key={p.user_id} className="row space">
                <span>{p.nickname || `玩家${p.user_id}`}{p.character_name ? `（${p.character_name}）` : ''}
                  {counts && counts.counts && counts.counts[String(p.user_id)] ? (
                    <span className="badge warn">{counts.counts[String(p.user_id)]} 票</span>
                  ) : null}
                </span>
                <button className="btn small" onClick={() => vote(p.user_id)}>投他</button>
              </li>
            ))}
          </ul>
          {counts && <p className="muted">已投 {counts.total} 票（实时）</p>}
        </div>
      )}

      {['reveal', 'ended'].includes(room.stage) && (
        <div className="card">
          <h3>真相复盘</h3>
          {result ? (
            <>
              <p><b>真凶：{result.murderer_name}</b></p>
              {result.murderer_description && <p className="muted">{result.murderer_description}</p>}
              {result.recap && <div className="script-body">{result.recap}</div>}
            </>
          ) : (
            <p className="muted">DM 正在公布真相…</p>
          )}
        </div>
      )}
    </>
  );
}
