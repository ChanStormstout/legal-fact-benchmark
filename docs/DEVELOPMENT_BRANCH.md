# 规则与判决方向的开发分支

当前分支：`research/rules-and-verdict`。
起点：`9ddc35d0a3b4b60fde11b3f669139ed38469aac3`，包括已发布的代码、历史实验和用户更正后的研究目标。
`main`继续保留该发布版本；创建开发分支不改变仓库默认分支，不自动合并到main。

新方向复用已有来源、抽取、字段依赖和关系执行模块，逐步研究规则获取、适用法源检索和逐请求判断。
新的方法和实验使用新的版本目录；已有标注、失败输出、冻结配置与方法快照保持原样。
本次仅建立分支和同步入口，没有启动模型运行、增加标注或实现法律推理算法。

## 在本地开发和同步

用户于2026-10-02明确授权：每轮实验运行结束后，更新报告、状态和审阅包，检查发布清单并通过核验，然后提交并推送到当前登记的开发分支，无需再次确认。这个授权包括本次V7；仍须保留失败结果和冻结材料，不发布环境、权重、凭据或无关文件。若后续任务明确要求暂不推送，以后续要求为准。

V7原报告中的“未推送”记录的是实验结束时的状态；随后用户追加了上述发布授权，不改写原报告或冻结记录。

当前聊天工作目录已切换到开发分支，不另建Space或复制项目。此目录内的其他聊天若编辑同一仓库，
也会看到这个分支。若以后需要同时改两个不同分支，应使用不同的Git worktree，即各自的工作目录；
本次没有建立第二个worktree。未完成的`legal_bench/local_chunk_v11.py`继续在本地保存，并从公开清单排除。

```sh
git switch research/rules-and-verdict
python3 scripts/repository_bridge.py prepare
python3 scripts/repository_bridge.py verify
python3 scripts/repository_bridge.py sync --message "Describe the concrete change"
```

发布目标登记在`docs/repository-artifacts.json`。同步脚本先检查仓库和当前分支，只有与登记目标一致
才会生成、提交并推送；不会自动推送到main。新增输出目录先登记，再检查PUBLICATION与MANIFEST。
运行环境、权重、界面截图、凭据和未登记的本地数据不进入公开仓库。

## 给ChatGPT网页版审阅

分享[当前分支审阅入口](https://github.com/ChanStormstout/legal-fact-benchmark/blob/research/rules-and-verdict/review/START_HERE.md)，
并指定`research/rules-and-verdict`及内容快照。入口、审阅请求和MANIFEST中的raw链接均指向该分支。
固定版本时，将链接中的`research/rules-and-verdict`替换为已推送的提交SHA。
GitHub链接无法完整读取时，可上传同一快照的Markdown分卷或导出的审阅包。

网页建议仍须对应具体文件、来源和证据。是否采纳建议、启动实验、修订方法和合并到main，
继续遵守每次任务的授权及冻结要求；创建开发分支不扩大实验权限。
