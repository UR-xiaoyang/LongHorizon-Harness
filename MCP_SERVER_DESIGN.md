# LongHorizon-Harness MCP Server 设计方案

## 概述

将LongHorizon-Harness改造为MCP (Model Context Protocol) 服务器，使其可以被Claude Code等主agent工具调用，提供长期任务的规划、执行、验证和checkpoint能力。

## 架构转换

### Before (当前架构)
```
┌─────────────────────────────────┐
│   LongHorizon-Harness (主控)    │
│  - Task State Management        │
│  - Manager/Executor/Auditor     │
│  - Checkpoint & Recovery        │
└──────────────┬──────────────────┘
               │ 调用
               ▼
┌─────────────────────────────────┐
│  Claude Code / Codex (工具)     │
│  - 执行具体操作                  │
└─────────────────────────────────┘
```

### After (MCP架构)
```
┌─────────────────────────────────┐
│    Claude Code (主Agent)        │
│  - 接收用户任务                  │
│  - 决策调用哪个MCP工具           │
└──────────────┬──────────────────┘
               │ MCP Protocol
               ▼
┌─────────────────────────────────┐
│  LongHorizon-Harness MCP Server │
│  - 提供长期任务管理能力          │
│  - Plan-Act-Verify循环           │
│  - State Checkpoint              │
└─────────────────────────────────┘
```

## MCP Tools 设计

### 1. 核心工具集

#### `lh_start_task`
启动一个长期任务，返回task_id
```json
{
  "name": "lh_start_task",
  "description": "启动一个需要多轮plan-act-verify循环的长期任务",
  "parameters": {
    "goal": "任务目标描述",
    "workspace": "工作目录路径",
    "max_rounds": "最大执行轮数 (默认25)",
    "config": "可选的配置覆盖"
  },
  "returns": {
    "task_id": "任务唯一标识",
    "status": "started",
    "initial_plan": "初始执行计划"
  }
}
```

#### `lh_get_task_status`
查询任务当前状态
```json
{
  "name": "lh_get_task_status",
  "description": "获取长期任务的当前状态和进度",
  "parameters": {
    "task_id": "任务ID"
  },
  "returns": {
    "status": "running|paused|completed|failed",
    "current_round": 5,
    "total_rounds": 25,
    "verified_progress": "已完成并验证的工作",
    "current_step": "当前正在执行的步骤",
    "next_action": "下一步计划"
  }
}
```

#### `lh_execute_round`
执行一轮plan-act-verify循环
```json
{
  "name": "lh_execute_round",
  "description": "执行一轮Manager规划→Executor执行→Auditor验证的循环",
  "parameters": {
    "task_id": "任务ID",
    "user_input": "可选的用户指令或反馈"
  },
  "returns": {
    "round_id": "本轮ID",
    "plan": "Manager的执行计划",
    "execution_result": "Executor的执行结果",
    "audit_report": "Auditor的验证报告",
    "status": "complete|incomplete|blocked",
    "checkpoint": "验证通过的状态快照"
  }
}
```

#### `lh_get_checkpoint`
获取最新的验证状态
```json
{
  "name": "lh_get_checkpoint",
  "description": "获取任务最新的已验证状态快照",
  "parameters": {
    "task_id": "任务ID"
  },
  "returns": {
    "checkpoint_id": "checkpoint标识",
    "verified_state": "已验证的任务状态",
    "completed_items": ["已完成项列表"],
    "artifacts": ["产出的文件列表"],
    "timestamp": "checkpoint时间"
  }
}
```

#### `lh_recover_task`
从checkpoint恢复任务
```json
{
  "name": "lh_recover_task",
  "description": "从最近的checkpoint恢复任务执行",
  "parameters": {
    "task_id": "任务ID",
    "checkpoint_id": "可选的特定checkpoint"
  },
  "returns": {
    "recovered_state": "恢复的状态",
    "next_plan": "恢复后的执行计划"
  }
}
```

#### `lh_pause_task`
暂停任务并保存状态
```json
{
  "name": "lh_pause_task",
  "description": "暂停长期任务，保存当前状态以便后续恢复",
  "parameters": {
    "task_id": "任务ID"
  }
}
```

#### `lh_stop_task`
停止并清理任务
```json
{
  "name": "lh_stop_task",
  "description": "停止任务执行并清理资源",
  "parameters": {
    "task_id": "任务ID",
    "keep_artifacts": "是否保留产出文件"
  }
}
```

### 2. 高级工具集

#### `lh_validate_progress`
独立验证当前进度
```json
{
  "name": "lh_validate_progress",
  "description": "使用Auditor角色独立验证当前工作成果",
  "parameters": {
    "task_id": "任务ID",
    "validation_criteria": "验证标准"
  }
}
```

#### `lh_get_audit_trail`
获取完整审计轨迹
```json
{
  "name": "lh_get_audit_trail",
  "description": "获取任务的完整执行和验证历史",
  "parameters": {
    "task_id": "任务ID",
    "include_details": true
  }
}
```

#### `lh_inject_feedback`
注入人工反馈
```json
{
  "name": "lh_inject_feedback",
  "description": "向正在运行的任务注入人工反馈或修正",
  "parameters": {
    "task_id": "任务ID",
    "feedback": "反馈内容",
    "type": "correction|guidance|approval"
  }
}
```

## MCP Resources 设计

### 任务状态资源
```
lh://task/{task_id}/state
- 任务的当前完整状态

lh://task/{task_id}/checkpoint/latest
- 最新的验证状态快照

lh://task/{task_id}/rounds
- 所有执行轮次的列表

lh://task/{task_id}/rounds/{round_id}
- 特定轮次的详细信息
```

## 实现路径

### 阶段1：核心MCP Server
1. 创建 `src/lh_harness/mcp_server/` 模块
2. 实现基础MCP协议处理
3. 封装现有的Manager/Executor/Auditor逻辑为可调用服务
4. 实现任务状态管理和持久化

### 阶段2：工具实现
1. 实现7个核心tools
2. 添加任务生命周期管理
3. 实现checkpoint机制的MCP接口

### 阶段3：资源实现
1. 实现任务状态resources
2. 添加历史轮次查询能力

### 阶段4：集成测试
1. 编写MCP server测试
2. 与Claude Code集成测试
3. 编写使用示例和文档

## 使用场景示例

### 场景1：Claude Code调用进行长期任务

```python
# Claude Code中的对话
User: "请帮我开发一个完整的Web应用，包括前端、后端和部署"

Claude Code (思考):
这是一个需要多步骤、多验证的长期任务，适合使用LongHorizon-Harness

# 调用MCP tool
task = lh_start_task(
    goal="开发完整Web应用：React前端 + FastAPI后端 + Docker部署",
    workspace="./my-web-app",
    max_rounds=30
)

# 执行第一轮
round1 = lh_execute_round(task_id=task.task_id)
# Manager规划 → 创建项目结构
# Executor执行 → 创建目录和配置文件
# Auditor验证 → 确认结构正确

# 检查进度
status = lh_get_task_status(task_id=task.task_id)
# 向用户报告：已完成项目结构创建，接下来实现后端API

# 继续执行
round2 = lh_execute_round(task_id=task.task_id)
# ...
```

### 场景2：暂停和恢复

```python
# 用户需要暂停
User: "先暂停，我需要调整需求"

lh_pause_task(task_id=task.task_id)

# 获取当前checkpoint
checkpoint = lh_get_checkpoint(task_id=task.task_id)
# 向用户展示已完成的工作

# 稍后恢复
User: "继续刚才的任务，但是后端改用Django"

lh_recover_task(task_id=task.task_id)
lh_inject_feedback(
    task_id=task.task_id,
    feedback="后端框架改为Django而非FastAPI",
    type="correction"
)
lh_execute_round(task_id=task.task_id)
```

## 技术栈

- **MCP SDK**: `@modelcontextprotocol/sdk` (TypeScript) 或 Python实现
- **通信**: stdio 或 HTTP SSE
- **状态存储**: 现有的 `.lh-harness/runs/` 结构
- **任务队列**: 内存队列 + 文件持久化

## 配置集成

### Claude Code配置
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

### Codex配置
在 `~/.codex/config.toml` 中添加：

```toml
[mcp_servers.longhorizon-harness]
command = "lh-harness"
args = ["mcp-server"]

[mcp_servers.longhorizon-harness.env]
LH_HARNESS_CONFIG = "./.lh-harness/config.toml"
```

## 优势

1. **架构清晰**: Claude Code负责对话和决策，LongHorizon-Harness负责长期任务管理
2. **灵活集成**: 任何支持MCP的工具都可以使用
3. **渐进增强**: Claude Code可以选择性使用LongHorizon能力
4. **保留核心价值**: Plan-Act-Verify循环和checkpoint机制完整保留
5. **降低侵入性**: 不需要修改Claude Code本身

## 下一步

1. 创建 `src/lh_harness/mcp_server/` 目录结构
2. 实现MCP协议处理器
3. 封装现有逻辑为service层
4. 编写集成测试
5. 更新文档和使用示例
