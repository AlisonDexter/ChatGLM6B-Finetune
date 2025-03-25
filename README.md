# 颐年智伴

本项目是基于ChatGLM3的智能语音助手，旨在为老年人提供更加便捷和智能的语音交互体验。基于大数据、自然语言处理大模型、自动语音识别（ASR）、文本转语音（TTS），前后端和数据库等技术打造了一款专属于老年人群体的智能对话系统。，

## 目录

- [功能](#功能)
- [技术栈](#技术栈)
- [安装与使用](#安装与使用)
- [API 说明](#api-说明)


## 功能

- 在网页端实现登录注册功能
- 与模型通过文本输入的方式进行对话
- 语音识别功能，用户可以通过麦克风输入问题，再提交给大模型
- 聊天记录保存
- 语音合成功能，将模型输出的文本转换为语音

## 技术栈

- Python
- Flask
- HTML/CSS/JavaScript
- TTS 库（`EmotiVoice`）
- 数据库（MySQL）
- 语音识别模型（`SenseVoice`）
- 对话模型（`ChatGLM3`）

## 安装与使用


1. 创建chatGLM虚拟环境并激活：
   ```bash
   create -n chatGLM python=3.8
   conda activate chatGLM
   ```



2. 安装依赖：
   ```bash
   conda activate chatGLM
   pip install -r requirements.txt
   ```
   ```bash
   conda activate whisper
   pip install -r requirements.txt
   ```

3. 配置数据库：
   - 创建数据库并运行迁移脚本。

4. 在github找到sensevoice和Emotivoice，按照.md配置环境：
   ```
   https://github.com/netease-youdao/EmotiVoice.git
   https://github.com/FunAudioLLM/SenseVoice.git
   ```

5. 运行应用：
   ```bash
   python app.py
   python openaiapi.py   // 开启TTS的API
   python api.py    //开启ASR的API
   ```

6. 打开浏览器，访问 `http://127.0.0.1:5000`。


