# 恢复运行入口

当前提交数为0。先执行 `python3 scripts/study04_analysis.py verify`，读取access-block.json与run-order.json。恢复浏览器连接并确认普通High后，按固定顺序将tasks对应文件及execution-wrapper.txt完整提交到独立对话。不要上传evaluation目录。不得重新生成任务或替换材料。

每项保存完整raw及metadata JSON；metadata必须包含conversation_url、visible_model、visible_mode、submitted_utc、observed_complete_utc和submitted_task_sha256（任务文件自身哈希）。完整提交哈希另见run-order。只记录实际可观察设置，精确型号或tokens不可得时不猜测。

使用 `python3 scripts/study04_analysis.py import --id ANS01 --raw /absolute/raw.txt --metadata /absolute/metadata.json` 导入对应项。导入器不改事实、不填答案、不覆盖已有结果。run-state.json是准备时快照，恢复后须依据runs中的实际记录更新台账，不把旧快照当成未执行证明。每次提交前检查该ID是否已有raw/对话，避免重复。最后一次性按evaluation-rules.json审阅；技术失败独立保存null。
