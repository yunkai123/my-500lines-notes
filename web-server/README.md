# Web Sever

- **项目名称：Web Server**
- **原作者：Greg Wilson**
- **环境：Python3+**

本项目代码目录中是一个简单的 Web 服务器，代码是分段开发的，每个子目录中依次包含一个更复杂的版本，最后一章会讨论各个版本之间的变化以解释每个版本的特点，并演示每个版本的效果来说明为什么要做这些修改。

*   00-hello-web: 响应固定的报文。
*   01-echo-request-info: 显示 HTTP 请求报文头。
*   02-serve-static: 包含静态文件和目录。
*   03-errcode-pathnorm: 错误处理，路径规范化和日志记录。
*   04-mimetypes: MIME 类型。
*   05-simple-cgi: 基本 CGI 脚本。
*   06-sockets: 用我们自己的套接字/解析代码替换Python HTTP库。（本部分尚未实现）