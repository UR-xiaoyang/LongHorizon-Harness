# LongHorizon-Harness MCP Server - Claude Desktop 安装指南

## ✅ 已完成配置

已将 LongHorizon-Harness MCP Server 添加到 Claude Desktop 配置文件：

**配置文件位置**：
```
C:\Users\xiaoyang\AppData\Roaming\Claude\claude_desktop_config.json
```

**添加的配置**：
```json
{
  "mcpServers": {
    ...
    "longhorizon-harness": {
      "command": "uv",
      "args": [
        "run",
        "--directory",
        "E:/Project/LongHorizon-Harness",
        "lh-harness",
        "mcp-server"
      ],
      "env": {
        "PYTHONPATH": "E:/Project/LongHorizon-Harness/src",
        "LH_HARNESS_CONFIG": "E:/Project/LongHorizon-Harness/.lh-harness/config.toml"
      }
    }
  }
}
```

## 🚀 如何使用

### 1. 重启 Claude Desktop
配置文件已更新，需要重启 Claude Desktop 应用以加载 MCP Server。

### 2. 验证 MCP Server 可用

重启后，在 Claude Desktop 中你可以使用以下工具：

#### 基础工具（9个）
- `lh_start_task` - 启动长期任务
- `lh_get_task_status` - 查询任务状态
- `lh_execute_round` - 执行一轮循环
- `lh_get_checkpoint` - 获取检查点
- `lh_recover_task` - 恢复任务
- `lh_pause_task` - 暂停任务
- `lh_stop_task` - 停止任务
- `lh_inject_feedback` - 注入反馈
- `lh_get_audit_trail` - 获取审计轨迹

#### 高级工具（14个）
- `lh_get_task_config` - 获取任务配置
- `lh_update_task_config` - 动态修改配置
- `lh_get_round_detail` - 获取轮次详情
- `lh_list_rounds` - 列出所有轮次
- `lh_edit_round` - 编辑轮次结果
- `lh_delete_round` - 删除轮次
- `lh_retry_round` - 重试失败的轮次
- `lh_list_checkpoints` - 列出所有检查点
- `lh_create_checkpoint` - 手动创建检查点
- `lh_get_conversation_log` - 获取完整对话日志
- `lh_search_in_conversation` - 搜索对话内容
- `lh_get_execution_metrics` - 获取执行指标
- `lh_validate_task_state` - 验证状态一致性

### 3. 示例使用

#### 启动一个长期任务
```
你: 请帮我开发一个完整的博客系统，包括前端、后端和数据库

Claude: 这是一个复杂的长期任务，我会使用 LongHorizon-Harness 来管理。

[调用 lh_start_task]
{
  "goal": "开发完整博客系统：React前端 + FastAPI后端 + MySQL数据库",
  "workspace": "E:/Projects/blog-system",
  "max_rounds": 30
}

任务已启动，task_id: task_abc123def456
```

#### 执行任务轮次
```
[调用 lh_execute_round]
{
  "task_id": "task_abc123def456"
}

第1轮执行完成：
- Manager 规划：创建项目结构
- Executor 执行：创建了目录和初始配置文件
- Auditor 验证：结构正确，已创建 checkpoint
```

#### 遇到问题时修正
```
你: 第5轮执行错了，需要重新做

Claude: 我来帮你修正。

[调用 lh_get_round_detail]
查看第5轮的详细信息...

[调用 lh_delete_round]
删除第6轮及之后的轮次...

[调用 lh_retry_round]
重新执行第5轮，已修正...
```

#### 动态调整配置
```
你: 太慢了，换个更快的模型

Claude: 
[调用 lh_pause_task]
任务已暂停

[调用 lh_update_task_config]
{
  "task_id": "task_abc123def456",
  "config_updates": {
    "executor_model": "gpt-5.6-sol",
    "timeouts": {
      "executor": 3600
    }
  }
}

配置已更新，继续执行...
```

## 🔧 故障排查

### 如果 MCP Server 无法连接

1. **检查项目路径**
   ```bash
   # 确认路径存在
   ls E:/Project/LongHorizon-Harness
   ```

2. **测试 MCP Server 启动**
   ```bash
   cd E:/Project/LongHorizon-Harness
   uv run lh-harness mcp-server --log-file /tmp/mcp-test.log
   ```

3. **查看 Claude Desktop 日志**
   - 日志位置：`C:\Users\xiaoyang\AppData\Local\Claude-3p\logs`
   - 查找 MCP 相关错误

### 如果找不到 uv 命令

使用完整路径：
```json
{
  "longhorizon-harness": {
    "command": "C:/Users/xiaoyang/.local/bin/uv.exe",
    "args": [
      "run",
      "--directory",
      "E:/Project/LongHorizon-Harness",
      "lh-harness",
      "mcp-server"
    ],
    ...
  }
}
```

## 📊 配置说明

### command: "uv"
使用 `uv run` 在项目虚拟环境中运行 MCP Server

### args
- `run` - uv 子命令
- `--directory E:/Project/LongHorizon-Harness` - 项目目录
- `lh-harness` - Python 包入口点
- `mcp-server` - MCP Server 子命令

### env
- `PYTHONPATH` - 确保能找到 src 模块
- `LH_HARNESS_CONFIG` - 配置文件路径（可选）

## 🎯 优势

现在你可以在 Claude Desktop 中：

✅ **启动长期任务** - 无需命令行  
✅ **实时查看进度** - 随时查询状态  
✅ **修正错误** - 编辑、删除、重试轮次  
✅ **动态调整配置** - 不需要重启任务  
✅ **查看完整日志** - 搜索对话历史  
✅ **调试诊断** - 验证状态、获取指标  

所有这些都通过自然语言交互完成，无需记忆命令！

## 📚 相关文档

- [MCP_INTEGRATION_GUIDE.md](../MCP_INTEGRATION_GUIDE.md) - 完整集成指南
- [MCP_ADVANCED_API_EXAMPLES.md](../MCP_ADVANCED_API_EXAMPLES.md) - 实战示例
- [INTEGRATION_COMPLETE_REPORT.md](../INTEGRATION_COMPLETE_REPORT.md) - 集成报告

## 🔄 下一步

1. **重启 Claude Desktop** 应用
2. **开始一个对话** 测试 MCP Server
3. **尝试启动一个长期任务**

祝使用愉快！🎉
