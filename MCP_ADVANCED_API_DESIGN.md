# LongHorizon-Harness MCP 高级 API 设计

## 问题分析

当前基础 API 的局限：
- ❌ 无法修改已执行的轮次
- ❌ 无法编辑任务配置
- ❌ 无法查看/修改对话日志
- ❌ 无法回滚到特定状态
- ❌ 无法调试执行细节
- ❌ 无法手动干预执行流程

这意味着如果任务执行出错或需要调整，用户只能：
1. 停止任务重新开始（丢失进度）
2. 注入反馈继续（但无法修正已有错误）

## 高级 API 设计

### 1. 任务配置管理

#### `lh_get_task_config`
获取任务的完整配置

```json
{
  "name": "lh_get_task_config",
  "description": "获取任务的完整配置信息，包括工作区、模型、超时等",
  "parameters": {
    "task_id": "任务ID"
  },
  "returns": {
    "task_id": "task_abc123",
    "goal": "原始任务目标",
    "workspace": "./project",
    "max_rounds": 25,
    "current_config": {
      "manager_model": "claude-opus-5",
      "executor_model": "gpt-5.6-sol",
      "auditor_model": "claude-opus-5",
      "timeouts": {
        "manager": 600,
        "executor": 1800,
        "auditor": 600
      },
      "agent_backend": "claude_code",
      "mcp_config": {...}
    }
  }
}
```

#### `lh_update_task_config`
动态修改任务配置

```json
{
  "name": "lh_update_task_config",
  "description": "动态修改正在运行或暂停的任务配置",
  "parameters": {
    "task_id": "任务ID",
    "config_updates": {
      "max_rounds": 30,
      "executor_model": "gpt-5.6-sol",
      "timeouts": {
        "executor": 2400
      }
    }
  },
  "returns": {
    "success": true,
    "updated_fields": ["max_rounds", "executor_model", "timeouts.executor"],
    "new_config": {...}
  }
}
```

### 2. 轮次历史管理

#### `lh_get_round_detail`
获取特定轮次的详细信息

```json
{
  "name": "lh_get_round_detail",
  "description": "获取特定轮次的完整执行细节，包括输入、输出、日志",
  "parameters": {
    "task_id": "任务ID",
    "round_id": "轮次ID或索引"
  },
  "returns": {
    "round_id": "task_abc123_r5",
    "round_index": 5,
    "timestamp": "2025-01-15T10:30:00Z",
    "status": "complete",
    "manager": {
      "input_prompt": "完整的 Manager 输入",
      "output": "Manager 的规划结果",
      "model": "claude-opus-5",
      "duration_ms": 5000,
      "tokens_used": 1500
    },
    "executor": {
      "type": "cli",
      "input_prompt": "完整的 Executor 输入",
      "output": "Executor 的执行结果",
      "commands_executed": ["npm install", "npm test"],
      "files_modified": ["package.json", "src/index.js"],
      "model": "gpt-5.6-sol",
      "duration_ms": 45000,
      "tokens_used": 3000
    },
    "auditor": {
      "input_prompt": "完整的 Auditor 输入",
      "output": "Auditor 的验证报告",
      "verification_checks": [...],
      "model": "claude-opus-5",
      "duration_ms": 8000,
      "tokens_used": 2000
    },
    "checkpoint": {...}
  }
}
```

#### `lh_list_rounds`
列出任务的所有轮次

```json
{
  "name": "lh_list_rounds",
  "description": "列出任务的所有执行轮次，支持过滤和分页",
  "parameters": {
    "task_id": "任务ID",
    "status_filter": "complete|incomplete|blocked",
    "offset": 0,
    "limit": 20
  },
  "returns": {
    "total": 12,
    "rounds": [
      {
        "round_id": "task_abc123_r1",
        "round_index": 1,
        "status": "complete",
        "timestamp": "2025-01-15T10:00:00Z",
        "summary": "创建项目结构"
      },
      // ...
    ]
  }
}
```

#### `lh_edit_round`
编辑特定轮次的结果（用于修正错误）

```json
{
  "name": "lh_edit_round",
  "description": "编辑已执行轮次的结果，用于修正错误或调整输出",
  "parameters": {
    "task_id": "任务ID",
    "round_id": "轮次ID",
    "edits": {
      "status": "complete",
      "audit_report": "修改后的审计报告",
      "checkpoint": {
        "verified_state": "更新的验证状态"
      }
    },
    "reason": "修正原因说明"
  },
  "returns": {
    "success": true,
    "round_id": "task_abc123_r5",
    "edited_fields": ["status", "audit_report", "checkpoint"],
    "revision": 2
  }
}
```

#### `lh_delete_round`
删除特定轮次及其后续轮次

```json
{
  "name": "lh_delete_round",
  "description": "删除特定轮次及其后续的所有轮次，用于回滚",
  "parameters": {
    "task_id": "任务ID",
    "round_id": "要删除的轮次ID",
    "delete_mode": "this_only|this_and_after"
  },
  "returns": {
    "success": true,
    "deleted_rounds": ["task_abc123_r5", "task_abc123_r6"],
    "new_current_round": 4,
    "rollback_checkpoint": {...}
  }
}
```

#### `lh_retry_round`
重试失败或有问题的轮次

```json
{
  "name": "lh_retry_round",
  "description": "重新执行特定轮次，可以修改输入参数",
  "parameters": {
    "task_id": "任务ID",
    "round_id": "要重试的轮次ID",
    "modified_input": {
      "manager_guidance": "额外的指导信息",
      "executor_hints": "执行提示"
    }
  },
  "returns": {
    "success": true,
    "new_round_id": "task_abc123_r5_retry1",
    "result": {...}
  }
}
```

### 3. Checkpoint 高级管理

#### `lh_list_checkpoints`
列出所有 checkpoint

```json
{
  "name": "lh_list_checkpoints",
  "description": "列出任务的所有 checkpoint，可以选择恢复点",
  "parameters": {
    "task_id": "任务ID"
  },
  "returns": {
    "checkpoints": [
      {
        "checkpoint_id": "task_abc123_cp1",
        "round_id": "task_abc123_r3",
        "timestamp": "2025-01-15T10:15:00Z",
        "verified_state": "完成项目结构创建",
        "can_restore": true
      },
      // ...
    ]
  }
}
```

#### `lh_create_checkpoint`
手动创建 checkpoint

```json
{
  "name": "lh_create_checkpoint",
  "description": "在当前状态手动创建一个 checkpoint",
  "parameters": {
    "task_id": "任务ID",
    "label": "Checkpoint 标签",
    "note": "说明信息"
  }
}
```

#### `lh_compare_checkpoints`
比较两个 checkpoint 的差异

```json
{
  "name": "lh_compare_checkpoints",
  "description": "比较两个 checkpoint 之间的差异",
  "parameters": {
    "task_id": "任务ID",
    "checkpoint_a": "checkpoint ID A",
    "checkpoint_b": "checkpoint ID B"
  },
  "returns": {
    "diff": {
      "rounds_added": 3,
      "files_changed": ["src/index.js", "README.md"],
      "state_changes": "从结构创建到API实现完成"
    }
  }
}
```

### 4. 对话日志管理

#### `lh_get_conversation_log`
获取完整的对话日志

```json
{
  "name": "lh_get_conversation_log",
  "description": "获取任务的完整对话和交互日志",
  "parameters": {
    "task_id": "任务ID",
    "include_prompts": true,
    "include_responses": true,
    "role_filter": "manager|executor|auditor|all"
  },
  "returns": {
    "conversations": [
      {
        "round_id": "task_abc123_r1",
        "role": "manager",
        "timestamp": "2025-01-15T10:00:00Z",
        "prompt": "完整的输入提示",
        "response": "完整的响应",
        "metadata": {...}
      },
      // ...
    ]
  }
}
```

#### `lh_export_conversation`
导出对话历史

```json
{
  "name": "lh_export_conversation",
  "description": "导出任务的对话历史为各种格式",
  "parameters": {
    "task_id": "任务ID",
    "format": "json|markdown|html",
    "output_path": "可选的输出路径"
  },
  "returns": {
    "format": "markdown",
    "content": "# Task Conversation...",
    "file_path": "/path/to/export.md"
  }
}
```

#### `lh_search_in_conversation`
在对话中搜索内容

```json
{
  "name": "lh_search_in_conversation",
  "description": "在任务的对话历史中搜索特定内容",
  "parameters": {
    "task_id": "任务ID",
    "query": "搜索关键词",
    "role_filter": "manager|executor|auditor|all",
    "search_in": "prompts|responses|all"
  },
  "returns": {
    "matches": [
      {
        "round_id": "task_abc123_r3",
        "role": "executor",
        "match_type": "response",
        "snippet": "...包含关键词的片段...",
        "full_text": "完整内容"
      }
    ]
  }
}
```

### 5. 执行流程控制

#### `lh_set_breakpoint`
在特定条件下设置断点

```json
{
  "name": "lh_set_breakpoint",
  "description": "设置执行断点，满足条件时暂停并通知用户",
  "parameters": {
    "task_id": "任务ID",
    "condition": {
      "type": "round_count|status_change|error|custom",
      "value": "round > 10 or status == 'blocked'"
    },
    "action": "pause|notify|callback"
  },
  "returns": {
    "breakpoint_id": "bp_123",
    "active": true
  }
}
```

#### `lh_step_execution`
单步执行（仅执行下一个角色）

```json
{
  "name": "lh_step_execution",
  "description": "单步执行，只运行下一个角色（Manager/Executor/Auditor）",
  "parameters": {
    "task_id": "任务ID",
    "step_mode": "next_role|full_round"
  },
  "returns": {
    "executed_role": "manager",
    "result": {...},
    "next_role": "executor"
  }
}
```

#### `lh_force_status`
强制设置任务或轮次状态

```json
{
  "name": "lh_force_status",
  "description": "强制设置任务或特定轮次的状态，用于解决卡住的任务",
  "parameters": {
    "task_id": "任务ID",
    "round_id": "可选的轮次ID",
    "new_status": "started|running|paused|completed|failed|blocked",
    "reason": "强制修改的原因"
  }
}
```

### 6. 调试和诊断

#### `lh_get_execution_metrics`
获取执行指标

```json
{
  "name": "lh_get_execution_metrics",
  "description": "获取任务的执行指标和统计信息",
  "parameters": {
    "task_id": "任务ID"
  },
  "returns": {
    "total_rounds": 12,
    "successful_rounds": 10,
    "failed_rounds": 2,
    "total_duration_ms": 540000,
    "total_tokens": 45000,
    "cost_estimate": 2.5,
    "by_role": {
      "manager": {
        "rounds": 12,
        "avg_duration_ms": 4500,
        "total_tokens": 15000
      },
      "executor": {...},
      "auditor": {...}
    }
  }
}
```

#### `lh_validate_task_state`
验证任务状态一致性

```json
{
  "name": "lh_validate_task_state",
  "description": "验证任务的内部状态一致性，检测潜在问题",
  "parameters": {
    "task_id": "任务ID",
    "fix_issues": false
  },
  "returns": {
    "valid": false,
    "issues": [
      {
        "severity": "warning",
        "type": "missing_checkpoint",
        "description": "Round 5 缺少 checkpoint",
        "auto_fixable": true
      }
    ],
    "fixed_issues": []
  }
}
```

#### `lh_get_error_details`
获取详细错误信息

```json
{
  "name": "lh_get_error_details",
  "description": "获取任务执行中的所有错误和警告详情",
  "parameters": {
    "task_id": "任务ID",
    "include_stack_traces": true
  },
  "returns": {
    "errors": [
      {
        "round_id": "task_abc123_r7",
        "role": "executor",
        "error_type": "ExecutionTimeout",
        "message": "Executor 超时",
        "stack_trace": "...",
        "recovery_suggestions": ["增加超时时间", "简化任务"]
      }
    ]
  }
}
```

### 7. 批量操作

#### `lh_batch_execute_rounds`
批量执行多轮

```json
{
  "name": "lh_batch_execute_rounds",
  "description": "批量执行多轮，直到完成或遇到错误",
  "parameters": {
    "task_id": "任务ID",
    "count": 5,
    "stop_on_error": true,
    "stop_on_blocked": true
  },
  "returns": {
    "executed_rounds": 3,
    "stopped_reason": "blocked",
    "last_round_id": "task_abc123_r8"
  }
}
```

#### `lh_clone_task`
克隆任务（用于实验）

```json
{
  "name": "lh_clone_task",
  "description": "克隆现有任务，用于尝试不同的执行策略",
  "parameters": {
    "task_id": "原任务ID",
    "clone_from_round": "从哪个轮次开始克隆",
    "config_overrides": {
      "executor_model": "不同的模型"
    }
  },
  "returns": {
    "new_task_id": "task_xyz789",
    "cloned_rounds": 5
  }
}
```

### 8. 实时监控

#### `lh_subscribe_task_events`
订阅任务事件

```json
{
  "name": "lh_subscribe_task_events",
  "description": "订阅任务的实时事件流",
  "parameters": {
    "task_id": "任务ID",
    "events": ["round_start", "round_complete", "status_change", "error"]
  },
  "returns": {
    "subscription_id": "sub_123",
    "websocket_url": "ws://..."
  }
}
```

## 使用场景示例

### 场景 1：修正执行错误

```
问题：第5轮的 Executor 执行了错误的命令

解决：
1. lh_get_round_detail(task_id, round_id="r5")
   - 查看详细的执行日志
   
2. lh_edit_round(task_id, round_id="r5", edits={
     "status": "incomplete",
     "audit_report": "命令执行错误，需要重新执行"
   })
   - 修改轮次状态
   
3. lh_delete_round(task_id, round_id="r6", delete_mode="this_and_after")
   - 删除后续依赖错误结果的轮次
   
4. lh_retry_round(task_id, round_id="r5", modified_input={
     "executor_hints": "使用 npm install 而不是 yarn"
   })
   - 重新执行修正后的轮次
```

### 场景 2：调整任务配置

```
问题：任务执行太慢，需要增加超时时间和更换模型

解决：
1. lh_get_task_config(task_id)
   - 查看当前配置
   
2. lh_pause_task(task_id)
   - 暂停任务
   
3. lh_update_task_config(task_id, config_updates={
     "executor_model": "gpt-5.6-sol",
     "timeouts": {"executor": 3600}
   })
   - 更新配置
   
4. lh_execute_round(task_id)
   - 继续执行，使用新配置
```

### 场景 3：调试卡住的任务

```
问题：任务在第8轮后一直显示 "running" 但没有进展

解决：
1. lh_get_execution_metrics(task_id)
   - 查看整体执行情况
   
2. lh_validate_task_state(task_id, fix_issues=true)
   - 检测并修复状态问题
   
3. lh_get_error_details(task_id)
   - 查看是否有隐藏错误
   
4. lh_force_status(task_id, round_id="r8", new_status="incomplete",
                    reason="手动重置卡住的轮次")
   - 强制重置状态
```

### 场景 4：实验性分支

```
场景：想尝试不同的执行策略，但不想丢失当前进度

解决：
1. lh_create_checkpoint(task_id, label="实验前备份")
   - 创建备份点
   
2. lh_clone_task(task_id, clone_from_round=5, config_overrides={
     "executor_model": "claude-opus-5"
   })
   - 克隆任务尝试不同配置
   
3. 比较两个任务的结果
   
4. 如果新策略更好，在原任务中应用相同配置
```

## 工具总结

| 类别 | 工具数量 | 核心功能 |
|------|---------|---------|
| 任务配置 | 2 | 查看和修改任务配置 |
| 轮次管理 | 6 | 查看、编辑、删除、重试轮次 |
| Checkpoint | 3 | 列出、创建、比较 checkpoint |
| 对话日志 | 3 | 查看、导出、搜索对话 |
| 执行控制 | 3 | 断点、单步、强制状态 |
| 调试诊断 | 3 | 指标、验证、错误详情 |
| 批量操作 | 2 | 批量执行、克隆任务 |
| 实时监控 | 1 | 事件订阅 |

**总计：23 个高级 API**

## 实现优先级

### P0 (核心功能)
- lh_get_round_detail
- lh_edit_round
- lh_delete_round
- lh_get_task_config
- lh_update_task_config
- lh_retry_round

### P1 (重要功能)
- lh_list_rounds
- lh_list_checkpoints
- lh_create_checkpoint
- lh_get_conversation_log
- lh_get_execution_metrics
- lh_validate_task_state

### P2 (增强功能)
- lh_compare_checkpoints
- lh_search_in_conversation
- lh_export_conversation
- lh_get_error_details
- lh_force_status
- lh_step_execution

### P3 (高级功能)
- lh_set_breakpoint
- lh_batch_execute_rounds
- lh_clone_task
- lh_subscribe_task_events

这些高级 API 让用户可以完全控制任务的执行过程，而不需要重新开始！
