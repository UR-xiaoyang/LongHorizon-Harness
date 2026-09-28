# LongHorizon-Harness MCP 集成指南

## 概述

LongHorizon-Harness 现在可以作为 MCP (Model Context Protocol) 服务器运行，让 Claude Code、Codex 等工具调用其长期任务管理能力。

## 快速开始

### 1. 启动 MCP Server

```bash
lh-harness mcp-server
```

默认使用 stdio 传输，可以被 MCP 客户端直接调用。

### 2. 配置 Claude Code

在 `~/.claude.json` 或项目的 `.mcp.json` 中添加：

```json
{
  "mcpServers": {
    "longhorizon-harness": {
      "command": "lh-harness",
      "args": ["mcp-server"],
      "env": {
        "LH_HARNESS_CONFIG": "./.lh-harness/config.toml"
      }
    }
  }
}
```

### 3. 配置 Codex

在 `~/.codex/config.toml` 中添加：

```toml
[mcp_servers.longhorizon-harness]
command = "lh-harness"
args = ["mcp-server"]

[mcp_servers.longhorizon-harness.env]
LH_HARNESS_CONFIG = "./.lh-harness/config.toml"
```

## 可用工具

### lh_start_task - 启动长期任务

启动一个新的多轮任务。

**参数：**
- `goal` (string, 必需): 任务目标描述
- `workspace` (string, 必需): 工作目录路径
- `max_rounds` (integer, 可选): 最大执行轮数，默认 25
- `config` (object, 可选): 配置覆盖

**返回：**
```json
{
  "success": true,
  "task_id": "task_abc123def456",
  "status": "started",
  "initial_plan": "Task started: ...",
  "workspace": "./my-project",
  "max_rounds": 25
}
```

### lh_get_task_status - 查询任务状态

获取任务的当前状态和进度。

**参数：**
- `task_id` (string, 必需): 任务ID

**返回：**
```json
{
  "success": true,
  "task_id": "task_abc123def456",
  "status": "running",
  "current_round": 5,
  "total_rounds": 25,
  "verified_progress": "已完成并验证的工作内容",
  "current_step": "当前正在执行的步骤",
  "next_action": "下一步计划"
}
```

### lh_execute_round - 执行一轮循环

执行一轮 Manager 规划 → Executor 执行 → Auditor 验证的完整循环。

**参数：**
- `task_id` (string, 必需): 任务ID
- `user_input` (string, 可选): 用户指令或反馈

**返回：**
```json
{
  "success": true,
  "round_id": "task_abc123def456_r1",
  "plan": "本轮执行计划...",
  "execution_result": "执行结果...",
  "audit_report": "审计报告...",
  "status": "complete",
  "checkpoint": { "round": 1, "verified": true },
  "duration_ms": 45000
}
```

### lh_get_checkpoint - 获取检查点

获取最新的已验证状态快照。

**参数：**
- `task_id` (string, 必需): 任务ID

**返回：**
```json
{
  "success": true,
  "checkpoint_id": "task_abc123def456_cp3",
  "verified_state": "已验证的任务状态描述",
  "completed_items": ["已完成项1", "已完成项2"],
  "artifacts": ["output/file1.txt", "output/file2.json"],
  "timestamp": "2025-01-15T10:30:00Z"
}
```

### lh_recover_task - 恢复任务

从最近的 checkpoint 恢复任务执行。

**参数：**
- `task_id` (string, 必需): 任务ID
- `checkpoint_id` (string, 可选): 特定 checkpoint ID

**返回：**
```json
{
  "success": true,
  "recovered_state": "已验证的任务状态",
  "next_plan": "恢复后的执行计划",
  "checkpoint_id": "task_abc123def456_cp3"
}
```

### lh_pause_task - 暂停任务

暂停正在运行的任务。

**参数：**
- `task_id` (string, 必需): 任务ID

### lh_stop_task - 停止任务

停止任务并清理资源。

**参数：**
- `task_id` (string, 必需): 任务ID
- `keep_artifacts` (boolean, 可选): 是否保留产出文件，默认 true

### lh_inject_feedback - 注入反馈

向运行中的任务注入人工反馈。

**参数：**
- `task_id` (string, 必需): 任务ID
- `feedback` (string, 必需): 反馈内容
- `type` (string, 必需): 反馈类型，可选值：
  - `"correction"`: 纠正错误
  - `"guidance"`: 提供指导
  - `"approval"`: 批准继续

### lh_get_audit_trail - 获取审计轨迹

获取任务的完整执行和验证历史。

**参数：**
- `task_id` (string, 必需): 任务ID

**返回：**
```json
{
  "success": true,
  "task_id": "task_abc123def456",
  "goal": "任务目标",
  "status": "completed",
  "total_rounds": 8,
  "rounds": [...],
  "checkpoints": [...],
  "feedbacks": [...]
}
```

## 使用示例

### 示例 1：在 Claude Code 中启动长期任务

```
用户: 请帮我开发一个完整的博客系统，包括前端、后端和数据库

Claude Code: 这是一个复杂的长期任务，我会使用 LongHorizon-Harness 来管理。

[调用 lh_start_task]
{
  "goal": "开发完整博客系统：React前端 + FastAPI后端 + PostgreSQL数据库",
  "workspace": "./blog-system",
  "max_rounds": 30
}

[返回]
任务已启动，task_id: task_abc123def456

[调用 lh_execute_round] 
执行第1轮：
- Manager 规划：创建项目结构
- Executor 执行：创建目录和初始配置文件
- Auditor 验证：确认结构正确

[调用 lh_get_task_status]
当前进度：已完成项目初始化，接下来实现后端API
```

### 示例 2：暂停和恢复任务

```
用户: 先暂停，我需要调整需求

Claude Code: 好的，我会暂停任务。

[调用 lh_pause_task]
任务已暂停

[调用 lh_get_checkpoint]
当前已完成：
- 项目结构创建
- 后端基础框架搭建
- 数据库模型定义

--- 稍后 ---

用户: 继续，但是把PostgreSQL改成MySQL

Claude Code: 好的，我会注入修正并继续任务。

[调用 lh_inject_feedback]
{
  "task_id": "task_abc123def456",
  "feedback": "数据库由PostgreSQL改为MySQL",
  "type": "correction"
}

[调用 lh_recover_task]
任务已恢复

[调用 lh_execute_round]
继续执行，应用了数据库修改...
```

### 示例 3：查看完整审计轨迹

```
用户: 显示这个任务的完整执行历史

Claude Code:
[调用 lh_get_audit_trail]

任务执行历史：
- 第1轮：项目结构创建 ✓
- 第2轮：后端框架搭建 ✓
- 第3轮：数据库模型定义 ✓
- 第4轮：API接口实现 ✓ (有1条修正反馈)
- 第5轮：前端初始化 ✓
...
```

## 工作流程

```
1. Claude Code 接收用户任务
   ↓
2. 判断是否为长期复杂任务
   ↓
3. 调用 lh_start_task 启动任务
   ↓
4. 循环执行：
   - 调用 lh_execute_round
   - 获取 plan/execution/audit 结果
   - 向用户报告进度
   ↓
5. 任务完成或需要暂停时：
   - lh_pause_task / lh_stop_task
   - lh_get_checkpoint 保存状态
```

## 优势

1. **职责分离**：Claude Code 负责对话和决策，LongHorizon-Harness 负责任务执行管理
2. **状态持久化**：任务状态通过 checkpoint 机制持久化，可随时暂停和恢复
3. **独立验证**：Auditor 角色独立验证执行结果，确保质量
4. **灵活集成**：任何支持 MCP 的工具都可以使用
5. **透明可控**：完整的审计轨迹，用户可以随时查看和干预

## 开发状态

当前实现状态：

- ✅ MCP Server 基础框架
- ✅ 9个核心工具定义
- ✅ 任务生命周期管理
- ✅ Checkpoint 机制
- ✅ 反馈注入
- ⏳ 与现有 Manager/Executor/Auditor 集成（TODO）
- ⏳ HTTP 传输支持（TODO）
- ⏳ MCP Resources 实现（TODO）

## 下一步开发

1. 集成现有的 Manager/Executor/Auditor 逻辑到 `task_manager.execute_round()`
2. 实现完整的 checkpoint 序列化和恢复
3. 添加 MCP Resources 支持（任务状态、轮次历史等）
4. 编写集成测试
5. 完善文档和使用示例

## 贡献

欢迎贡献代码、报告问题或提出建议！

仓库：https://github.com/AMAP-ML/LongHorizon-Harness
