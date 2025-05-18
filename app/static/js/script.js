document.addEventListener('DOMContentLoaded', () => {
    const chatMessages = document.getElementById('chatMessages');
    const userMessageInput = document.getElementById('userMessage');
    const sendButton = document.getElementById('sendButton');
    const mcpConfigTextarea = document.getElementById('mcpConfig');
    const simpleJsonEditor = document.getElementById('simpleJsonEditor');
    const modelSelect = document.getElementById('modelSelect');
    const tabs = document.querySelectorAll('.tab');
    const tabPanels = document.querySelectorAll('.tab-panel');
    const formatJsonBtn = document.getElementById('formatJsonBtn');
    const defaultConfigBtn = document.getElementById('defaultConfigBtn');
    const saveSettingsBtn = document.getElementById('saveSettingsBtn');

    // 默认MCP配置
    const defaultMcpConfig = {
        "mcpServers": {
            "weather": {
                "url": "http://127.0.0.1:8000/sse"
            }
        }
    };

    // 初始化配置编辑器
    function initConfigEditor() {
        // 将初始值同步到隐藏的textarea
        mcpConfigTextarea.value = simpleJsonEditor.value;

        // 编辑器内容变更事件
        simpleJsonEditor.addEventListener('input', () => {
            mcpConfigTextarea.value = simpleJsonEditor.value;
        });

        // 格式化JSON按钮事件
        formatJsonBtn.addEventListener('click', formatJson);

        // 恢复默认配置按钮事件
        defaultConfigBtn.addEventListener('click', restoreDefaultConfig);

        // 保存设置按钮事件
        saveSettingsBtn.addEventListener('click', saveSettings);

        // 添加Tab键处理，允许输入制表符
        simpleJsonEditor.addEventListener('keydown', function (e) {
            if (e.key === 'Tab') {
                e.preventDefault();

                // 获取光标位置
                const start = this.selectionStart;
                const end = this.selectionEnd;

                // 插入制表符（两个空格）
                this.value = this.value.substring(0, start) + '  ' + this.value.substring(end);

                // 移动光标到插入后的位置
                this.selectionStart = this.selectionEnd = start + 2;
            }
        });
    }

    // 格式化JSON
    function formatJson() {
        try {
            const currentValue = simpleJsonEditor.value;
            const parsed = JSON.parse(currentValue);
            const formatted = JSON.stringify(parsed, null, 2);
            simpleJsonEditor.value = formatted;
            mcpConfigTextarea.value = formatted;
            addSystemMessage('✅ JSON已格式化');
        } catch (e) {
            addSystemMessage('⚠️ JSON格式错误，无法格式化', true);
            console.error('格式化JSON出错:', e);
        }
    }

    // 恢复默认配置
    function restoreDefaultConfig() {
        const defaultConfig = JSON.stringify(defaultMcpConfig, null, 2);
        simpleJsonEditor.value = defaultConfig;
        mcpConfigTextarea.value = defaultConfig;
        addSystemMessage('✅ 已恢复默认MCP配置');
    }

    // 保存设置
    function saveSettings() {
        try {
            // 验证JSON格式
            const configValue = simpleJsonEditor.value;
            JSON.parse(configValue);
            mcpConfigTextarea.value = configValue;

            // 显示保存成功消息
            addSystemMessage('✅ 设置已保存');
            // 切换到聊天标签页
            switchToTab('chat');
        } catch (e) {
            addSystemMessage('⚠️ MCP配置JSON格式错误，无法保存', true);
            console.error('保存设置时出错:', e);
        }
    }

    // 切换到指定标签页
    function switchToTab(tabId) {
        tabs.forEach(t => t.classList.remove('active'));
        tabPanels.forEach(panel => panel.classList.remove('active'));

        const tab = document.querySelector(`.tab[data-tab="${tabId}"]`);
        if (tab) {
            tab.classList.add('active');
            document.getElementById(`${tabId}-panel`).classList.add('active');
        }
    }

    // 处理标签页切换
    tabs.forEach(tab => {
        tab.addEventListener('click', () => {
            // 移除所有标签的active类
            tabs.forEach(t => t.classList.remove('active'));
            // 给当前标签添加active类
            tab.classList.add('active');

            // 获取对应面板
            const panelId = `${tab.dataset.tab}-panel`;
            // 隐藏所有面板
            tabPanels.forEach(panel => panel.classList.remove('active'));
            // 显示选中的面板
            document.getElementById(panelId).classList.add('active');
        });
    });

    // 保存聊天历史记录
    let messageHistory = [];

    // 获取当前页面的基础URL
    const baseUrl = window.location.origin;

    // 判断是否在测试模式
    let isTestMode = false;

    // 添加用户消息到聊天界面
    function addUserMessage(message) {
        const messageElement = document.createElement('div');
        messageElement.className = 'message user-message';
        messageElement.textContent = message;
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // 添加到历史记录
        messageHistory.push({ role: 'user', content: message });
    }

    // 添加机器人消息到聊天界面
    function addBotMessage(message) {
        const messageElement = document.createElement('div');
        messageElement.className = 'message bot-message';
        // 使用marked.js解析并渲染Markdown
        messageElement.innerHTML = marked.parse(message);
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // 添加到历史记录
        messageHistory.push({ role: 'assistant', content: message });

        return messageElement;
    }

    // 添加系统消息，不计入对话历史
    function addSystemMessage(message, isError = false) {
        const messageElement = document.createElement('div');
        messageElement.className = `message system-message ${isError ? 'error-message' : ''}`;
        messageElement.innerHTML = marked.parse(message);
        chatMessages.appendChild(messageElement);
        chatMessages.scrollTop = chatMessages.scrollHeight;

        // 设置自动消失
        if (!isError) {
            setTimeout(() => {
                if (messageElement.parentNode === chatMessages) {
                    messageElement.style.opacity = '0';
                    setTimeout(() => {
                        if (messageElement.parentNode === chatMessages) {
                            chatMessages.removeChild(messageElement);
                        }
                    }, 500);
                }
            }, 3000);
        }
    }

    // 流式处理函数
    async function handleStream(response) {
        const reader = response.body.getReader();
        const decoder = new TextDecoder();
        let streamContent = '';
        let messageElement = null;
        let toolExecutionComplete = false;
        // 用于单独显示工具调用状态的元素
        let toolStatusElement = null;

        try {
            while (true) {
                const { done, value } = await reader.read();
                if (done) break;

                const chunk = decoder.decode(value);
                const lines = chunk.split('\n\n');

                for (const line of lines) {
                    if (line.trim() === '') continue;
                    if (line.trim() === 'data: [DONE]') continue;

                    if (line.startsWith('data: ')) {
                        try {
                            const jsonData = JSON.parse(line.slice(5));

                            // 处理错误消息
                            if (jsonData.error) {
                                addSystemMessage(`⚠️ 服务器错误: ${jsonData.error}`, true);
                                continue;
                            }

                            // 处理自定义工具执行完成事件
                            if (jsonData.tool_execution_complete) {
                                toolExecutionComplete = true;

                                // 获取工具名称、参数和结果
                                const toolName = jsonData.tool_name || "未知工具";
                                const toolArgs = jsonData.tool_arguments || {};
                                const toolResult = jsonData.tool_result || "无结果";

                                // 移除工具状态指示元素
                                if (toolStatusElement && toolStatusElement.parentNode === chatMessages) {
                                    chatMessages.removeChild(toolStatusElement);
                                    toolStatusElement = null;
                                }

                                // 创建工具调用的详细信息
                                let toolDetailsHtml = `
                                <div class="tool-execution">
                                    <div class="tool-header" onclick="toggleToolDetails(this)">
                                        <span class="tool-toggle">▶</span> ✅ 工具 <b>${toolName}</b> 执行完成 <span class="tool-hint">(点击查看详情)</span>
                                    </div>
                                    <div class="tool-details collapsed">
                                        <div class="tool-args">
                                            <b>参数:</b>
                                            <pre>${JSON.stringify(toolArgs, null, 2)}</pre>
                                        </div>
                                        <div class="tool-result">
                                            <b>结果:</b>
                                            <pre>${typeof toolResult === 'object' ? JSON.stringify(toolResult, null, 2) : toolResult}</pre>
                                        </div>
                                    </div>
                                </div>`;

                                // 处理之前的消息，从内容中移除工具调用提示
                                if (messageElement && streamContent.includes("*正在使用工具...*")) {
                                    streamContent = streamContent.replace(/\n\n\*正在使用工具\.\.\.\*$/g, '');
                                    if (streamContent.trim() === '') {
                                        // 如果消息为空，移除消息元素
                                        if (messageElement.parentNode === chatMessages) {
                                            chatMessages.removeChild(messageElement);
                                        }
                                        messageElement = null;
                                    } else {
                                        // 否则更新消息内容
                                        messageElement.innerHTML = marked.parse(streamContent);
                                    }
                                }

                                // 创建专门的工具执行详情元素
                                const toolDetailElement = document.createElement('div');
                                toolDetailElement.className = 'message tool-detail-message';
                                toolDetailElement.innerHTML = toolDetailsHtml;
                                chatMessages.appendChild(toolDetailElement);
                                chatMessages.scrollTop = chatMessages.scrollHeight;

                                // 创建新的消息元素，用于显示工具执行后的回复
                                messageElement = document.createElement('div');
                                messageElement.className = 'message bot-message';
                                chatMessages.appendChild(messageElement);
                                streamContent = '';
                                continue;
                            }

                            // 处理工具执行错误事件
                            if (jsonData.tool_execution_error) {
                                const errorMsg = jsonData.error || '未知错误';

                                // 移除工具状态指示元素
                                if (toolStatusElement && toolStatusElement.parentNode === chatMessages) {
                                    chatMessages.removeChild(toolStatusElement);
                                    toolStatusElement = null;
                                }

                                addSystemMessage(`⚠️ 工具执行失败: ${errorMsg}`, true);

                                // 如果是参数缺失错误，添加更友好的提示
                                if (errorMsg.includes('所需参数缺失')) {
                                    addSystemMessage('💡 提示: 请在问题中提供更多信息，例如位置、日期等具体细节。', false);
                                }

                                // 移除"正在使用工具..."的提示
                                if (messageElement && streamContent.includes("*正在使用工具...*")) {
                                    streamContent = streamContent.replace(/\n\n\*正在使用工具\.\.\.\*$/g, '');
                                    if (streamContent.trim() === '') {
                                        // 如果消息为空，移除消息元素
                                        if (messageElement.parentNode === chatMessages) {
                                            chatMessages.removeChild(messageElement);
                                        }
                                        messageElement = null;
                                    } else {
                                        // 否则更新消息内容
                                        messageElement.innerHTML = marked.parse(streamContent);
                                    }
                                }

                                continue;
                            }

                            // 处理流式返回的内容片段
                            if (jsonData.choices && jsonData.choices.length > 0) {
                                const delta = jsonData.choices[0].delta;

                                // 如果有内容增量，添加到当前消息
                                if (delta && delta.content) {
                                    streamContent += delta.content;

                                    // 如果还没有创建消息元素，先创建一个
                                    if (!messageElement) {
                                        messageElement = document.createElement('div');
                                        messageElement.className = 'message bot-message';
                                        chatMessages.appendChild(messageElement);
                                    }

                                    // 更新内容，使用Markdown解析
                                    messageElement.innerHTML = marked.parse(streamContent);
                                    chatMessages.scrollTop = chatMessages.scrollHeight;
                                }

                                // 处理工具调用
                                if (delta && delta.tool_calls) {
                                    // 检查是否已经有状态元素
                                    if (!toolStatusElement) {
                                        // 从正文中删除"正在使用工具..."提示，改为使用独立状态元素
                                        if (streamContent.includes('正在使用工具...')) {
                                            streamContent = streamContent.replace(/\n\n\*正在使用工具\.\.\.\*$/g, '');
                                            if (messageElement) {
                                                messageElement.innerHTML = marked.parse(streamContent);
                                            }
                                        }

                                        // 创建独立的工具调用状态元素
                                        toolStatusElement = document.createElement('div');
                                        toolStatusElement.className = 'message tool-status-message';
                                        toolStatusElement.innerHTML = `
                                            <div class="tool-status">
                                                <span class="loading-dots"></span>
                                                <span class="tool-status-text">正在调用外部工具...</span>
                                            </div>
                                        `;
                                        chatMessages.appendChild(toolStatusElement);
                                        chatMessages.scrollTop = chatMessages.scrollHeight;
                                    }
                                }
                            }
                        } catch (e) {
                            console.error('解析流数据出错:', e);
                        }
                    }
                }
            }

            // 流结束，清理工作

            // 移除工具状态指示元素（如果还存在）
            if (toolStatusElement && toolStatusElement.parentNode === chatMessages) {
                chatMessages.removeChild(toolStatusElement);
                toolStatusElement = null;
            }

            // 将完整内容添加到历史记录
            if (streamContent && messageElement) {
                // 移除"正在使用工具..."提示，不显示在最终消息中
                streamContent = streamContent.replace(/\n\n\*正在使用工具\.\.\.\*$/g, '');

                // 检查清理后的内容是否为空
                if (streamContent.trim() !== '') {
                    messageElement.innerHTML = marked.parse(streamContent);
                    messageHistory.push({ role: 'assistant', content: streamContent });
                } else {
                    // 如果只有工具使用提示，移除整个消息元素
                    if (messageElement.parentNode === chatMessages) {
                        chatMessages.removeChild(messageElement);
                    }
                }
            }

        } catch (error) {
            console.error('读取流出错:', error);
            // 确保移除工具状态指示元素
            if (toolStatusElement && toolStatusElement.parentNode === chatMessages) {
                chatMessages.removeChild(toolStatusElement);
            }
            addSystemMessage(`读取响应时出错: ${error.message}`, true);
        }
    }

    // 发送消息到API
    async function sendMessage(message) {
        try {
            // 获取MCP配置
            let mcpConfig = null;
            try {
                if (mcpConfigTextarea.value.trim()) {
                    mcpConfig = JSON.parse(mcpConfigTextarea.value);

                    // 验证mcpConfig格式是否正确
                    if (!mcpConfig.mcpServers) {
                        addSystemMessage('⚠️ MCP配置必须包含mcpServers字段', true);
                        return;
                    }
                }
            } catch (e) {
                console.error('MCP配置解析失败:', e);
                addSystemMessage('⚠️ MCP配置JSON格式错误，将不使用工具功能', true);
                return;
            }

            // 获取当前选择的模型
            const selectedModel = modelSelect.value;

            // 准备请求数据 - 复制一份消息历史用于请求
            // 注意: 流式响应中工具调用的历史记录将由后端管理，但我们需要更新本地历史以便进行后续对话
            const requestHistory = JSON.parse(JSON.stringify(messageHistory));

            const requestData = {
                messages: requestHistory,
                model: selectedModel,
                stream: true  // 启用流式响应
            };

            if (mcpConfig) {
                requestData.mcp_config = mcpConfig;
            }

            // 显示加载状态
            const loadingElement = document.createElement('div');
            loadingElement.className = 'message bot-message loading';
            loadingElement.textContent = '思考中...';
            chatMessages.appendChild(loadingElement);

            // 发送请求 - 使用绝对路径
            const response = await fetch(`${baseUrl}/api/chat`, {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });

            // 移除加载状态
            chatMessages.removeChild(loadingElement);

            if (!response.ok) {
                // 尝试解析错误响应
                let errorDetail = '';
                try {
                    const errorData = await response.json();
                    errorDetail = errorData.detail || await response.text();
                } catch (e) {
                    errorDetail = await response.text();
                }

                // 检查是否是API密钥错误
                if (errorDetail.includes('ARK_API_KEY') || errorDetail.includes('API密钥')) {
                    isTestMode = true;
                    addSystemMessage('⚠️ 正在测试模式下运行，未设置API密钥。某些功能可能不可用。', true);
                }

                throw new Error(`API错误: ${response.status} - ${errorDetail}`);
            }

            // 检查返回的Content-Type
            const contentType = response.headers.get('Content-Type');

            if (contentType && contentType.includes('text/event-stream')) {
                // 处理流式响应
                await handleStream(response);
            } else {
                // 处理非流式响应
                const data = await response.json();

                // 检查是否是测试响应
                if (data.id === 'test-response') {
                    isTestMode = true;
                    addSystemMessage('⚠️ 正在测试模式下运行，未设置API密钥。某些功能可能不可用。', true);
                }

                // 处理响应
                if (data.choices && data.choices.length > 0) {
                    const message = data.choices[0].message;
                    if (message && message.content) {
                        addBotMessage(message.content);
                    }
                }
            }
        } catch (error) {
            console.error('发送消息出错:', error);
            addSystemMessage(`发送消息时出错: ${error.message}`, true);
        }
    }

    // 添加工具调用切换功能
    window.toggleToolDetails = function (element) {
        const detailsContainer = element.nextElementSibling;
        const toggleIcon = element.querySelector('.tool-toggle');
        const isCollapsed = detailsContainer.classList.contains('collapsed');

        // 切换展开/折叠状态
        if (isCollapsed) {
            detailsContainer.classList.remove('collapsed');
            toggleIcon.textContent = '▼';
        } else {
            detailsContainer.classList.add('collapsed');
            toggleIcon.textContent = '▶';
        }
    };

    // 检查服务器健康状态
    async function checkHealth() {
        try {
            const response = await fetch(`${baseUrl}/api/health`);
            if (response.ok) {
                console.log('服务器健康状态正常');
                return true;
            } else {
                console.error('服务器健康状态异常');
                addSystemMessage('⚠️ 无法连接到服务器，请检查您的网络连接或服务器状态。', true);
                return false;
            }
        } catch (error) {
            console.error('健康检查出错:', error);
            addSystemMessage('⚠️ 服务器连接失败，请检查您的网络连接。', true);
            return false;
        }
    }

    // 设置Enter键发送消息
    userMessageInput.addEventListener('keydown', (e) => {
        // 检查是否按下了Enter键且没有按下Shift键
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault(); // 阻止默认行为（换行）
            const message = userMessageInput.value.trim();
            if (message) {
                sendButton.click(); // 触发发送按钮点击事件
            }
        }
    });

    // 设置发送按钮点击事件
    sendButton.addEventListener('click', async () => {
        const message = userMessageInput.value.trim();
        if (!message) return;

        // 添加用户消息到聊天界面
        addUserMessage(message);

        // 清空输入框
        userMessageInput.value = '';

        // 发送消息到API
        await sendMessage(message);
    });

    // 启动应用
    async function initialize() {
        // 添加欢迎消息
        addBotMessage('👋 欢迎使用大模型与MCP集成演示！我可以帮你查询天气或回答其他问题。请在下方输入框中输入您的问题。');

        // 初始化配置编辑器
        initConfigEditor();

        // 检查服务器健康状态
        await checkHealth();
    }

    // 初始化应用
    initialize();
}); 