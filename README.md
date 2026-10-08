# jubensha（网页版剧本杀 · 第一阶段）

Python(FastAPI) 后端骨架。React 前端为二期。详细设计见 `docs/DESIGN.md`。

## 本地运行

```bash
cd backend
pip install -r requirements.txt
cp .env.example .env   # 填写真实值，不要提交
uvicorn app.main:app --reload --port 8000
```

## 环境变量

| 变量 | 说明 | 默认 |
|---|---|---|
| TIDB_HOST | TiDB 主机 | 空=未配置（降级启动） |
| TIDB_PORT | 端口 | 4000 |
| TIDB_USER | 用户名 | 空 |
| TIDB_PASSWORD | 密码 | 空 |
| TIDB_DB | database | jubensha |
| TIDB_SSL_CA | TiDB Cloud CA 证书路径（需 TLS 时） | 空 |
| JWT_SECRET | JWT 签名密钥，生产必须改 | change-me |
| JWT_EXPIRE_MINUTES | token 有效期（分钟） | 10080 |

数据库未配置也能启动（降级模式：DB 相关接口报错，启动日志有明确提示）。

## clerk 部署注意

clerk 无直连外网：pip 安装走代理 `http://192.168.56.1:7897`；玩家入站走 cloudflared 隧道。
