# LongHorizon-Harness MCP 架构重新设计

## 🎯 设计理念转变

### 旧设计（错误）
```
LongHorizon-Harness = 独立的自主任务系统
Claude = 只是启动和监控
```

### 新设计（正确）
```
Claude = 主控智能体（决策者）
LongHorizon-Harness = 工具集（执行者 + 验证者）
```

## 🏗️ 新架构

### 核心理念
**LongHorizon-Harness 是 Claude 的"长期记忆 + 验证助手"**

```
┌─────────────────────────────────────┐
│         Claude (主控智能体)          │
│  - 理解用户需求                      │
│  - 分解任务                          │
│  - 规划每一步                        │
│  - 分析执行结果                      │
│  - 决定下一步动作                    │
└──────────────┬──────────────────────┘
               │
               │ MCP Protocol
               │
┌──────────────▼──────────────────────┐
│   LongHorizon-Harness (工具集)      │
│                                      │
│  📝 State Manager                   │
│     - 持久化任务状态                 │
│     - 记录历史轮次                   │
│     - Checkpoint 管理               │
│                                      │
│  ⚙️ Executor Agent                  │
│     - 执行具体操作                   │
│     - 操作文件系统                   │
│     - 运行命令                       │
│                                      │
│  ✅ Auditor Agent                   │
│     - 验证执行结果                   │
│     - 检查完整性                     │
│     - 生成审计报告                   │
│                                      │
│  🔍 Inspector Tools                 │
│     - 查看历史                       │
│     - 搜索日志                       │
│     - 诊断问题                       │
└─────────────────────────────────────┘
```

## 📋 新的工具设计

### 第一层：核心执行工具（4个）

#### 1. `lh_execute`
**描述**: 执行一个具体的操作并返回结果

```python
{
  "action": "create_file",  # 或 run_command, modify_file 等
  "params": {
    "path": "src/main.py",
    "content": "print('hello')"
  },
  "workspace": "./project"
}

# 返回
{
  "success": true,
  "result": "文件已创建",
  "files_changed": ["src/main.py"],
  "verification_needed": true
}
```

#### 2. `lh_verify`
**描述**: 独立验证上一步操作的结果

```python
{
  "execution_id": "exec_123",
  "verification_goals": [
    "文件存在",
    "语法正确",
    "可以运行"
  ]
}

# 返回
{
  "verified": true,
  "integrity": "clean",
  "issues": [],
  "audit_report": "✅ 所有检查通过"
}
```

#### 3. `lh_inspect`
**描述**: 检查当前状态（不执行任何操作）

```python
{
  "target": "workspace",  # 或 file, command_output 等
  "workspace": "./project"
}

# 返回
{
  "files": ["src/main.py", "README.md"],
  "structure": {...},
  "current_state": "..."
}
```

#### 4. `lh_rollback`
**描述**: 回滚到之前的 checkpoint

```python
{
  "checkpoint_id": "cp_5"
}

# 返回
{
  "success": true,
  "restored_to": "第5个检查点",
  "changes_undone": [...]
}
```

### 第二层：状态管理工具（5个）

#### 5. `lh_save_checkpoint`
**描述**: 手动保存当前状态为检查点

```python
{
  "label": "完成前端框架搭建",
  "note": "React + TypeScript 项目创建完成"
}
```

#### 6. `lh_list_checkpoints`
**描述**: 列出所有检查点

#### 7. `lh_get_history`
**描述**: 获取执行历史

```python
{
  "limit": 10,
  "filter": "failed"  # 可选：只看失败的
}

# 返回所有执行记录
```

#### 8. `lh_search_history`
**描述**: 在执行历史中搜索

```python
{
  "query": "npm install",
  "search_in": "commands"  # 或 results, errors
}
```

#### 9. `lh_get_metrics`
**描述**: 获取统计信息

```python
# 返回
{
  "total_executions": 25,
  "successful": 23,
  "failed": 2,
  "total_files_changed": 50
}
```

### 第三层：工作空间管理（3个）

#### 10. `lh_init_workspace`
**描述**: 初始化工作空间

```python
{
  "path": "./my-project",
  "git_init": true
}
```

#### 11. `lh_get_workspace_state`
**描述**: 获取工作空间完整状态

#### 12. `lh_cleanup_workspace`
**描述**: 清理临时文件

## 🔄 工作流示例

### 场景：开发一个 Web 应用

```python
# 用户请求
User: "帮我开发一个博客系统，React前端 + FastAPI后端"

# Claude 的思考和执行流程：

# 第1步：初始化工作空间
Claude: "我先创建项目结构"
→ lh_init_workspace(path="./blog-system")

# 第2步：创建前端
Claude: "创建 React 前端"
→ lh_execute(action="run_command", params={
    "command": "npx create-react-app frontend"
  })
→ 等待返回
→ lh_verify(verification_goals=["React项目创建成功"])
→ lh_save_checkpoint(label="前端框架创建完成")

# 第3步：创建后端
Claude: "创建 FastAPI 后端"
→ lh_execute(action="run_command", params={
    "command": "mkdir backend && cd backend && python -m venv venv"
  })
→ lh_verify(...)
→ lh_save_checkpoint(label="后端环境创建完成")

# 第4步：如果出错
Claude: "让我检查一下刚才的执行"
→ lh_get_history(limit=5)
→ 发现问题
→ lh_rollback(checkpoint_id="cp_2")
→ 重新执行

# 循环直到完成...
```

## 🎯 核心优势

### 1. Claude 完全掌控
- 每一步都由 Claude 决定
- Claude 能看到所有执行结果
- Claude 能随时调整策略

### 2. 长期任务能力
- 状态持久化（跨对话）
- Checkpoint 机制（可回滚）
- 完整历史记录（可追溯）

### 3. 独立验证
- Auditor 独立检查
- 不信任 Executor 的输出
- 发现伪造或错误

### 4. 灵活应对
- 出错时可回滚
- 可查看历史找原因
- 可修改策略继续

## 📊 对比

| 维度 | 旧设计 | 新设计 |
|-----|--------|--------|
| **决策者** | LH-Harness 内部 Manager | Claude |
| **Claude 的角色** | 监控者 | 主控者 |
| **工具数量** | 23个（复杂） | 12个（简洁） |
| **交互方式** | 轮次自动执行 | 每步手动决策 |
| **灵活性** | 低（预设流程） | 高（动态调整） |
| **可见性** | 低（黑盒） | 高（白盒） |

## 🚀 实现计划

### Phase 1: 核心执行（优先）
- [x] lh_execute - 执行操作
- [x] lh_verify - 验证结果
- [x] lh_inspect - 检查状态
- [x] lh_rollback - 回滚

### Phase 2: 状态管理
- [x] lh_save_checkpoint
- [x] lh_list_checkpoints
- [x] lh_get_history
- [x] lh_search_history
- [x] lh_get_metrics

### Phase 3: 工作空间
- [x] lh_init_workspace
- [x] lh_get_workspace_state
- [x] lh_cleanup_workspace

## 💡 关键洞察

**LongHorizon-Harness 不是替代 Claude，而是增强 Claude**

- Claude = 大脑（智能、决策、规划）
- LH-Harness = 手脚（执行、验证、记忆）

这样才能真正发挥"人机协同"的最大价值！
