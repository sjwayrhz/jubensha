import { useEffect, useRef, useState } from 'react';
import { api } from '../api';
import emptyState from '../assets/empty-state.webp';

const statusName = { uploaded: '已上传', parsed: '已解析', reviewed: '已校对', published: '已发布' };
const statusBadge = { uploaded: '', parsed: 'stage', reviewed: 'stage', published: 'ok' };

export default function AdminScripts() {
  const [scripts, setScripts] = useState([]);
  const [err, setErr] = useState('');
  const [ok, setOk] = useState('');
  const [busy, setBusy] = useState(false);
  const [sel, setSel] = useState(null); // 当前编辑的剧本
  const [raw, setRaw] = useState('');
  const [parseInfo, setParseInfo] = useState(null);
  const fileRef = useRef(null);

  const load = () => api('/admin/scripts').then(setScripts).catch((e) => setErr(e.message));
  useEffect(load, []);

  const upload = async (e) => {
    const f = e.target.files && e.target.files[0];
    if (!f) return;
    setErr(''); setOk(''); setBusy(true);
    try {
      const fd = new FormData();
      fd.append('file', f);
      const r = await api('/admin/scripts/upload', { method: 'POST', form: fd });
      setOk(`上传成功，剧本 id=${r.script_id}，点「解析」继续`);
      load();
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
      e.target.value = '';
    }
  };

  const parse = async (s) => {
    setErr(''); setOk(''); setBusy(true);
    try {
      const r = await api(`/admin/scripts/${s.id}/parse`, { method: 'POST' });
      setParseInfo(r);
      const rawRes = await api(`/admin/scripts/${s.id}/raw`);
      setSel({ ...s, status: r.status });
      setRaw(rawRes.raw_text || '');
      setOk(`解析完成：方式=${r.method}，${r.chars} 字`);
      load();
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  };

  const openRaw = async (s) => {
    setErr('');
    try {
      const r = await api(`/admin/scripts/${s.id}/raw`);
      setSel(s);
      setRaw(r.raw_text || '');
      setParseInfo(null);
    } catch (ex) {
      setErr(ex.message);
    }
  };

  const saveRaw = async () => {
    setErr(''); setOk(''); setBusy(true);
    try {
      const r = await api(`/admin/scripts/${sel.id}/raw`, { method: 'PUT', body: { raw_text: raw } });
      setSel({ ...sel, status: r.status });
      setOk('校对文本已保存');
      load();
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  };

  const structure = async () => {
    setErr(''); setOk(''); setBusy(true);
    try {
      const r = await api(`/admin/scripts/${sel.id}/structure`, { method: 'POST' });
      setSel({ ...sel, status: r.status });
      setOk(`已发布：${r.characters} 个人物，${r.clues} 条线索`);
      load();
    } catch (ex) {
      setErr(ex.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <h2 className="page-title">剧本<span>管理</span></h2>
      <p className="page-sub">上传 · 解析 · 校对 · 发布</p>

      <div className="card">
        <h3>上传剧本 PDF</h3>
        {err && <div className="err">{err}</div>}
        {ok && <div className="okmsg">{ok}</div>}
        <input ref={fileRef} type="file" accept=".pdf" onChange={upload} disabled={busy} />
        <div className="pipe-steps">
          <b>上传</b><span className="arrow">→</span><span>解析</span><span className="arrow">→</span><span>校对</span><span className="arrow">→</span><span>结构化发布</span>
        </div>
        <p className="muted">文字版直接提取，扫描版走 OCR；发布前务必人工校对。</p>
      </div>

      <div className="card">
        <h3>剧本库</h3>
        <ul className="list">
          {scripts.map((s) => (
            <li key={s.id} className="row space">
              <span><b>{s.title}</b> <span className={`badge ${statusBadge[s.status] || ''}`}>{statusName[s.status] || s.status}</span></span>
              <span className="row">
                <button className="btn small ghost" onClick={() => parse(s)} disabled={busy}>解析</button>
                <button className="btn small ghost" onClick={() => openRaw(s)}>校对</button>
              </span>
            </li>
          ))}
        </ul>
        {scripts.length === 0 && (
          <div className="empty">
            <img src={emptyState} alt="" />
            <p>还没有剧本，传第一本吧。</p>
          </div>
        )}
      </div>

      {sel && (
        <div className="card">
          <h3>校对：{sel.title} <span className="badge">{statusName[sel.status] || sel.status}</span></h3>
          {parseInfo && <p className="muted">解析方式 {parseInfo.method} · {parseInfo.chars} 字</p>}
          <textarea value={raw} onChange={(e) => setRaw(e.target.value)} rows={14} />
          <div className="row mt">
            <button className="btn" onClick={saveRaw} disabled={busy}>保存校对</button>
            <button className="btn ghost" onClick={structure} disabled={busy}>结构化并发布</button>
          </div>
          <p className="muted">发布后玩家端可见；真凶标记请在文本中注明「真凶：X」。</p>
        </div>
      )}
    </>
  );
}
