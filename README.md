# jubensha · 网页版剧本杀

在线网页版剧本杀（类似百变大侦探）：管理员上传剧本、DM 控场、玩家用浏览器即玩，无需安装。

**线上地址：https://jubensha.monk.de5.net**（手机/电脑浏览器直接打开）

## 功能特性

### 玩家端
- 邮箱注册登录（无短信验证），输入 6 位房间码加入
- 按阶段游玩：选角 → 读本（只看自己的角色剧本）→ 搜证（公开/定向线索）→ 讨论（文字聊天 + 异步语音条）→ 投票（一人一票，不可投自己）→ 真相复盘
- WebSocket 实时推送：DM 切阶段、投线索、开关投票即时同步，断线自动重连

### DM 控制台
- 选剧本建房，6 位房间码发给玩家
- 分配角色、按阶段推进、投放公开/定向线索、开关投票、公布真相

### 管理后台
- 剧本全链路：上传 PDF → 解析（文字提取/扫描版 OCR）→ 人工校对 → 结构化发布（规则拆分人物/线索，"真凶：X"自动标记）
- 用户管理：给熟人开通 DM 权限（注册默认都是 player）
- 剧本来源要求：公开免费剧本必须记录原始链接、作者/发布方及授权说明，无来源不发布

## 技术栈

| 层 | 选型 |
|---|---|
| 后端 | Python 3.14 / FastAPI（REST + WebSocket） |
| 前端 | React 18 + Vite，mobile-first，构建产物由后端直接托管 |
| 数据库 | TiDB Cloud（MySQL 协议），与 ludepress 共用集群、独立 database `jubensha` |
| 部署 | clerk 服务器（无公网 IP）：入站走 cloudflared 隧道，出站走 `http://192.168.56.1:7897` 代理 |

## 本地快速开始

### 后端

```bash
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp .env.example ../.env   # .env 在项目根目录，填写真实值，不要提交
uvicorn app.main:app --reload --port 8000
```

`.env` 固定在**项目根目录**（`backend/` 的上一级），与启动时的当前目录无关。

数据库未配置也能启动（降级模式：`/healthz` 显示 `db_configured: false`，DB 相关接口报错）。

### 前端

```bash
cd frontend
npm install
npm run dev      # 开发模式
npm run build    # 生产构建，产物在 frontend/dist（gitignored）
```

后端 `app/main.py` 会自动托管 `frontend/dist`（含 SPA fallback），API 保持 `/api/v1` 前缀。

## 环境变量

以 `backend/app/core/config.py` 为准：

| 变量 | 说明 | 默认 |
|---|---|---|
| APP_ENV / APP_NAME | 环境名/应用名 | dev / jubensha |
| TIDB_HOST / TIDB_PORT / TIDB_USER / TIDB_PASSWORD / TIDB_DB | TiDB 连接 | 端口 4000，库名 jubensha |
| TIDB_SSL_CA | TiDB Cloud CA 证书路径（需 TLS 时） | 空 |
| JWT_SECRET | JWT 签名密钥，**生产必须改** | change-me |
| JWT_ALGORITHM | 签名算法 | HS256 |
| JWT_EXPIRE_MINUTES | token 有效期（分钟） | 10080（7 天） |
| UPLOAD_DIR | 剧本 PDF 上传目录 | uploads |
| MAX_UPLOAD_MB | PDF 大小上限（MB） | 50 |
| OCR_TEXT_THRESHOLD | 文字提取少于该字数则判为扫描版走 OCR | 200 |
| VOICE_DIR | 语音条存放目录 | uploads/voice |
| MAX_VOICE_MB | 语音条大小上限（MB） | 2 |
| VOICE_ALLOWED_EXT | 语音格式白名单 | mp3,m4a,wav,amr,webm |

## 项目结构

```
jubensha/
├── backend/
│   ├── app/
│   │   ├── main.py          # 入口：API + 前端 SPA 托管 + /healthz
│   │   ├── core/            # config / security(bcrypt+JWT) / deps(鉴权)
│   │   ├── db/              # SQLAlchemy engine/session，连接失败降级启动
│   │   ├── models/          # User/Script/ScriptCharacter/ScriptClue/Room/…
│   │   ├── schemas/         # pydantic 请求/响应模型
│   │   ├── api/v1/          # auth/admin/scripts/dm/rooms/chat/voice/ws
│   │   ├── services/        # PDF 解析(文字提取+Tesseract OCR)/结构化规则
│   │   └── ws/              # 房间级 WebSocket 连接管理与事件广播
│   └── requirements.txt
├── frontend/                # React 18 + Vite
│   └── src/pages/           # Login/Register/Home/Room/DM/Admin…
├── docs/
│   ├── DESIGN.md            # 技术方案设计
│   ├── 操作手册.md           # 管理员/DM/玩家操作手册
│   └── 部署手册.md           # 服务器部署与运维手册
└── .env.example             # 占位示例，无真实凭据
```

## 文档

- `docs/DESIGN.md` —— 技术方案设计（架构、模块、数据模型）
- `docs/操作手册.md` —— 管理员 / DM / 玩家三端操作步骤 + 常见问题
- `docs/部署手册.md` —— clerk 服务器部署、隧道配置、日常运维

## 部署状态

- 生产环境：clerk `/root/jubensha`（git 同步），venv `/root/venvs/jubensha`
- systemd `jubensha.service` 常驻 + 开机自启，公网 https://jubensha.monk.de5.net
- 测试管理员账号 `admin@jubensha.local` 仅用于测试，**上线前必须改密码**
