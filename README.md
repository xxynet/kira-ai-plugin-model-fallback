# Model Fallback

`kira-ai-plugin-model-fallback` adds a configured sequence of LLM fallback models to every message batch.

## Configuration

Set up to three fallback models in the plugin settings. For every batch, the plugin creates the model group in this order:

1. The session's selected LLM, or KiraAI's global default LLM when unset
2. First Fallback Model
3. Second Fallback Model
4. Third Fallback Model
5. More Fallback Models, in the order they were selected

Empty selections are ignored. Duplicate selections are used only once.

The agent tries the next model only after a provider-level failure, such as a network, timeout, or API error.

Requires KiraAI >3.2.0 with [KiraAI PR #437](https://github.com/xxynet/KiraAI/pull/437), which adds session-aware default LLM lookup and metadata-only session resolution. The original v3.2.0 release does not contain these APIs; use a newer core version containing that merged change. An unavailable session selection raises an error instead of silently using the global default.

### Changes in v1.2.0

The session's selected LLM now takes precedence over the global default. The plugin loads only session metadata before building the fallback list. Existing fallback settings and model ordering remain unchanged.

## 配置说明

在插件设置中最多可配置三个回退模型，并可在“更多回退模型”中添加任意数量的额外模型。每个消息批次会按以下顺序建立模型组：

1. 会话选择的大语言模型；未设置时使用 KiraAI 的全局默认大语言模型
2. 第一回退模型
3. 第二回退模型
4. 第三回退模型
5. 更多回退模型（按选择顺序）

未选择的项会被忽略，重复模型只会尝试一次。仅在网络、超时或 API 错误等 Provider 级失败后，才会尝试下一个模型。

需要 KiraAI >3.2.0，且包含 [KiraAI PR #437](https://github.com/xxynet/KiraAI/pull/437) 提供的会话级默认模型选择和仅元数据会话解析接口。原始 v3.2.0 发布版不包含这些接口，请使用包含该合并改动的更高版本核心。会话指定的模型不可用时会报错，不会悄悄改用全局默认模型。

### v1.2.0 变更

会话选择的大语言模型优先于全局默认模型。构建回退列表前仅加载会话元数据。已有回退配置及模型顺序保持不变。
