# 超星平台题目收录脚本

此 Python 脚本用于从超星学习通平台收集和处理题目，并将其存储到 MySQL 数据库中。以下是脚本功能和使用的概述。

## 功能

- **自动登录**：使用 AES 和 DES 加密方式在超星平台上进行用户认证，保障登录安全。
- **课程获取**：获取用户已注册的课程列表及其详细信息。
- **题目提取**：从课程章节中抓取题目、选项和答案（包括单选题、多选题和判断题）。
- **答案处理**：处理和格式化答案，包括处理判断题和合并选项内容。
- **数据库存储**：将题目数据（类型、内容、答案和选项）存储到 MySQL 数据库，检查避免重复并更新现有记录。
- **错误处理**：妥善处理网络问题、数据缺失和未完成题目等情况。

## 依赖项

- Python 库：`requests`, `pyDes`, `pycryptodome`, `lxml`, `beautifulsoup4`, `pymysql`, `re`, `time`, `binascii`, `base64`
- MySQL 数据库：用于存储题目数据

## 核心函数

- `sign_in(username, password)`：登录超星平台并获取 cookies。
- `get_course(cookie)`：获取用户课程列表并返回课程字典。
- `deal_course(url)`：处理课程 URL，重定向并提取相关参数。
- `add_misson(url)`：获取课程章节的任务点（已完成或未完成）。
- `get_tm(tm_get_url)`：解析章节中的题目 URL，提取题目和答案。
- `get_list_tm(url)`：处理单页题目，解析题目类型、内容、答案和选项。
- `get_mysql(data_type, tm, da, result, true_result, optionTexts)`：将题目数据存储或更新到 MySQL 数据库。
- `get_answer(list_work, tm)`：通过外部 API 获取正确答案并存储。

## 使用方法

1. 配置 MySQL 数据库连接参数（`pysql`, `mysql_port`, `mysql_user`, `mysql_password`, `mysql_database`）。
2. 调用 `sign_in` 函数，传入超星账号和密码以获取 cookies。
3. 使用 `get_course` 获取课程列表，选择目标课程。
4. 通过 `deal_course` 和 `add_misson` 获取章节任务点。
5. 使用 `get_tm` 和 `get_list_tm` 提取题目并存储到数据库。
6. 如果需要正确答案，可通过 `get_answer` 调用外部 API（需提供有效 token）。

## 注意事项

- 确保网络稳定，避免请求超时或连接失败。
- 数据库表需包含字段：`type`, `tm`, `da`, `courseId`, `optionTexts`。
- 脚本中的外部 API 调用（`get_answer`）需配置有效 token，否则无法获取正确答案。
- 判断题答案会自动转换为 '√' 或 '×'，便于存储和展示。

## 示例输出

运行脚本后，控制台会显示：

- 已开启的课程列表
- 每个课程的章节完成状态
- 提取的题目类型、内容、答案及是否正确
- 数据库插入或更新的日志信息

此脚本适用于需要批量收集超星平台题目并构建题库的用户，适合教育机构或个人学习使用。