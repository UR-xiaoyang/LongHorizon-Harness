# LongHorizon-Harness MCP 高级 API 使用示例

## 完整实现的高级 API（14个）

### ✅ 配置管理（2个）
1. **lh_get_task_config** - 获取任务配置
2. **lh_update_task_config** - 动态修改配置

### ✅ 轮次管理（5个）
3. **lh_get_round_detail** - 获取轮次详情
4. **lh_list_rounds** - 列出所有轮次
5. **lh_edit_round** - 编辑轮次结果
6. **lh_delete_round** - 删除轮次
7. **lh_retry_round** - 重试轮次

### ✅ Checkpoint 管理（2个）
8. **lh_list_checkpoints** - 列出所有 checkpoint
9. **lh_create_checkpoint** - 手动创建 checkpoint

### ✅ 对话日志（2个）
10. **lh_get_conversation_log** - 获取对话日志
11. **lh_search_in_conversation** - 搜索对话内容

### ✅ 诊断工具（2个）
12. **lh_get_execution_metrics** - 获取执行指标
13. **lh_validate_task_state** - 验证状态一致性

### 基础 API（9个，已实现）
- lh_start_task
- lh_get_task_status
- lh_execute_round
- lh_get_checkpoint
- lh_recover_task
- lh_pause_task
- lh_stop_task
- lh_inject_feedback
- lh_get_audit_trail

**总计：23 个 MCP 工具**

---

## 实战场景演示

### 场景 1：任务执行出错，需要修正

**问题**：第 5 轮 Executor 执行了错误的命令，导致后续轮次都基于错误结果

**完整解决流程**：

```javascript
// 1. 首先查看第5轮的详细信息
const round5 = await lh_get_round_detail({
  task_id: "task_abc123",
  round_id: 5  // 或使用 "task_abc123_r5"
});

console.log("第5轮执行详情：");
console.log("- Manager 计划：", round5.manager.output);
console.log("- Executor 执行：", round5.executor.output);
console.log("- 执行的命令：", round5.executor.commands_executed);
// 发现：执行了 "rm -rf node_modules" 但应该是 "npm install"

// 2. 编辑第5轮，标记为需要重做
await lh_edit_round({
  task_id: "task_abc123",
  round_id: 5,
  edits: {
    status: "incomplete",
    audit_report: "执行了错误的删除命令，需要重新执行安装"
  },
  reason: "修正错误的命令执行"
});

// 3. 删除第6轮及之后的所有轮次（因为它们基于错误结果）
const deleted = await lh_delete_round({
  task_id: "task_abc123",
  round_id: 6,
  delete_mode: "this_and_after"
});

console.log("已删除轮次：", deleted.deleted_rounds);
// 输出：["task_abc123_r6", "task_abc123_r7", "task_abc123_r8"]

// 4. 重新执行第5轮，并提供正确的指导
const retry = await lh_retry_round({
  task_id: "task_abc123",
  round_id: 5,
  modified_input: {
    executor_hints: "使用 npm install 安装依赖，不要删除 node_modules"
  }
});

console.log("重试结果：", retry.result.status);
// 输出：complete

// 5. 验证任务状态一致性
const validation = await lh_validate_task_state({
  task_id: "task_abc123",
  fix_issues: true
});

console.log("状态验证：", validation.valid ? "通过" : "有问题");
```

---

### 场景 2：任务太慢，需要调整配置

**问题**：Executor 经常超时，需要增加超时时间并切换到更快的模型

```javascript
// 1. 查看当前配置
const config = await lh_get_task_config({
  task_id: "task_abc123"
});

console.log("当前配置：");
console.log("- Executor 模型：", config.current_config.executor_model);
console.log("- Executor 超时：", config.current_config.timeouts?.executor);
// 输出：模型 gpt-4，超时 1800 秒

// 2. 暂停任务
await lh_pause_task({
  task_id: "task_abc123"
});

// 3. 更新配置
const updated = await lh_update_task_config({
  task_id: "task_abc123",
  config_updates: {
    executor_model: "gpt-5.6-sol",  // 更快的模型
    timeouts: {
      executor: 3600  // 增加到1小时
    },
    max_rounds: 30  // 同时增加最大轮数
  }
});

console.log("已更新配置项：", updated.updated_fields);
// 输出：["executor_model", "timeouts", "max_rounds"]

// 4. 继续执行
await lh_execute_round({
  task_id: "task_abc123"
});
```

---

### 场景 3：需要审查所有对话，找出问题

**问题**：任务多次失败，需要找出是哪个环节反复出问题

```javascript
// 1. 获取执行指标
const metrics = await lh_get_execution_metrics({
  task_id: "task_abc123"
});

console.log("执行统计：");
console.log(`- 总轮次：${metrics.total_rounds}`);
console.log(`- 成功：${metrics.successful_rounds}`);
console.log(`- 失败：${metrics.failed_rounds}`);
console.log(`- Manager 平均耗时：${metrics.by_role.manager.avg_duration_ms}ms`);
console.log(`- Executor 平均耗时：${metrics.by_role.executor.avg_duration_ms}ms`);
console.log(`- 总 Token 消耗：${metrics.total_tokens}`);

// 2. 搜索错误相关的对话
const errorMatches = await lh_search_in_conversation({
  task_id: "task_abc123",
  query: "error",
  role_filter: "executor",
  search_in: "responses"
});

console.log(`找到 ${errorMatches.total_matches} 处错误相关内容`);

errorMatches.matches.forEach(match => {
  console.log(`\n轮次 ${match.round_id}:`);
  console.log(match.snippet);
});

// 3. 查看失败的轮次列表
const failedRounds = await lh_list_rounds({
  task_id: "task_abc123",
  status_filter: "incomplete"
});

console.log(`\n失败的轮次（共 ${failedRounds.total} 个）：`);
failedRounds.rounds.forEach(round => {
  console.log(`- 轮次 ${round.round_index}: ${round.summary}`);
});

// 4. 查看具体某个失败轮次的完整对话
const failedDetail = await lh_get_round_detail({
  task_id: "task_abc123",
  round_id: failedRounds.rounds[0].round_index
});

console.log("\n失败轮次的完整对话：");
console.log("Manager 输入：", failedDetail.manager.input_prompt);
console.log("Executor 输出：", failedDetail.executor.output);
console.log("Auditor 报告：", failedDetail.auditor.output);
```

---

### 场景 4：创建实验性备份点

**问题**：想尝试不同的执行策略，但不想丢失当前进度

```javascript
// 1. 查看当前所有 checkpoint
const checkpoints = await lh_list_checkpoints({
  task_id: "task_abc123"
});

console.log(`当前有 ${checkpoints.total} 个 checkpoint`);

// 2. 在当前位置手动创建一个备份点
const backup = await lh_create_checkpoint({
  task_id: "task_abc123",
  label: "实验前备份 - 尝试不同的 Executor 模型",
  note: "当前进度：完成了前端基础框架，准备实现后端 API"
});

console.log("已创建备份点：", backup.checkpoint_id);

// 3. 更新配置尝试新策略
await lh_update_task_config({
  task_id: "task_abc123",
  config_updates: {
    executor_model: "claude-opus-5",  // 尝试更强的模型
  }
});

// 4. 执行几轮
for (let i = 0; i < 3; i++) {
  await lh_execute_round({ task_id: "task_abc123" });
}

// 5. 如果效果不好，可以回滚
// 方案A：恢复到备份点
await lh_recover_task({
  task_id: "task_abc123",
  checkpoint_id: backup.checkpoint_id
});

// 方案B：或者删除实验的轮次
const currentRound = (await lh_get_task_status({ task_id: "task_abc123" })).current_round;
const experimentStartRound = currentRound - 3;
await lh_delete_round({
  task_id: "task_abc123",
  round_id: experimentStartRound,
  delete_mode: "this_and_after"
});
```

---

### 场景 5：完整的对话日志导出和分析

**问题**：任务完成后，需要导出完整日志用于学习和分析

```javascript
// 1. 获取完整的对话日志
const fullLog = await lh_get_conversation_log({
  task_id: "task_abc123",
  include_prompts: true,
  include_responses: true,
  role_filter: "all"
});

console.log(`总共 ${fullLog.total} 条对话记录`);

// 2. 分析对话模式
const managerConversations = fullLog.conversations.filter(c => c.role === "manager");
const executorConversations = fullLog.conversations.filter(c => c.role === "executor");
const auditorConversations = fullLog.conversations.filter(c => c.role === "auditor");

console.log("\n对话统计：");
console.log(`- Manager：${managerConversations.length} 次`);
console.log(`- Executor：${executorConversations.length} 次`);
console.log(`- Auditor：${auditorConversations.length} 次`);

// 3. 分析 token 使用
const totalTokens = fullLog.conversations.reduce(
  (sum, c) => sum + (c.metadata?.tokens_used || 0), 
  0
);
console.log(`\n总 Token 消耗：${totalTokens}`);

// 4. 提取所有 Manager 的规划
const allPlans = managerConversations.map(c => ({
  round: c.round_id,
  plan: c.response
}));

console.log("\n所有 Manager 规划：");
allPlans.forEach(p => {
  console.log(`\n${p.round}:`);
  console.log(p.plan.substring(0, 200) + "...");
});

// 5. 搜索特定关键词
const searchResult = await lh_search_in_conversation({
  task_id: "task_abc123",
  query: "API",
  search_in: "all"
});

console.log(`\n关键词 "API" 出现 ${searchResult.total_matches} 次`);
```

---

## 对比：有无高级 API 的区别

### 没有高级 API 时

```javascript
// 问题：第5轮执行错误
用户: "第5轮执行错了，需要重做"
Claude: "抱歉，我无法修改已执行的轮次。你需要：
1. 停止当前任务
2. 重新开始一个新任务
3. 所有进度丢失"

// 结果：❌ 丢失所有进度，从头开始
```

### 有高级 API 时

```javascript
// 问题：第5轮执行错误
用户: "第5轮执行错了，需要重做"
Claude: "我来帮你修正：
1. 查看第5轮详情
2. 删除第6轮及之后的轮次
3. 重新执行第5轮
4. 继续后续工作"

// 结果：✅ 保留前4轮进度，只重做有问题的部分
```

---

## 高级 API 的核心价值

### 1. 细粒度控制
- ✅ 修改单个轮次
- ✅ 动态调整配置
- ✅ 精确回滚

### 2. 深度调试
- ✅ 查看完整对话
- ✅ 搜索特定内容
- ✅ 分析执行指标

### 3. 灵活恢复
- ✅ 多个 checkpoint
- ✅ 选择性回滚
- ✅ 实验性分支

### 4. 透明可控
- ✅ 完整审计轨迹
- ✅ 状态一致性验证
- ✅ 问题快速定位

---

## 完整的 API 分类

### 基础层（9个）- 任务生命周期
- 启动、状态、执行、暂停、恢复、停止

### 高级层（14个）- 细粒度控制
- 配置管理（2个）
- 轮次管理（5个）
- Checkpoint（2个）
- 对话日志（2个）
- 诊断工具（2个）
- 验证工具（1个）

### 未来扩展（可选）
- 批量操作
- 实时监控
- 任务克隆
- 断点调试

---

## 使用建议

### 日常使用
基础 API 足够：
- lh_start_task
- lh_execute_round
- lh_get_task_status
- lh_pause_task / lh_stop_task

### 出现问题时
使用高级 API：
- lh_get_round_detail（查看详情）
- lh_search_in_conversation（搜索问题）
- lh_edit_round / lh_delete_round（修正错误）
- lh_retry_round（重新执行）

### 任务优化时
使用诊断 API：
- lh_get_execution_metrics（分析性能）
- lh_update_task_config（调整配置）
- lh_validate_task_state（确保一致性）

### 学习分析时
使用日志 API：
- lh_get_conversation_log（导出日志）
- lh_list_rounds（回顾历史）
- lh_get_audit_trail（审计轨迹）

---

## 总结

通过这 23 个 MCP 工具，LongHorizon-Harness 现在提供：

✅ **完整的任务生命周期管理**  
✅ **细粒度的执行控制**  
✅ **强大的调试和诊断能力**  
✅ **灵活的错误恢复机制**  
✅ **透明的审计轨迹**  

**核心优势**：不再需要因为配置错误或执行失败而重新开始，可以随时修正、回滚、调整，真正实现"可控的长期任务管理"！
