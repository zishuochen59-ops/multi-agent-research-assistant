# 项目更迭日志

[![English](https://img.shields.io/badge/语言-English-2563EB)](CHANGELOG.md)
[![中文](https://img.shields.io/badge/语言-中文-DC2626)](CHANGELOG.zh-CN.md)

本日志根据仓库的真实提交记录整理项目功能变化。以下更新均完成于 2026 年 9 月 9 日。

## 文档语言拆分

提交 [`4369baa`](https://github.com/zishuochen59-ops/multi-agent-research-assistant/commit/4369baa)

- 将中英混排的 README 拆分为独立的英文版和中文版。
- 在两版文件顶部加入语言选择按钮。
- 为调度演示增加独立的英文和中文输出。

## 可运行的调度演示

提交 [`2ea222b`](https://github.com/zishuochen59-ops/multi-agent-research-assistant/commit/2ea222b)

- 新增一个执行名额、三个任务的 FCFS 与 SJF 可运行示例。
- 展示执行顺序、平均等待时间和全部任务完成时间。
- 解释并发名额有限时，任务排序为什么会影响等待时间。

## 预测感知调度实验

提交 [`386b0bb`](https://github.com/zishuochen59-ops/multi-agent-research-assistant/commit/386b0bb)、[`201a70e`](https://github.com/zishuochen59-ops/multi-agent-research-assistant/commit/201a70e) 和 [`0867caf`](https://github.com/zishuochen59-ops/multi-agent-research-assistant/commit/0867caf)

- 新增 FCFS 和预测短任务优先两种研究任务调度策略，并支持配置执行名额。
- 新增可解释的问题长度规则，输出相对长度单位和长度区间。
- 新增结构化任务追踪，记录排队时间、调度策略、任务编号和预测长度。
- 新增模型服务调用记录，保存服务商返回的 token 数量和端到端延迟。
- 新增可复现的合成实验，覆盖 20 个随机种子和四档预测误差上限。
- 记录仿真假设、评价指标、实验结果和适用范围。
- 自动化测试由 4 项增加到 12 项。
- 使用字符二元组和中文标点支持基础中文词语检索。

该实验属于合成任务调度研究，没有复现 Prompt2Length 或 JDPMHF，没有训练时长预测模型、控制 GPU 集群或证明真实推理加速。

## 全角色模型协作

提交 [`5250e24`](https://github.com/zishuochen59-ops/multi-agent-research-assistant/commit/5250e24)

- 在线模式下，规划、研究、分析、写作和审查角色分别调用模型。
- 在共享工作区中增加研究笔记。
- 审查提出问题后，写作角色可以进行一次修改。

## 可解释的多智能体流程

提交 [`03d285d`](https://github.com/zishuochen59-ops/multi-agent-research-assistant/commit/03d285d) 和 [`370710d`](https://github.com/zishuochen59-ops/multi-agent-research-assistant/commit/370710d)

- 实现规划、检索、分析、写作和引用审查角色。
- 建立类型明确的来源、证据、事件和共享工作区数据结构。
- 通过线程池并发运行检索角色。
- 增加确定性的离线来源、Markdown 报告、运行轨迹和初始测试。
- 增加安装说明、离线演示和在线模型服务配置。

## 仓库建立

提交 [`14d2059`](https://github.com/zishuochen59-ops/multi-agent-research-assistant/commit/14d2059)

- 将项目定位为本科阶段对可解释多智能体研究流程的探索。
