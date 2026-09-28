# LongHorizon-Harness MCP Server 开发者指南

## ✅ 启动成功！

MCP Server 现在可以正常启动，日志显示：
```
2026-09-28 17:46:53,194 - lh_harness.cli - INFO - Starting LongHorizon-Harness MCP server
2026-09-28 17:46:53,194 - lh_harness.cli - INFO - Transport: stdio
2026-09-28 17:46:53,194 - lh_harness.cli - INFO - State root: ~/.lh-harness
2026-09-28 17:46:53,309 - lh_harness.mcp_server.server - INFO - Starting MCP server on stdio
```

## 🛠️ 开发者模式启动方式

### 方式 1：直接运行（用于调试）

```bash
cd E:/Project/LongHorizon-Harness
uv run lh-harness mcp-server --log-file /tmp/mcp-dev.log --log-level DEBUG
```

### 方式 2：测试模式（带超时）

```bash
cd E:/Project/LongHorizon-Harness
timeout 10 uv run lh-harness mcp-server --log-level INFO
```

### 方式 3：通过 Claude Desktop（生产模式）

已配置在：`C:\Users\xiaoyang\AppData\Roaming\Claude\claude_desktop_config.json`

重启 Claude Desktop 即可使用。

## 🧪 测试 MCP Server

### 1. 手动测试 stdio 通信

```bash
cd E:/Project/LongHorizon-Harness

# 发送 tools/list 请求
echo '{"jsonrpc":"2.0","id":1,"method":"tools/list","params":{}}' | uv run lh-harness mcp-server
```

预期输出：包含 23 个工具的列表

### 2. 运行测试套件

```bash
cd E:/Project/LongHorizon-Harness
uv run pytest tests/test_mcp_server.py -v
```

### 3. 交互式测试

```bash
cd E:/Project/LongHorizon-Harness
uv run python tests/test_mcp_server.py
```

这会运行完整的工作流演示：
- 启动任务
- 执行轮次
- 获取状态
- 注入反馈
- 查看审计轨迹

## 🔍 调试技巧

### 查看详细日志

```bash
# 启动时指定日志文件和级别
uv run lh-harness mcp-server \
  --log-file /tmp/mcp-debug.log \
  --log-level DEBUG

# 在另一个终端查看日志
tail -f /tmp/mcp-debug.log
```

### 检查 MCP 工具是否正确注册

在 Python 中：

```python
from lh_harness.mcp_server import create_mcp_server

server = create_mcp_server()
print(f"已注册 {len(server.tools)} 个工具:")
for name in server.tools.keys():
    print(f"  - {name}")
```

### 测试单个工具

```python
import asyncio
from lh_harness.mcp_server import create_mcp_server

async def test():
    server = create_mcp_server()
    
    # 测试启动任务
    result = await server.handle_tool_call(
        "lh_start_task",
        {
            "goal": "测试任务",
            "workspace": "./test-workspace",
            "max_rounds": 10
        }
    )
    print(result)

asyncio.run(test())
```

## 📝 修复的问题

### Issue 1: 导入错误
**问题**: `ImportError: cannot import name 'get_agent_adapter'`

**修复**: 
- 移除了不存在的 `get_agent_adapter` 导入
- 在 `integration.py` 中实现了 `_build_agent()` 方法
- 支持 claude_code、codex、opencode、deepseek_harness

### Issue 2: 现在支持的 Agent
```python
# 支持的 agent 类型
agents = [
    "claude_code",   # Claude Code (默认)
    "codex",         # Codex
    "opencode",      # OpenCode
    "deepseek_harness"  # DeepSeek Harness
]
```

## 🚀 在 Claude Desktop 中测试

### 1. 确认配置

配置文件位置：
```
C:\Users\xiaoyang\AppData\Roaming\Claude\claude_desktop_config.json
```

配置内容：
```json
{
  "mcpServers": {
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

### 2. 重启 Claude Desktop

关闭并重新打开 Claude Desktop 应用。

### 3. 测试工具可用性

在 Claude Desktop 的对话中：

```
你: 请列出可用的 LongHorizon-Harness 工具

Claude: [会显示 23 个 MCP 工具]
```

### 4. 测试基础功能

```
你: 请使用 LongHorizon-Harness 启动一个测试任务

Claude: [调用 lh_start_task]
已启动任务，task_id: task_abc123
```

## 📊 当前状态

### ✅ 已完成
- [x] MCP Server 可以成功启动
- [x] 23 个工具已注册
- [x] 集成层已实现
- [x] Agent 适配器修复完成
- [x] Claude Desktop 配置完成

### ⏳ 待完善
- [ ] 完整的 Manager/Executor/Auditor 集成
- [ ] Checkpoint 文件持久化
- [ ] Token 使用跟踪
- [ ] 时间戳完善

### 🧪 测试状态
- [ ] 单元测试通过
- [ ] 集成测试通过
- [ ] Claude Desktop 测试
- [ ] 完整工作流测试

## 🔄 提交的更改

### Git 状态
- **分支**: `feature/mcp-server-integration`
- **提交**: `ec2e07c` - feat: Add MCP Server support with 23 tools
- **推送**: ✅ 已推送到 fork
- **PR**: [#91](https://github.com/AMAP-ML/LongHorizon-Harness/pull/91)
- **Issue**: [#90](https://github.com/AMAP-ML/LongHorizon-Harness/issues/90)

### 需要提交修复

当前修复了导入错误，需要提交：

```bash
git add src/lh_harness/mcp_server/integration.py
git commit -m "fix: Resolve agent adapter import error in MCP Server integration

- Remove non-existent get_agent_adapter import
- Implement _build_agent() method in integration layer
- Support claude_code, codex, opencode, deepseek_harness agents
- MCP Server now starts successfully"
git push fork feature/mcp-server-integration
```

## 📚 相关文档

- [MCP_INTEGRATION_GUIDE.md](MCP_INTEGRATION_GUIDE.md) - 完整集成指南
- [MCP_ADVANCED_API_EXAMPLES.md](MCP_ADVANCED_API_EXAMPLES.md) - 使用示例
- [CLAUDE_DESKTOP_SETUP.md](CLAUDE_DESKTOP_SETUP.md) - Claude Desktop 安装
- [INTEGRATION_COMPLETE_REPORT.md](INTEGRATION_COMPLETE_REPORT.md) - 实现报告

## 🎯 下一步

1. **提交修复** - 将导入错误修复推送到 PR
2. **测试 Claude Desktop** - 重启并测试集成
3. **完善集成层** - 实现完整的 Manager/Executor/Auditor 调用
4. **编写测试** - 确保所有功能正常工作

祝开发顺利！🚀
