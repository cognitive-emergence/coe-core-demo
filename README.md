---
title: COE Core Demo
emoji: 🌍
colorFrom: purple
colorTo: pink
sdk: gradio
sdk_version: 5.20.0
app_file: app.py
pinned: false
---

# COE Core — Cognition-Oriented Emergence

**A Cognitive Interaction Protocol for Shared World Models**

COE 为碎片化的世界模型生态（JEPA、Dreamer、World Labs、Cosmos 等）提供统一的**认知交互层**。通过 J/D/T/V 四原语，使异构智能体在可追溯、可审计的框架内达成对世界状态的**可验证共识**。

## 与 JEP 的关系

| 协议 | 回答的问题 | 时态 | 语义 |
|------|-----------|------|------|
| **JEP** | "谁负责？" | 事后追溯 (post-hoc) | 问责语法 |
| **COE** | "世界是什么？" | 事前/事中 (ex-ante / in-situ) | 认知共识 |

&gt; 两者共享 J/D/T/V 原语基因，形成完整的 **"认知-问责"双循环架构**。

## 核心组件

- **四原语认知代数**：J (观察断言) / D (委托观察) / T (终止状态) / V (交叉验证)
- **共识引擎**：Simple Majority / Weighted Trust / Byzantine Fault Tolerance
- **版本化审计链**：Git-like 版本控制 + 时间戳锚定
- **窄腰架构**：~2000-3000 行参考实现，下层世界模型可独立演进

## 验证场景 (Appendix A)

三机器人（A/B/C）协同确认仓库门状态：
1. A 观察门开 → J 事件
2. B 委托 A 持续观察 → D 事件
3. B 确认 A 的观察 → V 事件
4. C 人类确认 → V 事件
5. 共识引擎输出 SWS: door=open
6. A 观察门关 → T + J 事件
7. B/C 确认新状态
8. 共识引擎更新 SWS: door=closed

## 关联资源

- 问责追溯层：[cognitiveemergencelab/jep-spec](https://huggingface.co/spaces/cognitiveemergencelab/jep-spec)
- 记录与隐私层：[cognitiveemergencelab/hjs-archive](https://huggingface.co/spaces/cognitiveemergencelab/hjs-archive)
- 因果链层：[cognitiveemergencelab/jac-core-demo](https://huggingface.co/spaces/cognitiveemergencelab/jac-core-demo)
- 数学基础：[cognitiveemergencelab/causal-observability-demo](https://huggingface.co/spaces/cognitiveemergencelab/causal-observability-demo)

## 许可证

Apache-2.0

## 作者

Cognitive Emergence Lab / Human Judgment Systems Foundation
