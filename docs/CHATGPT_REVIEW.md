# Codex 与 ChatGPT 网页版的协作

GitHub 保存可追踪的版本；ChatGPT 阅读仓库并提出建议；Codex 在授权后实施建议、验证、
更新文件并推送。仓库不会自动把网页聊天写回来，也没有后台付费API或自动推送任务。

入口是 ../review/START_HERE.md；完整审阅请求是 ../review/REVIEW_REQUEST.md。
其中记录内容快照编号、当前结果、应读文件和原文链接。请让网页先复述快照编号，
并区分“文件已读”“只读到摘要”“链接打不开”。不能把没读到的代码当作已review。

当前审阅分支为`research/rules-and-verdict`，入口是
[该分支的START_HERE](https://github.com/ChanStormstout/legal-fact-benchmark/blob/research/rules-and-verdict/review/START_HERE.md)。
仓库默认分支仍是`main`；仅提供仓库首页可能读到已有发布版本。
请同时指定分支和内容快照；固定审阅版本时用提交SHA替换URL中的分支名。

优先在ChatGPT支持的GitHub连接中授权 ChanStormstout/legal-fact-benchmark，然后指定
仓库和文件路径。可用模式随账号和界面不同；官方说明该连接按需读取已授权内容，
不是自动同步索引，网页连接只读，代码推送由Codex完成。
来源：[OpenAI官方说明](https://help.openai.com/en/articles/11145903-connecting-github-to-chatgpt)。

未连接GitHub或读取不完整时，可以分享公开raw链接，或下载并上传审阅文件：
review/CODE.md、review/RESULTS.md及四份review/SOURCES_*.md分别保存代码、全部预定题结果、
完整判决。全文依据来自SOURCES或原实验文件，不能只看RESULTS中的引文就声称核验全文。
本地 `python3 scripts/repository_bridge.py export` 另生成ZIP归档，便于下载或手工解包。
ChatGPT能否直接解析ZIP取决于该对话工具；不能解析时上传其中的Markdown文件即可。

网页意见以问题、文件/行号、证据、修改建议和应验证的测试表达。结构化反馈格式见
../review/feedback/schema.json。网页回复可原样保存为review/feedback中的新文件，或由
用户写入GitHub Issue；同一内容快照下的旧意见不能当作已解决。这里没有自动接受或
实施网页建议，也没有自动发评论的工具。

每次已授权更新后：修改相应文档与版本化实验目录，更新CHANGELOG和EXPERIMENTS，执行
`python3 scripts/repository_bridge.py prepare`，检查新增公开清单，然后执行
`python3 scripts/repository_bridge.py sync --message "Describe the concrete change"`。
sync先核对当前分支与登记目标，再生成文件、核验哈希、仅提交白名单中的变更并推送
`docs/repository-artifacts.json`登记的分支，当前为`research/rules-and-verdict`；其他已暂存文件会导致
停止。失败时保留提交，不强推、不回滚、不覆盖远端。正式实验仍须遵守其冻结规则。
