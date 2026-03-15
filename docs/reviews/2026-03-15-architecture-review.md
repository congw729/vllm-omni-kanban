# vLLM-Omni Kanban 架构审视报告

**Date:** 2026-03-15
**Reviewer:** Arch Analyzer
**Status:** Draft

---

## 1. 执行摘要

vLLM-Omni Kanban 是一个用于监控 vLLM 多模态模型 CI 稳定性、性能和准确性的仪表板系统。经过审视，该系统架构设计合理，PRD 需求覆盖度高（19/20 功能需求已实现），但存在以下关键问题：

1. **FR-07 未实现** - 缺少独立的硬件状态卡片
2. **依赖版本未锁定** - 可能导致构建不一致
3. **无安全性审视** - 原报告未覆盖安全性分析（已补充）

本报告已新增安全性审视、依赖分析章节，并修正了章节编号。

### 总体评估

| 维度 | 评分 | 说明 |
|------|------|------|
| **需求覆盖度** | ⭐⭐⭐⭐☆ | PRD 中 19/20 功能需求已实现（FR-07 缺失） |
| **架构合理性** | ⭐⭐⭐⭐☆ | 分层清晰，职责分离，但静态 JSON 有限制 |
| **可扩展性** | ⭐⭐⭐⭐⭐ | 配置驱动，新增模型/硬件无需改代码 |
| **可维护性** | ⭐⭐⭐⭐☆ | 模块化设计，测试覆盖要求明确 |
| **用户体验** | ⭐⭐⭐☆☆ | 功能完整，但交互体验有提升空间 |

---

## 2. 架构分析

### 2.1 当前架构

```
┌─────────────────────────────────────────────────────────────────────┐
│                         Data Sources                                 │
├────────────────────────┬────────────────────────────────────────────┤
│   vLLM-omni CI         │      External Results Source               │
│   (repository_dispatch)│      (scheduled fetch @ 6:00 AM Beijing)   │
└───────────┬────────────┴───────────────────┬────────────────────────┘
            │                                │
            ▼                                ▼
┌───────────────────────────────────────────────────────────────────────┐
│                     Ingestion Layer                                    │
│  ┌────────────────────────────┐  ┌─────────────────────────────────┐  │
│  │ fetch_latest_results.py    │  │ process_results.py              │  │
│  │ - Fetch daily batch        │  │ - Validate schema               │  │
│  │ - Auth via env token       │  │ - Deduplicate by (date,hw,model)│  │
│  │                            │  │ - Prune >90 days                │  │
│  │                            │  │ - Generate daily reports        │  │
│  └────────────────────────────┘  └─────────────────────────────────┘  │
└───────────────────────────────────────────────────────────────────────┘
            │
            ▼
┌───────────────────────────────────────────────────────────────────────┐
│                       Data Layer                                       │
│  ┌─────────────────────────────────────────────────────────────────┐  │
│  │  data/                                                           │  │
│  │  ├── results/YYYY-MM-DD.json  (per-date sharded)               │  │
│  │  ├── index.json               (date list, last_updated)        │  │
│  │  ├── config.json              (models, hardware, thresholds)   │  │
│  │  └── alerts.json              (alert history)                  │  │
│  └─────────────────────────────────────────────────────────────────┘  │
│                                                                        │
│  Storage: Static JSON files, 90-day rolling retention                 │
└───────────────────────────────────────────────────────────────────────┘
            │
            ├──────────────────────────────┐
            ▼                              ▼
┌───────────────────────┐      ┌───────────────────────────┐
│   Alerting Layer      │      │   Visualization Layer     │
│   check_alerts.py     │      │   generate_charts.py      │
│   - Absolute checks   │      │   - Line charts (1d/7d/30d)│
│   - Regression detect │      │   - Heatmap               │
│   - 24h cooldown      │      │   - Summary stats         │
│   - WeChat + Email    │      └───────────────────────────┘
└───────────────────────┘                  │
            │                              ▼
            │              ┌───────────────────────────────────────┐
            │              │        Presentation Layer             │
            │              │  ┌─────────────────────────────────┐  │
            │              │  │  docs/                          │  │
            │              │  │  ├── index.md (dashboard)       │  │
            │              │  │  ├── reports/YYYY-MM-DD.md      │  │
            │              │  │  ├── alerts.md                  │  │
            │              │  │  └── assets/charts/*.json       │  │
            │              │  └─────────────────────────────────┘  │
            │              │                                       │
            │              │  MkDocs Material + ECharts            │
            │              └───────────────────────────────────────┘
            │                              │
            ▼                              ▼
    ┌───────────────┐           ┌─────────────────────┐
    │ Notifications │           │  GitHub Pages       │
    │ - WeChat      │           │  (static hosting)   │
    │ - Email SMTP  │           │                     │
    └───────────────┘           └─────────────────────┘
```

### 2.2 架构优点

| 优点 | 说明 |
|------|------|
| **分层清晰** | 数据采集 → 处理 → 存储 → 可视化，职责分离 |
| **无外部依赖** | 完全基于 GitHub 生态，无需维护服务器 |
| **配置驱动** | 新增模型/硬件只需修改 `config.json` |
| **数据分片** | 按日期分片存储，git diff 清晰，避免单文件膨胀 |
| **TDD 规范** | 测试覆盖要求明确（alerting ≥95%，整体 ≥80%）|

### 2.3 架构限制

| 限制 | 影响 | 严重程度 |
|------|------|----------|
| **静态 JSON 存储** | 无法支持动态查询、聚合、过滤 | 中 |
| **GitHub Pages 静态托管** | 无服务端逻辑，所有动态功能需客户端 JS | 中 |
| **90 天保留** | 无法做长期趋势分析（季度/年度） | 低 |
| **单分支追踪** | 仅支持 main 分支 | 低（设计决策）|

---

## 3. 需求符合性分析

### 3.1 功能需求覆盖情况

| PRD 需求 | 状态 | 实现位置 | 备注 |
|----------|------|----------|------|
| **FR-01** repository_dispatch + scheduled fetch | ✅ | `.github/workflows/process-results.yml` | 双路径支持 |
| **FR-02** CI 结果必需字段 | ✅ | `process_results.py:validate_result()` | 强校验 |
| **FR-03** 拒绝非法输入不崩溃 | ✅ | `process_results.py` | 抛异常 + 日志 |
| **FR-04** 单日单硬件单模型快照 | ✅ | `process_results.py:upsert_result()` | 去重逻辑 |
| **FR-05** 90 天数据修剪 | ✅ | `process_results.py:prune_old_data()` | 自动清理 |
| **FR-06** 首页 summary card | ✅ | `docs/index.md` + `generate_charts.py` | Global Health Banner |
| **FR-07** 硬件状态卡片 | ❌ | 未实现 | 仅有 Global Health Banner，无独立硬件状态卡片 |
| **FR-08** Model × Hardware 矩阵 | ✅ | `generate_charts.py:build_heatmap()` | Pass Rate Heatmap |
| **FR-09** 7d/30d 趋势图 | ✅ | `generate_charts.py` + 前端时间选择器 | 已实现 |
| **FR-10** 每日 Markdown 报告 | ✅ | `process_results.py:generate_report()` | 自动生成 |
| **FR-11-13** 绝对阈值告警 | ✅ | `check_alerts.py:check_absolute_thresholds()` | 完整实现 |
| **FR-14** 回归检测 | ✅ | `check_alerts.py:check_regressions()` | 7 天基线 |
| **FR-15** WeChat + Email 通知 | ✅ | `check_alerts.py` | 双通道 |
| **FR-16** 24h 告警冷却 | ✅ | `check_alerts.py:within_cooldown()` | 抑制重复 |
| **FR-17** 告警历史存储 | ✅ | `data/alerts.json` | 持久化 |
| **FR-18-20** 配置驱动扩展 | ✅ | `data/config.json` | 零代码添加 |

### 3.2 非功能需求覆盖情况

| NFR 需求 | 状态 | 验证方式 |
|----------|------|----------|
| **NFR-01** Dashboard < 3s 加载 | ⚠️ | 需实测（静态文件应满足） |
| **NFR-02** 处理 < 5min | ✅ | 简单 Python 脚本，应满足 |
| **NFR-03** < 7 天基线降级 | ✅ | `check_alerts.py:compute_baseline()` 返回空 |
| **NFR-04** 每天数据 < 500KB | ⚠️ | 需监控（25 个快照约 25-50KB） |
| **NFR-05** Alerting 测试 ≥95% | ⚠️ | 需运行 `pytest --cov` 验证 |
| **NFR-06** 整体测试 ≥80% | ⚠️ | 需运行 `pytest --cov` 验证 |
| **NFR-07** GitHub Actions 部署 | ✅ | 工作流已配置 |

---

## 4. 代码质量审视

### 4.1 模块分析

#### `process_results.py` (270 行)

**优点:**
- 清晰的职责分离（验证、去重、修剪、报告生成）
- 良好的错误处理和类型注解
- 支持双数据源（dispatch + schedule）

**风险点:**
- `normalize_results()` 对多种输入格式的容错可能掩盖问题
- 无并发写入保护（多 CI 同时推送可能冲突）

#### `check_alerts.py` (200 行)

**优点:**
- 告警逻辑完整（绝对阈值 + 回归检测）
- 冷却机制防止告警风暴
- 通知抽象清晰，易于扩展

**风险点:**
- `compute_baseline()` 在数据稀疏时可能返回不准确的基线
- Email/WeChat 失败时无重试机制

#### `generate_charts.py` (170 行)

**优点:**
- 预生成多时间窗口图表（1d/7d/30d）
- 图表配置与业务逻辑分离
- Summary 统计复用度高

**风险点:**
- 图表数量随模型/指标线性增长（5 模型 × 4 指标 × 3 窗口 = 60+ JSON 文件）
- 无增量更新机制，每次全量重新生成

### 4.2 数据模型审视

#### `config.json` 结构

```json
{
  "retention_days": 90,
  "hardware": { /* 6 platforms */ },
  "models": { /* 5 models with per-model metrics */ },
  "thresholds": { /* global + regressions */ }
}
```

**优点:**
- 扁平结构，易于理解和扩展
- 支持模型级 `alert_overrides`

**改进建议:**
- 考虑添加 `metadata.version` 用于配置迁移
- 添加 `validation` 规则（如 `pass_rate` 必须在 0-1 之间）

#### 结果数据格式

```json
{
  "date": "2026-03-15",
  "results": [
    { "timestamp", "commit", "hardware", "model", "metrics": { ... } }
  ]
}
```

**优点:**
- 按日期分片，查询效率高
- 嵌套 `metrics` 结构支持分类（stability/performance/accuracy/custom）

**风险点:**
- `metrics` 结构自由度过高，依赖代码层面校验

---

## 5. 安全性审视

### 5.1 Secrets 管理

| Secret | 存储位置 | 风险 |
|--------|----------|------|
| `KANBAN_TOKEN` | GitHub Secrets | ✅ 安全 |
| `RESULTS_SOURCE_URL/TOKEN` | GitHub Secrets | ✅ 安全 |
| `WECHAT_WEBHOOK` | GitHub Secrets | ⚠️ Webhook URL 泄露可被滥用 |
| `EMAIL_SMTP_*` | GitHub Secrets | ✅ 安全 |

**建议:**
- WeChat Webhook 应定期轮换
- 考虑使用 GitHub Environments 分离生产/测试环境

### 5.2 输入校验

| 入口 | 校验 | 风险 |
|------|------|------|
| `repository_dispatch` | `validate_result()` | ✅ Schema 校验 |
| Scheduled fetch | `validate_result()` | ✅ Schema 校验 |
| External source URL | HTTP only | ⚠️ 建议强制 HTTPS |

### 5.3 敏感数据

- **无用户数据**: 系统仅处理 CI 指标，无 PII
- **公开仓库**: GitHub Pages 公开可见，不应包含敏感信息
- **Commit SHA**: 公开可见，但无安全风险

### 5.4 安全建议

| 建议 | 优先级 |
|------|--------|
| 强制 External Source 使用 HTTPS | 高 |
| 定期轮换 WeChat Webhook | 中 |
| 添加 IP 白名单限制（如可能） | 低 |

---

## 6. 依赖分析

### 6.1 Python 依赖 (`requirements.txt`)

| 依赖 | 版本 | 用途 | 风险 |
|------|------|------|------|
| `mkdocs-material` | 未锁定 | 主题 | 低 |
| `mkdocs-macros-plugin` | 未锁定 | 宏支持 | 低 |
| `jsonschema` | 未锁定 | Schema 校验 | 低 |
| `requests` | 未锁定 | HTTP 请求 | 低 |
| `pytest` / `pytest-cov` 等 | 未锁定 | 测试 | 低 |

**问题:**
- **无版本锁定**: 依赖未指定版本，可能导致不一致

**建议:**
```txt
mkdocs-material==9.5.0
mkdocs-macros-plugin==1.0.5
jsonschema==4.21.0
requests==2.31.0
pytest==8.0.0
pytest-cov==4.1.0
```

### 6.2 前端依赖

| 依赖 | 来源 | 风险 |
|------|------|------|
| ECharts 5 | CDN (jsdelivr) | ⚠️ CDN 可用性依赖 |
| MkDocs Material | 内置 | 低 |

**建议:**
- 考虑将 ECharts 打包到本地，避免 CDN 依赖

---

## 7. 前端架构审视

### 7.1 当前实现

- **框架:** MkDocs Material (静态站点生成)
- **图表:** ECharts 5 (CDN 加载)
- **交互:** 纯客户端 JS (`render_charts.js`)
- **样式:** 自定义 CSS (`dashboard.css`)

### 7.2 优点

| 优点 | 说明 |
|------|------|
| **零构建** | 无需 Webpack/Vite，简单直接 |
| **CDN 加速** | ECharts 从 CDN 加载，减少包体积 |
| **时间范围选择器** | 已实现，支持 1d/7d/30d 切换 |
| **Dark Mode** | MkDocs Material 原生支持 |
| **响应式布局** | Material 主题自适应 |

### 7.3 改进空间

| 问题 | 建议 | 优先级 |
|------|------|--------|
| **图表过多** | 按需加载 / 懒加载 | 中 |
| **无缓存策略** | 添加版本号或 hash 到 JSON URL | 低 |
| **无错误边界** | 图表加载失败时显示友好提示 | 中 |
| **无数据时体验** | 空数据状态应显示占位符而非空白图表 | 中 |

---

## 8. 待解决问题

### 8.1 Open Questions (from PRD)

| # | 问题 | 状态 | 建议 |
|---|------|------|------|
| 1 | GitHub Pages 是否私有？ | Open | 如需私有，需 GitHub Enterprise |
| 2 | CI payload 大小限制 | Answered | 单次推送，已通过 scheduled fetch 解决 |
| 3 | benchmark_score 阈值全局 or 模型级？ | Open | 建议在 `alert_overrides` 中配置 |
| 4 | Webhook/SMTP 凭据归属 | Open | 文档化到 `contributing.md` |

### 8.2 架构债务

| 债务 | 影响 | 建议 |
|------|------|------|
| **静态 JSON 查询限制** | 无法支持复杂过滤、聚合 | 长期考虑 FastAPI 后端 |
| **无并发写入保护** | 多 CI 同时推送可能数据丢失 | 添加文件锁或队列机制 |
| **图表文件数量爆炸** | 随模型/指标增长，JSON 文件数量失控 | 按需生成 or 合并到单一 JSON |
| **无重试机制** | 通知失败后无补救 | 添加失败队列和重试逻辑 |

---

## 9. 优化建议

### 9.1 短期（Quick Wins）

| 建议 | 工作量 | 影响 |
|------|--------|------|
| 添加空数据状态 UI | S | 用户体验提升 |
| 图表加载失败提示 | S | 错误处理完善 |
| 配置版本控制 | S | 配置迁移友好 |
| 告警通知重试 | S | 可靠性提升 |
| 锁定 Python 依赖版本 | S | 构建一致性 |
| **实现 FR-07 硬件状态卡片** | M | PRD 完整性 |

### 9.2 中期（架构增强）

| 建议 | 工作量 | 影响 |
|------|--------|------|
| 图表按需生成 | M | 减少构建时间和存储 |
| 并发写入保护 | M | 数据一致性保障 |
| DuckDB 历史数据归档 | L | 支持长期趋势分析 |
| API 层抽象 | L | 为 FastAPI 迁移做准备 |

### 9.3 长期（架构演进）

| 建议 | 工作量 | 影响 |
|------|--------|------|
| FastAPI 后端 | XL | 支持动态查询、过滤、聚合 |
| 数据库存储 | XL | 替代静态 JSON，支持复杂查询 |
| 实时推送 | L | WebSocket 支持，减少轮询 |

> **工作量说明:** S = < 4h, M = 1-2 days, L = 3-5 days, XL = > 5 days

---

## 10. 结论

vLLM-Omni Kanban 是一个架构合理、需求覆盖度高的监控系统。核心优势在于：

1. **零外部依赖**：完全基于 GitHub 生态
2. **配置驱动**：扩展性极强
3. **TDD 规范**：测试覆盖要求明确

主要改进方向：

1. **FR-07 未实现** → 需添加硬件状态卡片
2. **静态 JSON 的限制** → 长期考虑 API 后端
3. **前端体验优化** → 空数据处理、错误边界
4. **可靠性增强** → 通知重试、并发保护
5. **依赖版本锁定** → 确保构建一致性

---

**Next Steps:**
1. 确认 Open Questions 的决策
2. 评估测试覆盖是否达标
3. 实现缺失的 FR-07 硬件状态卡片
4. 决定是否启动中期优化项
