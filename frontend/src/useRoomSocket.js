import { useEffect, useRef, useState } from 'react';
import { getToken } from './api';

// 房间 WebSocket：断线自动重连，事件驱动刷新
export function useRoomSocket(roomId, onEvent) {
  const [connected, setConnected] = useState(false);
  const ref = useRef(onEvent);
  ref.current = onEvent;

  useEffect(() => {
    if (!roomId) return;
    let ws = null;
    let timer = null;
    let closed = false;
    const proto = location.protocol === 'https:' ? 'wss' : 'ws';
    const url =
      `${proto}://${location.host}/api/v1/ws/rooms/${roomId}` +
      `?token=${encodeURIComponent(getToken() || '')}`;

    const connect = () => {
      try {
        ws = new WebSocket(url);
      } catch {
        timer = setTimeout(() => !closed && connect(), 3000);
        return;
      }
      ws.onopen = () => setConnected(true);
      ws.onmessage = (e) => {
        try {
          ref.current && ref.current(JSON.parse(e.data));
        } catch {
          /* 忽略坏帧 */
        }
      };
      ws.onclose = () => {
        setConnected(false);
        if (!closed) timer = setTimeout(connect, 3000);
      };
      ws.onerror = () => {
        try {
          ws.close();
        } catch {
          /* ignore */
        }
      };
    };
    connect();
    return () => {
      closed = true;
      clearTimeout(timer);
      try {
        ws && ws.close();
      } catch {
        /* ignore */
      }
    };
  }, [roomId]);

  return connected;
}
