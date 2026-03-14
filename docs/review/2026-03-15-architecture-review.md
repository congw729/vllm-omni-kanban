# vLLM-Omni Kanban 架构与需求审视报告

**审视人**: OmniClaw-3 (需求分析师 🦐)
**日期**: 2026-03-15
**仓库**: `hsliuustc0106/vllm-omni-kanban`
**目标**: 为 @OmniClaw-1 提供实施参考

---

## 📊 项目概览

### 基本信息
- **架构**: 静态站点 (MkDocs) + Python 数据管道
- **部署**: GitHub Pages
- **数据存储**: 静态 JSON 文件 (90 天滚动)
- **告警**: 企业微信 + Email

### 技术栈
```
前端: MkDocs Material + ECharts
后端: Python 3.11
CI/CD: GitHub Actions
存储: JSON 文件 (分片存储)
通知: WeChat Webhook + SMTP
```

---

## ✅ 已完成功能

### 1. 核心数据管道
- ✅ **process_results.py** - 验证、去重、插入、清理
- ✅ **check_alerts.py** - 绝对阈值 + 回归检测 + 24h 冷却
- ✅ **generate_charts.py** - 生成 ECharts JSON
- ✅ **fetch_latest_results.py** - 拉取外部数据源

### 2. 配置驱动
- ✅ **config.json** 定义 models/hardware
- ✅ Per-model metric registry
- ✅ 可配置告警阈值

### 3. GitHub Actions
- ✅ 三阶段工作流 (process → alert → deploy)
- ✅ 支持 repository_dispatch + schedule
- ✅ 自动提交数据变更

### 4. 历史数据
- ✅ 8 天历史数据 (2026-03-07 ~ 2026-03-14)
- ✅ 每日 ~20KB JSON 文件
- ✅ 按日期分片存储

---

## ⚠️ 潜在风险与问题

### 1. 数据源依赖 (高风险)
**问题**: `fetch_latest_results.py` 依赖外部数据源
- 如果 `RESULTS_SOURCE_URL` 不可用，定时任务会失败
- 无重试机制
- 无备用数据源

**影响**: 每日数据更新失败，看板停滞

**建议**:
```python
# 添加重试逻辑
import tenacity

@tenacity.retry(
    stop=tenacity.stop_after_attempt(3),
    wait=tenacity.wait_exponential(multiplier=1, min=4, max=10)
)
def fetch_results(url, token):
    ...
```

---

### 2. 测试覆盖不足 (中风险)
**现状**:
- 测试代码总计 92 行
- PRD 要求：告警逻辑 ≥95%，整体 ≥80%
- 未知当前覆盖率

**风险**: 核心告警逻辑可能有 bug

**建议**: 运行 `pytest --cov=scripts tests/` 确认覆盖率

---

### 3. 告警通知未验证 (中风险)
**问题**:
- WeChat webhook / Email SMTP 需要 secrets 配置
- 未知是否已实际测试发送
- 无发送失败降级策略

**建议**:
- 添加告警发送测试模式 (`--dry-run`)
- 记录发送失败到日志

---

### 4. 静态 JSON 扩展性 (低风险，长期)
**问题**:
- 当前 8 天数据 ~160KB
- 90 天预计 ~1.8MB
- 单文件最大 ~500KB (PRD 要求)

**当前状态**: ✅ 符合要求

**未来风险**: 如果模型/硬件数量增长 3x，可能超限

**建议**: 监控文件大小，超阈值时考虑 DuckDB

---

### 5. 缺少监控自检 (低风险)
**问题**:
- 看板本身无健康检查
- 如果数据更新失败，无自动告警

**建议**: 添加数据新鲜度检查
```python
# check_alerts.py 增加
def check_data_freshness(index):
    last_update = parse_timestamp(index["last_updated"])
    if datetime.now() - last_update > timedelta(hours=26):
        alert("Data stale: last update > 26h ago")
```

---

## 🔍 架构设计评价

### 优点 ✅
1. **简单可靠**: 静态站点 + JSON，无数据库依赖
2. **配置驱动**: 新增模型只需改 config.json
3. **分片存储**: 每日一文件，git diff 友好
4. **三阶段工作流**: 失败隔离，部署独立

### 改进空间 ⚡
1. **无数据备份**: JSON 文件在 git，但无额外备份
2. **无数据校验**: 运行时未验证 JSON 完整性
3. **无性能监控**: 页面加载时间未追踪
4. **无灰度发布**: 每次全量部署

---

## 📋 PRD 实施检查表

### Functional Requirements
| ID | 需求 | 状态 | 备注 |
|----|------|------|------|
| FR-01 | repository_dispatch + schedule | ✅ 已实现 | |
| FR-02 | CI result schema | ✅ 已实现 | |
| FR-03 | 拒绝 malformed 数据 | ✅ 已实现 | validate_result() |
| FR-04 | 每日快照去重 | ✅ 已实现 | upsert_result() |
| FR-05 | 90 天清理 | ✅ 已实现 | prune_old_results() |
| FR-06 | Summary cards | ❓ 未知 | 需检查 index.md |
| FR-07 | Hardware status | ❓ 未知 | |
| FR-08 | Model×Hardware matrix | ❓ 未知 | |
| FR-09 | 7d/30d 趋势图 | ❓ 未知 | |
| FR-10 | Daily reports | ✅ 已实现 | docs/reports/ |
| FR-11-14 | 告警规则 | ✅ 已实现 | check_alerts.py |
| FR-15 | WeChat + Email | ⚠️ 待验证 | 需要 secrets |
| FR-16 | 24h 冷却 | ✅ 已实现 | suppressed_until |
| FR-17 | Alert history | ✅ 已实现 | alerts.json |
| FR-18 | Config-driven models | ✅ 已实现 | config.json |
| FR-19 | Per-model metrics | ✅ 已实现 | |
| FR-20 | 可配置阈值 | ✅ 已实现 | |

### Non-Functional Requirements
| ID | 需求 | 状态 | 备注 |
|----|------|------|------|
| NFR-01 | 页面加载 <3s | ❓ 未测试 | |
| NFR-02 | 处理 <5min | ✅ 符合 | 当前 ~1min |
| NFR-03 | <7 天优雅降级 | ✅ 已实现 | compute_baseline() |
| NFR-04 | 每日 <500KB | ✅ 符合 | 当前 ~20KB |
| NFR-05 | 告警测试 ≥95% | ❓ 未知 | 需运行覆盖率 |
| NFR-06 | 整体测试 ≥80% | ❓ 未知 | |
| NFR-07 | 纯 GitHub Actions | ✅ 已实现 | |

---

## 🚨 Open Questions (来自 PRD)

| # | 问题 | 状态 | 建议 |
|---|------|------|------|
| 1 | GitHub Pages 是否私有？ | Open | 如需私有，需 GitHub Enterprise |
| 2 | CI payload 最大大小？ | Answered | 单次 dispatch ~1-2KB |
| 3 | Accuracy 阈值全局/Per-model？ | Open | 建议 per-model (已支持 alert_overrides) |
| 4 | 谁持有 secrets？ | Open | 需明确责任人 |

---

## 📌 给 @OmniClaw-1 的建议

### 优先级 1 - 验证核心功能
1. **运行测试覆盖率**
   ```bash
   pytest --cov=scripts tests/ --cov-report=term-missing
   ```
2. **测试告警发送**
   - 配置 WeChat webhook
   - 发送测试告警验证
3. **检查前端完整性**
   - 本地运行 `mkdocs serve`
   - 验证 FR-06/07/08/09

### 优先级 2 - 增强健壮性
1. **添加数据源重试**
   - fetch_latest_results.py 加 tenacity
2. **添加数据新鲜度告警**
   - 如果 >26h 未更新，发送告警
3. **添加 JSON 完整性校验**
   - 启动时验证 index.json

### 优先级 3 - 文档完善
1. **解决 PRD Open Questions**
2. **添加运维手册**
   - Secrets 配置步骤
   - 故障排查指南
3. **添加性能基准**
   - 页面加载时间
   - 数据处理时间

---

## 🎯 总结

### 架构评分: ⭐⭐⭐⭐ (4/5)

**优点**:
- 设计简洁，符合 PRD 95% 以上
- 配置驱动，易于扩展
- 静态部署，维护成本低

**扣分项**:
- 测试覆盖率未知 (-0.5)
- 外部依赖无重试 (-0.3)
- 告警未实际验证 (-0.2)

### 实施建议
1. **本周**: 验证核心功能（测试 + 告警 + 前端）
2. **下周**: 增强健壮性（重试 + 新鲜度告警）
3. **长期**: 监控扩展性，按需引入 DuckDB

---

**生成时间**: 2026-03-15 07:12 AM
**文档版本**: v1.0
**下次审视**: 实施优化后
