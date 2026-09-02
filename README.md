# Model Fallback

`kira-ai-plugin-model-fallback` adds a configured sequence of LLM fallback models to every message batch.

## Configuration

Set up to three fallback models in the plugin settings. For every batch, the plugin creates the model group in this order:

1. KiraAI's configured default LLM
2. First Fallback Model
3. Second Fallback Model
4. Third Fallback Model

Empty selections are ignored. Duplicate selections are used only once.

The agent tries the next model only after a provider-level failure, such as a network, timeout, or API error.

## 配置说明

在插件设置中最多可配置三个回退模型。每个消息批次会按以下顺序建立模型组：

1. KiraAI 配置的默认大语言模型
2. 第一回退模型
3. 第二回退模型
4. 第三回退模型

未选择的项会被忽略，重复模型只会尝试一次。仅在网络、超时或 API 错误等 Provider 级失败后，才会尝试下一个模型。
