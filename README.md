# Run MCP with LLM Demo

<div align="center">
  <img src="https://raw.githubusercontent.com/fastmcp/fastmcp/main/docs/_static/logo.png" width="200" alt="FastMCP Logo">
  <br>
  <p><strong>将大语言模型与外部MCP服务器无缝集成的演示应用</strong></p>
</div>

## 📖 项目简介

这是一个展示如何将大语言模型与外部MCP（Model Control Protocol）服务器集成的Web应用。通过这个演示项目，您可以了解如何让大模型使用外部工具执行各种任务，例如查询天气、搜索信息或访问其他API服务。

## 💻 运行示例

<div align="center">
  <img src="screenshots/demo_screenshot.png" alt="应用运行示例" width="90%" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
  <p><em>应用运行界面 - 天气查询示例</em></p>
</div>

<div align="center">
  <img src="screenshots/demo_screenshot2.png" alt="应用运行示例" width="90%" style="border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.1);">
  <p><em>应用设置界面 - 天气查询示例</em></p>
</div>

## ✨ 特性

- 🤖 **大模型集成**：使用标准API与大语言模型进行对话交互
- 🔌 **MCP服务器连接**：支持通过HTTP和命令行两种方式连接外部MCP服务器
- 🔄 **流式响应**：实时显示模型回复，提供更好的用户体验
- 🛠️ **工具调用**：支持大模型调用外部工具并处理工具执行结果
- 📱 **现代化UI**：直观友好的用户界面，支持移动设备

## 🚀 快速开始

### 前置条件

- Python 3.8+
- [FastMCP](https://github.com/fastmcp/fastmcp) 库
- 有效的API密钥（目前支持豆包等中文大模型）

### 安装依赖

```bash
pip install -r requirements.txt
```

### 设置环境变量

```bash
# Linux/MacOS
export ARK_API_KEY=your_api_key_here

# Windows (PowerShell)
$env:ARK_API_KEY = "your_api_key_here"

# 或者在启动时直接传递
python run.py --api-key=your_api_key_here
```

### 启动应用

```bash
python run.py
```

应用将在 http://localhost:8080 上运行。在浏览器中打开此地址即可使用。

## ⚙️ 配置外部MCP服务器

在Web界面的"设置"标签页中，您可以配置外部MCP服务器。配置采用JSON格式：

```json
{
  "mcpServers": {
    "weather": {
      "url": "http://127.0.0.1:8000/sse"
    },
    "command_server": {
      "command": "./run_tool.sh",
      "args": ["--arg1", "--arg2"],
      "env": {
        "ENV_VAR1": "value1"
      }
    }
  }
}
```

### 支持的服务器类型

- **HTTP服务器**：通过URL连接，使用SSE传输
  ```json
  {
    "url": "http://127.0.0.1:8000/sse"
  }
  ```

- **命令行服务器**：通过执行命令启动
  ```json
  {
    "command": "./run_tool.sh",
    "args": ["--arg1", "--arg2"], 
    "env": {
      "ENV_VAR1": "value1"
    }
  }
  ```

## 🌤️ 示例气象服务

项目附带了一个示例气象服务，用于演示外部MCP服务器的使用：

```bash
# 启动气象服务
bash run_weather_service.sh
```

启动后，您可以在Web界面中配置以下内容来连接：

```json
{
  "mcpServers": {
    "weather": {
      "url": "http://127.0.0.1:8000/sse"
    }
  }
}
```

然后，您可以在聊天界面中询问天气，例如：
- "北京今天天气怎么样？"
- "上海明天会下雨吗？"
- "武汉气温多少度？"

## 🧩 项目结构

```
.
├── app/                  # 主应用代码
│   ├── api/              # API路由和端点
│   │   └── routes.py     # API路由定义
│   ├── services/         # 服务层
│   │   └── mcp_service.py # MCP服务集成
│   ├── static/           # 静态资源
│   │   ├── css/          # 样式文件
│   │   └── js/           # JavaScript代码
│   ├── templates/        # HTML模板
│   └── main.py           # 应用主模块
├── fastmcp/              # FastMCP库（子模块）
├── requirements.txt      # 项目依赖
├── run.py                # 主运行脚本
├── run_weather_service.sh # 气象服务启动脚本
└── weather_service.py    # 示例气象服务
```

## 📚 技术栈

- **后端**：FastAPI, Python 3.8+
- **前端**：HTML, CSS, JavaScript
- **工具集成**：FastMCP 库
- **模型接口**：兼容 OpenAI API 的接口

## 🔍 开发说明

### 添加新工具服务器

1. 创建一个遵循MCP协议的服务器脚本
2. 确保服务器提供所需的工具定义和实现
3. 将服务器配置添加到Web界面中的MCP配置

### 自定义界面

前端界面使用简单的HTML、CSS和JavaScript实现。您可以通过修改`app/templates`和`app/static`目录中的文件来自定义界面。

## 📋 待办功能

- [ ] 支持更多大模型提供商
- [ ] 添加更多示例工具服务
- [ ] 用户认证和配置保存
- [ ] Docker容器化部署

## 📝 许可

本项目采用 [MIT 许可证](LICENSE)。

## 🙏 致谢

- [FastMCP](https://github.com/fastmcp/fastmcp) - MCP协议实现
- 所有贡献者和测试用户

---

<div align="center">
  <p>Made with ❤️ for the AI and MCP community</p>
</div> 