# jubensha 技术方案设计（第一阶段）

在线网页版剧本杀（类似百变大侦探）：管理员上传剧本（PDF+OCR 二期）、DM（熟人邀请制）控场、玩家邮箱注册、多房间并行。

## 1. 技术栈

| 层 | 选型 | 说明 |
|---|---|---|
| 后端 | Python 3.11+ / FastAPI | REST + WebSocket（二期） |
| 前端 | React（二期） | 移动端优先，手机浏览器即玩 |
| 数据库 | TiDB Cloud（MySQL 协议） | 与 ludepress 共用集群，独立 database `jubensha` |
| 部署 | clerk `/root/jubensha` | 无公网 IP、无直连外网：入站走 cloudflared 隧道，出站走代理 `192.168.56.1:7897` |

## 2. 系统架构

```
玩家浏览器 ──HTTPS──▶ cloudflared 隧道 ──▶ clerk:8000 (uvicorn)
                                              ├─ FastAPI REST /api/v1
                                              ├─ WebSocket /ws/room/{code}（二期）
                                              └─ PyMySQL ─▶ TiDB Cloud（经代理）
```

管理员 / DM / 玩家三类角色由 JWT 中的 role 区分，不建三套登录。

## 3. 模块划分（backend/app）

- `core/`：config（pydantic-settings，全走环境变量）、security（bcrypt+JWT）、deps（鉴权依赖）
- `db/`：SQLAlchemy engine / session；启动时探测连接，失败不崩、降级为警告
- `models/`：User / Script / ScriptCharacter / ScriptClue / Room / RoomPlayer
- `schemas/`：pydantic 请求/响应模型
- `api/v1/`：auth（注册/登录）、admin（剧本管理骨架）；rooms、dm、ws 均为二期

## 4. API 端点概要

一期（本阶段）：
- `POST /api/v1/auth/register` {email,password,nickname} → 注册玩家（role=player）
- `POST /api/v1/auth/login`（form: username=email, password）→ JWT
- `GET /api/v1/auth/me` → 当前用户
- `GET /api/v1/admin/scripts` → 剧本列表占位（需 admin）

二期：剧本上传/解析管线（PDF 提取 + PaddleOCR + 人工校对）、房间 CRUD、DM 控场（切阶段/发线索/开投票/公布真相）、WebSocket 房间实时同步、投票、异步语音条上传/播放。

## 5. 数据模型

- `users`(id, email!, password_hash, role[admin|dm|player], nickname, created_at)
- `scripts`(id, title, description, player_min/max, duration_min, difficulty, status[draft|published], source_url, source_note, created_by→users, created_at)
- `script_characters`(id, script_id→scripts, name, description, is_murderer, sort_order)
- `script_clues`(id, script_id→scripts, character_id→script_characters?, title, content, clue_type[public|personal|hidden], sort_order)
- `rooms`(id, code!, script_id→scripts, dm_id→users, stage[waiting|reading|searching|discussion|voting|reveal|finished], created_at)
- `room_players`(id, room_id→rooms, user_id→users, character_id→script_characters?, is_ready, unique(room_id,user_id))

个人剧本正文存 `script_characters.description`（长文本）；公共线索走 `script_clues`。

## 6. 分阶段计划

1. ✅ 方案设计 + 后端骨架 + 数据模型（本阶段）
2. 剧本上传/解析管线（PDF 提取 + PaddleOCR + 人工校对页）
3. 房间/开本流水状态机 + DM 控场 API
4. WebSocket 实时同步 + 投票 + 异步语音条
5. React 前端（玩家端 + DM 控制台 + 管理后台）
6. clerk 联调部署 + 内测
