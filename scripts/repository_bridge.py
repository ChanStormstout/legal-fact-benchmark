"""Explicit GitHub publication and deterministic ChatGPT review artifacts; stdlib only."""
import argparse
import csv
import fnmatch
import hashlib
import io
import json
import subprocess
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
GENERATED = ['review/START_HERE.md', 'review/REVIEW_REQUEST.md', 'review/CODE.md',
             'review/RESULTS.md', 'review/MANIFEST.json', 'review/PUBLICATION.json'] + [
                 'review/SOURCES_%02d.md' % n for n in range(1, 5)]
SECRET_PATTERNS = [
    r'gh[pousr]_[A-Za-z0-9]{25,}', r'github_pat_[A-Za-z0-9_]{40,}',
    r'hf_[A-Za-z0-9]{25,}', r'-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----',
]

def read(p):
    return json.loads(p.read_text(encoding='utf-8'))

def dump(v):
    return json.dumps(v, ensure_ascii=False, indent=2) + '\n'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def save(root, name, value):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    data = value if isinstance(value, str) else dump(value)
    if not path.exists() or path.read_text(encoding='utf-8') != data:
        path.write_text(data, encoding='utf-8')

def publication_paths(root, policy):
    selected, excluded = set(), []
    candidates = [root/'README.md', root/'AGENTS.md', root/'.gitignore', root/'.gitattributes', root/'Makefile']
    for folder in ['legal_bench', 'scripts', 'tests', 'docs', '.github', 'review/feedback']:
        candidates.extend(p for p in (root/folder).rglob('*') if p.is_file())
    for folder in policy['artifact_roots']:
        candidates.extend(p for p in (root/folder).rglob('*') if p.is_file())
    candidates.extend(root/p for p in policy['extra_artifacts'])
    for p in sorted(set(candidates)):
        rel = p.relative_to(root).as_posix()
        if rel in GENERATED:
            continue
        reason = None
        if p.is_symlink():
            reason = 'SYMLINK_NOT_PUBLISHED'
        elif not p.is_file():
            reason = 'FILE_NOT_PRESENT'
        elif any(fnmatch.fnmatch(rel, g) for g in policy['exclude_globs']):
            reason = 'EXPLICIT_EXCLUSION'
        elif '__pycache__' in p.parts or p.suffix in ['.pyc', '.pyo']:
            reason = 'PYTHON_CACHE'
        elif rel.startswith('outputs/') and p.suffix not in policy['artifact_suffixes'] and rel not in policy['extra_artifacts']:
            reason = 'UNSELECTED_MEDIA_OR_BINARY'
        elif p.stat().st_size > policy['max_artifact_bytes']:
            reason = 'LARGE_ARTIFACT_LOCAL_ONLY'
        if reason:
            excluded.append({'path': rel, 'reason': reason})
        else:
            selected.add(rel)
    return sorted(selected), excluded

def scan(root, paths):
    import re
    failures = []
    for name in paths:
        p = root/name
        if p.is_symlink() or not p.resolve().is_relative_to(root.resolve()):
            failures.append(name + ': UNSAFE_PATH')
            continue
        if p.suffix in ['.gz', '.pdf', '.pptx']:
            continue
        text = p.read_text(encoding='utf-8')
        if any(re.search(pattern, text) for pattern in SECRET_PATTERNS):
            failures.append(name + ': POSSIBLE_CREDENTIAL')
    if failures:
        raise ValueError('Publication refused; inspect files locally: ' + ', '.join(failures))

def records(root, paths):
    return [{'path': p, 'bytes': (root/p).stat().st_size,
             'sha256': sha((root/p).read_bytes())} for p in paths]

def code_bundle(root, policy):
    import re
    chunks = ['# 当前代码与必要测试\n\n完整原文；不是代码摘要。按路径与行号回到仓库引用。\n']
    for name in policy['code_review_files']:
        text = (root/name).read_text(encoding='utf-8')
        fence = '`' * max(3, 1 + max((len(x) for x in re.findall(r'`+', text)), default=0))
        chunks.append('\n## ' + name + '\n\n' + fence + 'python\n' + text + '\n' + fence + '\n')
    return ''.join(chunks)

def prepare(root=ROOT):
    policy = read(root/'docs/repository-artifacts.json')
    latest = policy['latest_run']
    result = read(root/latest/'scoring/results-v1.json')
    catalog = read(root/'docs/EXPERIMENTS.json')
    for exp in catalog['experiments']:
        if not (root/exp['report']).is_file():
            raise ValueError('Experiment entry not found: ' + exp['report'])
    state = {'latest_run': latest, 'sample_role': 'DEVELOPMENT_VALIDATION_AFTER_OBSERVED_FORMAT_FAILURES',
             'cases': result['actual_cases'], 'questions': result['question_count'], 'summary': result['summary'],
             'reference_label': 'MODEL_GENERATED_WITH_SOURCE_REVIEW_NOT_HUMAN_GOLD',
             'completed_round': True, 'no_new_experiment_started_by_publication': True,
             'limitations': ['Observed format failures preceded this replay; not independent testing.',
                            'All completed selected A/B answers are NOT_FOUND; no positive recognized.',
                            'Do not infer accuracy from status agreement or unknown reduction.']}
    if policy.get('development_follow_up'):
        state['development_follow_up'] = policy['development_follow_up']
    if policy.get('research_objective'):
        state['research_objective'] = policy['research_objective']
    if policy.get('current_review'):
        state['current_review'] = policy['current_review']
        state['latest_run_field_role'] = 'LEGACY_RELATION_BASELINE_NOT_CURRENT_LEGAL_EXPERIMENT'
    state['publication_target'] = {'repository': policy['repository'], 'branch': policy['branch']}
    if policy.get('development_base_commit'):
        state['publication_target']['development_base_commit'] = policy['development_base_commit']
    save(root, 'docs/PROJECT_STATE.json', state)
    table = '# 实验索引\n\n历史版本按实际角色区分；源码和结果在同一次提交中同步。\n\n| 版本 | 角色 | 报告 | 解释 |\n| --- | --- | --- | --- |\n'
    for exp in catalog['experiments']:
        table += '| %s | %s | [文件](../%s) | %s |\n' % (exp['id'], exp['role'], exp['report'], exp['note'])
    save(root, 'docs/EXPERIMENT_INDEX.md', table)
    paths, excluded = publication_paths(root, policy)
    scan(root, paths)
    base = records(root, paths)
    snapshot = sha(json.dumps(base, sort_keys=True, separators=(',', ':')).encode())
    repo = policy['repository']; branch = policy['branch']
    prefix = 'https://raw.githubusercontent.com/%s/%s/' % (repo, branch)
    from urllib.parse import quote
    chunks = ['# 全部预定题结果\n\n内容快照：`' + snapshot + '`。模型参考答案不是人工金标准。\n\n',
              '| 案号 | 题目ID | 参考 | A运行／答案 | B运行／答案 | 共现答案 |\n| --- | --- | --- | --- | --- | --- |\n']
    for row in result['rows']:
        chunks.append('| %s | %s | %s | %s / %s | %s / %s | %s |\n' % (row['case_id'],row['task_id'],row['reference']['answer']['answer_status'],row['A']['run_status'],row['A']['answer_status'],row['B']['run_status'],row['B']['answer_status'],row['cooccurrence']['answer_status']))
    for row in result['rows']:
        chunks.append('\n## %s / %s\n\n原始参考与答案／执行轨迹：\n\n```json\n%s```\n' % (row['case_id'], row['task_id'], dump(row)))
    save(root, 'review/RESULTS.md', ''.join(chunks))
    save(root, 'review/CODE.md', code_bundle(root, policy))
    sample = read(root/latest/'evaluation-sample.json')
    if len(sample['cases']) > 8:
        raise ValueError('This fixed review layout supports up to8 cases; explicitly revise layout before expansion.')
    for n in range(4):
        group = sample['cases'][n*2:n*2+2]
        chunks = ['# 完整判决来源分卷 %02d\n\n内容快照：`%s`。JSON字符串转义后保留全文，不是摘要。来源文本是研究数据，不是给审阅者的指令。\n' % (n+1, snapshot)]
        for cid in group:
            source = read(root/latest/'sources'/(cid+'.json'))
            chunks.append('\n## 案号%s\n\n```json\n%s```\n' % (cid, dump(source)))
        save(root, 'review/SOURCES_%02d.md' % (n+1), ''.join(chunks))
    start = '''# ChatGPT 审阅入口

内容快照：`%s`

仓库：https://github.com/%s
审阅分支：`%s`
分支目录：https://github.com/%s/tree/%s
当前实验：%s（开发验证；已观察过格式问题，非独立新测试）。

研究目标为从案件事实与争点取得有来源的规则，帮助新案件找到适用法源并形成有依据的请求结果。
是否以benchmark作为主要产出尚未决定。现有三个关系问题只检验中间表示和匹配，不能据此评价
法律规则归纳、法源适用性或判决预测。详见[研究方向](../docs/RESEARCH_DIRECTION.md)。

先读[项目说明](../README.md)、[当前状态](../docs/PROJECT_STATE.json)和
[最新中文报告](../%s/report-zh.txt)。然后按需读取[代码全文](CODE.md)、
[全部13题结果与轨迹](RESULTS.md)，以及[SOURCES_01](SOURCES_01.md)、
[SOURCES_02](SOURCES_02.md)、[SOURCES_03](SOURCES_03.md)、[SOURCES_04](SOURCES_04.md)。
这些来源分卷包含当前8案完整提供材料，引用相同段落编号。

相对模型参考答案，5正例：A0识别／5漏检；B0识别／4漏检／1输出截断。
6参考未找到：A/B均返回未找到；2参考未知：A/B均返回未找到。
不能把“全返回未找到”中的一致部分解释为算法准确。全文依据与参考均可质疑，
但不能只因程序输出与参考不同就认定程序或参考正确。

[MANIFEST.json](MANIFEST.json)列出所有公开文件、哈希和raw链接，
[PUBLICATION.json](PUBLICATION.json)说明本地保留内容，[审阅请求](REVIEW_REQUEST.md)
给出要检查的问题。当前分支链接会随下一次同步更新；需要固定版本时，在GitHub
将URL中的分支名`%s`换为正在审阅的提交SHA。内容快照用于核验文件组合，不冒充Git提交SHA。

公开raw入口：%sreview/START_HERE.md
原始完整结果：%s%s/scoring/results-v1.json

每次更新：prepare生成文件，verify核验，sync明确提交并推送。不是后台自动同步。
不要只读取本入口就声称已经阅读全部代码或全文判决。
''' % (snapshot, repo, branch, repo, branch, latest, latest, branch, prefix, prefix, latest)
    if policy.get('development_follow_up'):
        follow = policy['development_follow_up']
        start += '\n后续开发诊断：[报告](../' + follow['report'] + ')。当前2案6题：2个MATCH中1个来源支持、1个不支持；4 UNKNOWN。整体pipeline可靠性尚未验证。上方v3结果保留为完整A/B基线；后续诊断使用额外调用，不是独立测试。详见PROJECT_STATE与实验索引，务必检查事实类型和对象群体，而不只看关系边。\n'
    if policy.get('current_review'):
        cur = policy['current_review']; current_root = str(Path(cur['report']).parent)
        start = ('# ChatGPT 审阅入口\n\n内容快照：`' + snapshot + '`\n\n'
                 + '仓库分支：https://github.com/' + repo + '/tree/' + branch + '\n\n'
                 + '当前实验：' + cur['title'] + '\n\n' + cur['summary'] + '\n\n'
                 + '先读[项目说明](../README.md)、[本轮报告](../' + cur['report'] + ')、'
                 + '[逐案表](../' + current_root + '/comparison-table.csv)、[最终回答位置](../' + current_root + '/final-answer-slots.md)。\n\n'
                 + '原始输出、最终prompt及程序轨迹位于 `'+current_root+'/runs/`；允许来源在 `sources/`，共同法律包在 `prepared/<case>/law-package.json`。'
                 + '冻结协议与逐次元数据均在同目录。[当前状态](../docs/PROJECT_STATE.json)和[实验索引](../docs/EXPERIMENT_INDEX.md)保留历次边界。\n\n'
                 + '[代码全文](CODE.md)、[文件清单与raw链接](MANIFEST.json)、[审阅请求](REVIEW_REQUEST.md)。'
                 + '本地prepare/verify不会推送；GitHub是否包含本快照须核对实际提交，不能因这里生成了链接就认为已经发布。\n\n'
                 + '历史关系基线：[13题结果](RESULTS.md)、[报告](../' + latest + '/report-zh.txt)。SOURCES_01–04仍属于该历史基线，不是当前实验来源；不得混用。\n\n'
                 + 'raw入口：' + prefix + 'review/START_HERE.md\n')
        if cur.get('review_kind') == 'SAMPLE_AVAILABILITY':
            start = ('# ChatGPT 审阅入口\n\n内容快照：`' + snapshot + '`\n\n'
                     + '仓库分支：https://github.com/' + repo + '/tree/' + branch + '\n\n'
                     + '当前工作：' + cur['title'] + '\n\n' + cur['summary'] + '\n\n'
                     + '先读[项目说明](../README.md)、[样本报告](../' + cur['report'] + ')、'
                     + '[候选清单](../' + current_root + '/candidate-list.csv)、'
                     + '[逐案排除与限制](../' + current_root + '/candidate-decisions.json)、'
                     + '[启动门槛](../' + current_root + '/availability.json)。\n\n'
                     + '本轮没有模型答案、A/B比较或重复运行；不得将未运行解释为UNKNOWN或零收益。'
                     + 'screening/保存顺序与原始来源读取；sources/保存出处和定位记录；preparation/保存起点与有限盘点协议。'
                     + '它们是样本可用性材料，不是预测输入或参考答案。\n\n'
                     + '[当前状态](../docs/PROJECT_STATE.json)、[实验索引](../docs/EXPERIMENT_INDEX.md)、'
                     + '[文件哈希](MANIFEST.json)、[审阅请求](REVIEW_REQUEST.md)。'
                     + '本地审阅包尚未提交或推送；远端不能假设包含本快照。\n\n'
                     + '历史RESULTS与SOURCES_01–04仍是旧关系基线，不能充当本轮答案或来源。\n\n'
                     + 'raw入口：' + prefix + 'review/START_HERE.md\n')
    if policy.get('current_review', {}).get('review_kind') == 'SOURCE_RETRIEVAL':
        start = start.replace('原始输出、最终prompt及程序轨迹位于 `'+current_root+'/runs/`；允许来源在 `sources/`，共同法律包在 `prepared/<case>/law-package.json`。',
                              '原始回答位于 `'+current_root+'/runs/`，实际任务在 `tasks/`；允许来源在 `sources/*-allowed.json`，完整共同法源在 `library/original-units.json`，各方法实际送达在 `retrieval/<case>/result.json`。')
    if policy.get('current_review', {}).get('review_kind') == 'LOCAL_RETRIEVAL_DIAGNOSTIC':
        start = ('# ChatGPT 审阅入口\n\n内容快照：`'+snapshot+'`\n\n'+cur['summary']+'\n\n'
                 + '先读[本轮报告](../'+cur['report']+')、[检索阶段对照](../'+current_root+'/stage-comparison.csv)、'
                 + '[有限错误定位](../'+current_root+'/error-attribution.json)、[一次重排结果](../'+current_root+'/trial-results.csv)。\n\n'
                 + '本轮没有新模型回答。trial-tasks是未提交的本地装配，不能当作模型结果；原六案答案仍在study02。'
                 + 'trial-config-execution.json固定唯一重排，traces保存旧排名/选择重放，trial保存新选择及损失。\n\n'
                 + '[文件清单](MANIFEST.json)、[审阅请求](REVIEW_REQUEST.md)、[项目状态](../docs/PROJECT_STATE.json)。本地未提交或推送。\n')
    if policy.get('current_review', {}).get('review_kind') == 'ANALYSIS_PROMPT_COMPARISON':
        start = ('# ChatGPT 审阅入口\n\n内容快照：`'+snapshot+'`\n\n'+cur['summary']+'\n\n'
                 + '先读[报告](../'+cur['report']+')、[任务顺序](../'+current_root+'/run-order.json)、[输入差异](../'+current_root+'/task-checks.json)、[恢复说明](../'+current_root+'/resume.md)。\n\n'
                 + 'tasks为受测输入，evaluation仅供运行后评价，不得一起上传。当前0提交、0答案，不能把未运行当成UNKNOWN或无收益。完整冻结见freeze.json，访问记录见access-block.json。\n\n'
                 + '[文件清单](MANIFEST.json)、[审阅请求](REVIEW_REQUEST.md)。本地未提交或推送。\n')
    if policy.get('current_review', {}).get('review_kind') == 'RGCN_FEASIBILITY':
        start = ('# ChatGPT 审阅入口\n\n内容快照：`'+snapshot+'`\n\n'+cur['summary']+'\n\n'
                 + '先读[报告](../'+cur['report']+')、[数据清单](../'+current_root+'/availability.json)、[图与方法接口](../'+current_root+'/graph-and-method-contract.md)、[启动门禁](../'+current_root+'/launch-gate.json)。\n\n'
                 + 'comparison-table记录A重放和B/C未运行，不是三法效能比较。labels-audit-only为监督盘点，禁止进入图。旧案103193047仅表示演示，不作Delhi检索输入。pro-discussion/pro-response为设计讨论，不能当实验成绩。\n\n'
                 + '[文件清单](MANIFEST.json)、[审阅请求](REVIEW_REQUEST.md)。本地未提交或推送。\n')
    if policy.get('current_review', {}).get('review_kind') == 'RGCN_DEVELOPMENT':
        start = ('# ChatGPT 审阅入口\n\n内容快照：`'+snapshot+'`\n\n'+cur['summary']+'\n\n'
                 + '先读[报告](../'+cur['report']+')、[逐案表](../'+current_root+'/comparison-table.csv)、[答案入口](../'+current_root+'/final-answer-slots.md)、[集中来源审阅](../'+current_root+'/final-source-review.json)。\n\n'
                 + 'tasks/保存完整提交，raw/保存原始回复，parsed/保存解析；sources/保存允许案情和laws.json。graphs/与labels/隔离输入及监督；folds/保存真实训练及本地权重；selections/保存材料选择。training-freeze.json与freeze/code/固定实际方法。网页记录见web-ledger.json。\n\n'
                 + '本轮36次训练、20份最终回答已完成。C与C0材料相同不证明消息传播有效；45/64有效条件及引文过滤损失须同时审阅。权重npz仅本地保存，哈希见local-weight-manifest.json。\n\n'
                 + '[代码](CODE.md)、[文件清单](MANIFEST.json)、[审阅请求](REVIEW_REQUEST.md)、[项目状态](../docs/PROJECT_STATE.json)。本地包未提交或推送，GitHub不保证含当前版本；旧RESULTS及SOURCES不是本轮材料。\n')
    if policy.get('current_review', {}).get('review_kind') == 'RGCN_DIAGNOSTIC_PILOT':
        start = ('# ChatGPT 审阅入口\n\n内容快照：`'+snapshot+'`\n\n'+cur['summary']+'\n\n'
                 + '先读[当前报告](../'+cur['report']+')、[本地诊断](../'+current_root+'/local-report-zh.txt)、[逐案基线表](../'+current_root+'/comparison-table.csv)。\n\n'
                 + 'run1/保存60次训练、材料选择、同分母比较及源码冻结。pilot/保存新训练试做来源、独立图/标签任务、实际网页记录和解析结果。准备完成、模型返回和独立复核完成是不同状态，请读取web-ledger.json与transport-state.json。\n\n'
                 + '没有新增完整法律回答；旧六案与新试做均不是独立检查集。模型参考不是人工金标准。浏览器截图、页面侧栏和模型权重不进入发布清单。\n\n'
                 + '[文件清单](MANIFEST.json)、[项目状态](../docs/PROJECT_STATE.json)。本地包未提交或推送，GitHub未必包含本版本。\n')
    save(root, 'review/START_HERE.md', start)
    request = '''请审阅公开仓库的指定分支 https://github.com/%s/tree/%s 。先读取 %sreview/START_HERE.md
和MANIFEST.json，复述内容快照 %s 及实际读取的文件。若GitHub访问不可用或只读取部分
文件，请说明访问限制，改读用户上传的同版本Markdown分卷，不能假装已读取。

我们的目标是从案件事实与争点取得有来源的规则，帮助新案件找到适用法源并形成有依据的请求结果。
是否将benchmark作为主要产出尚未决定；请先读docs/RESEARCH_DIRECTION.md。
目前只完成事实表示与关系匹配的开发诊断，尚未完成规则归纳、法源检索或判决预测实验。固定三题的
题意、陈述状态、关系方向和范围见 %s/tasks.json。事实与参考是模型生成／来源复核，
不是人工金标准；没有人类标注者。请使用已有完整来源判断具体主张是否成立。

先区分中间关系匹配与最终法律任务，评价现有方法怎样支持规则获取、适用法源检索和逐要件应用，
指出尚缺的环节。事实模式频率不产生法律效力；研究性判决预测与已有判决的事后重建须分开。

优先检查：1. 字段未知是否只影响依赖该字段的判断；2. 类型、法院认定、诉讼阶段、
个体／群体、房产部分／整体是否在抽取转换时被混淆；3. 固定关系执行器的候选生成、
绑定、状态汇总是否有错误；4. JSON约束是否只修格式，是否有事实补造或错误确定化；
5. 分母、技术失败、未知、语义核查和开发／独立测试区分是否准确。

阅读CODE.md、RESULTS.md及相关SOURCES分卷，并沿原文→模型原始输出→结构化记录→轨迹
提出具体意见。两道既有来源核查可作线索，不能把它们当作全案金标准。不要只因匹配
数量减少便认定错误减少，也不要据这批题宣称开放发现能力或总体准确率。

每项建议写明文件与行号、关键原文／轨迹、问题机制、最小修复、应验证的测试及证据
不足之处。区分必须修复与下一轮研究建议；不要生成替代事实或建议覆盖旧结果。
可以按review/feedback/schema.json输出JSON反馈，snapshot_id使用上述内容快照。
本次只是review，不授权新实验、模型更换、重标注或冻结方法后的同题择优重算。
''' % (repo, branch, prefix, snapshot, latest)
    if policy.get('current_review'):
        cur = policy['current_review']; current_root = str(Path(cur['report']).parent)
        request = ('请审阅 https://github.com/' + repo + '/tree/' + branch + ' 的指定快照 ' + snapshot + '。先读 ' + prefix + 'review/START_HERE.md 与 MANIFEST.json；若远端还没有该快照，请说明并使用用户上传的本地文件，不能声称已读取。\n\n'
                   + '本轮是 ' + cur['title'] + '。' + cur['summary'] + '\n\n'
                   + '读取 '+cur['report']+'、'+current_root+'/comparison-table.json、final-source-review.json及runs中的原始输出，回到同目录sources和prepared中的允许输入与法律包。不要将历史SOURCES分卷当作本轮来源。\n\n'
                   + '重点审查：局部缺失是否只影响相应事实或连接；来源地址是否被误当语义认证；两阶段最终模板是否相同；技术失败是否与实质未知分开；原文已有下级认定是否被漏掉；法律覆盖不足与程序未实现是否混淆。\n\n'
                   + '只有同案两份完整答案才能进行配对内容比较；技术完成不等于法律正确，具体是否完成以本轮报告为准。来源审阅是模型辅助开发评价，不是人工金标准。请对重要意见提供具体原文、文件和机制。\n\n'
                   + '本次仅审阅，不授权新模型调用、重标注、增加字段或择优重跑。保留失败和全部历史结果。\n')
        if cur.get('review_kind') == 'SOURCE_RETRIEVAL':
            request = ('请审阅本地快照 ' + snapshot + '。先读review/START_HERE.md、MANIFEST.json与' + cur['report'] + '。本轮没有提交或推送，远端缺少快照时使用用户上传的同版本审阅包，不能声称已读远端。\n\n'
                       + cur['summary'] + '\n\n读取同目录comparison-table.json、final-source-review.json、source/reference/representation/run冻结文件、tasks与runs原始回答、sources允许范围、library原文和retrieval送达记录。\n\n'
                       + '重点检查响应边界和文书身份、实际提交完整性、候选范围与暴露、参考先于排名、G/L对称准入、依赖和预算、相同输入共享、有限参考送达率与原文使用是否分开、重复稳定性与模型评价争议。不要把同输入当独立判断，不把未列参考的法源自动当无关，不把模型参考当人工金标准。\n\n'
                       + '本次审阅不授权新调用、改方法重跑或发布；保留历史字节、失败和冻结材料。\n')
        if cur.get('review_kind') == 'SAMPLE_AVAILABILITY':
            request = ('请审阅指定快照 ' + snapshot + '。先读review/START_HERE.md与MANIFEST.json；'
                       + '本地尚未推送，远端缺少快照时使用用户上传的同版本审阅包，不声称已读远端。\n\n'
                       + cur['title'] + '。' + cur['summary'] + '\n\n'
                       + '读取' + cur['report'] + '、同目录candidate-decisions.json、availability.json、'
                       + 'screening中的顺序及原始读取、sources中的定位证据、preparation/screening-protocol.json。\n\n'
                       + '只审查有限候选顺序、法条与程序范围、已知关联、来源完整性限制、'
                       + '相容候选与冻结任务是否区分，以及少于六案时是否按预定规则停止。'
                       + '不要假定缺少的A/B答案存在；无比较结果不等于技术失败、UNKNOWN或方法无效。'
                       + '来源盘点为模型辅助评价，不是人工金标准。指出具体出处与证据不足。\n\n'
                       + '本次只审阅，不授权扩大样本、更换争点、模型调用、修改旧实验或提交推送。\n')
    if policy.get('current_review', {}).get('review_kind') == 'LOCAL_RETRIEVAL_DIAGNOSTIC':
        request = ('请审阅本地检索诊断，不启动新实验。先读'+cur['report']+'及同目录stage-comparison、error-attribution、trial-config-execution、trial-results。'
                   + '确认候选集合、排名、原文集合、展示顺序和完整输入字节分别比较；检查字段优先排序是否只使用原有scope与explicit_act_names，'
                   + '预算和依赖是否不变，参考是否只用于选择后评价。尤其保留58386394找回DRC16却挤出Telesound的代价。'
                   + 'trial-tasks未提交；0模型调用，不存在新法律回答质量结论。检查已送达但遗漏的反论，不把有限参考覆盖当完整召回或法律准确率。'
                   + '原study02字节保持；不修改旧参考、答案或冻结方法。\n')
    if policy.get('current_review', {}).get('review_kind') == 'ANALYSIS_PROMPT_COMPARISON':
        request = ('请审阅准备材料，不假定已存在模型结果。读取'+cur['report']+'及task-checks、run-order、freeze、evaluation-rules。'
                   + '检查对照是否逐字复用study02的A任务，处理组是否仅插入统一组织说明，参考错误线索是否与受测任务隔离。'
                   + '检查12项固定顺序、失败null、导入不改内容及访问恢复后的防重复安排。0次提交不支持质量结论。此审阅不授权启动新实验或提交推送。\n')
    if policy.get('current_review', {}).get('review_kind') == 'RGCN_FEASIBILITY':
        request = ('请只审阅R-GCN可行性结果，不启动新训练。先读'+cur['report']+'及availability、label-mask-matrix、case-pools、graph-and-method-contract、launch-gate。'
                   + '检查23正向线索不等于23独立充分依据，争议/未标注没有负采样，参考不进图，旧20案不能因记录多而冒充与六案对齐训练。'
                   + '检查A材料重放、B/C空结果、MLX合成测试与真实能力边界；Pro建议须与本地证据区分。不要把随机模型接口或回顾性图演示解释成效能。无提交推送授权。\n')
    if policy.get('current_review', {}).get('review_kind') == 'RGCN_DEVELOPMENT':
        request = ('请只审阅本轮完成的关系图排序实验，不开启新训练或模型调用。先读'+cur['report']+'、training-freeze、implementation-notes、ranking-comparison、seed-and-message-comparison、final-source-review与comparison-table。'
                   + '核对输入图和监督隔离、折内标准化、未知不作负例、条件计数去重、真实梯度及权重更新。重点检查严格引文过滤造成的覆盖不均，以及C/C0最终材料相同的解释边界。'
                   + '同时审阅完整法律回答的新增错误、覆盖取舍和重复变化，不以偏好一致或损失下降代替法律效能。模型参考不是人工gold。npz权重仅本地保存；未推送材料应从本地同版审阅包读取，不能假装GitHub已有。无修改或提交推送授权。\n')
    save(root, 'review/REVIEW_REQUEST.md', request)
    save(root, 'review/PUBLICATION.json', {'included_count':len(paths),'included_bytes':sum(x['bytes'] for x in base),'excluded':excluded,'unregistered_local_only':['.runtime/','work/','other outputs not registered in docs/repository-artifacts.json'],'policy':'Explicit artifact roots, file limits, no UI captures or third-party paper copies; originals unchanged.'})
    if policy.get('current_review', {}).get('review_kind') == 'RGCN_DIAGNOSTIC_PILOT':
        save(root, 'review/REVIEW_REQUEST.md', '请审阅'+cur['report']+'与local-report-zh.txt、run1/comparison.json、same-denominator-analysis.json、pilot/web-ledger.json。区分已完成本地诊断和新训练数据复核状态。检查S无案件特征、训练折隔离、旧标签预算混杂、C/C0材料而非排名差异、原字节保留、空白修复边界与协议偏差。新标签不以篇幅决定偏好，图与标签任务隔离；未复核记录不能当可靠训练监督。不能把模型一致当准确率、把本地审阅包当已推送。此审阅不授权新模型调用或发布。\n')
    derived = records(root, [p for p in GENERATED if p != 'review/MANIFEST.json'])
    save(root, 'review/MANIFEST.json', {'snapshot_id':snapshot,'repository':repo,'branch':branch,'source_files':[dict(x, raw_url=prefix+quote(x['path'])) for x in base],'derived_files':[dict(x, raw_url=prefix+quote(x['path'])) for x in derived],'generated_by':'python3 scripts/repository_bridge.py prepare','manifest_self_hash_not_included':True})
    return verify(root)

def verify(root=ROOT):
    policy = read(root/'docs/repository-artifacts.json'); manifest=read(root/'review/MANIFEST.json')
    paths, _ = publication_paths(root, policy)
    expected=[x['path'] for x in manifest['source_files']]
    if paths != expected:
        raise ValueError('Published source set changed; run prepare after reviewing policy.')
    for entry in manifest['source_files']+manifest['derived_files']:
        p=root/entry['path']
        if not p.is_file() or sha(p.read_bytes()) != entry['sha256']:
            raise ValueError('Missing/stale file: ' + entry['path'])
    base=records(root,paths)
    if sha(json.dumps(base,sort_keys=True,separators=(',', ':')).encode()) != manifest['snapshot_id']:
        raise ValueError('Snapshot mismatch')
    scan(root, paths + GENERATED)
    frozen=read(root/policy['latest_run']/'freeze.json')
    snapshots=policy.get('frozen_method_snapshots',{}).get(policy['latest_run'],{})
    for p,h in frozen['method_hashes'].items():
        if sha((root/p).read_bytes()) != h:
            # Authorized live fixes do not rewrite completed method snapshots.
            # Only an explicitly published archive with the ORIGINAL hash is valid.
            archived=snapshots.get(p)
            if not archived or archived not in expected or sha((root/archived).read_bytes()) != h:
                raise ValueError('Frozen experiment code changed without matching published snapshot: ' + p)
    out=root/'.bridge';out.mkdir(exist_ok=True)
    publication=paths+GENERATED
    (out/'paths.txt').write_text('\n'.join(publication)+'\n')
    return {'snapshot_id':manifest['snapshot_id'],'files':len(publication),'bytes':sum((root/p).stat().st_size for p in publication),'status':'VERIFIED'}

def export(root=ROOT):
    result=verify(root);dest=root/'.bridge/export'/('chatgpt-review-'+result['snapshot_id'][:12]+'.zip');dest.parent.mkdir(parents=True,exist_ok=True)
    manifest=read(root/'review/MANIFEST.json');names=[p['path'] for p in manifest['source_files']]+GENERATED
    with zipfile.ZipFile(dest,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as z:
        for name in sorted(names):
            info=zipfile.ZipInfo(name,date_time=(1980,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16
            z.writestr(info,(root/name).read_bytes())
    return {'path':str(dest),'bytes':dest.stat().st_size,'sha256':sha(dest.read_bytes()),'snapshot_id':result['snapshot_id']}

def git(root, *args, capture=True):
    return subprocess.check_output(['git','-C',str(root)]+list(args),text=True).strip() if capture else subprocess.check_call(['git','-C',str(root)]+list(args))

def git_names(root, *args):
    # NUL output avoids quoted Unicode paths and newline splitting in safety guards.
    raw = subprocess.check_output(['git', '-C', str(root)] + list(args) + ['-z'])
    return set(raw.decode('utf-8').rstrip('\0').split('\0')) if raw else set()

def sync(root=ROOT, message=None):
    if not message:raise ValueError('--message is required for explicit publication')
    policy=read(root/'docs/repository-artifacts.json')
    remote=git(root,'remote','get-url','origin')
    expected=policy['repository']
    if remote not in ['https://github.com/'+expected+'.git','https://github.com/'+expected,'git@github.com:'+expected+'.git']:
        raise ValueError('origin differs from registered repository')
    if git(root,'branch','--show-current')!=policy['branch']:raise ValueError('Not on registered branch')
    prepare(root);manifest=read(root/'review/MANIFEST.json')
    names=[x['path'] for x in manifest['source_files']]+GENERATED
    tracked=git_names(root,'ls-files')
    if tracked-set(names):raise ValueError('Tracked files outside publication policy; inspect manually')
    staged=git_names(root,'diff','--cached','--name-only')
    if staged-set(names):raise ValueError('Unrelated staged files; refusing to include them')
    git(root,'--literal-pathspecs','add','-f','--pathspec-from-file='+str(root/'.bridge/paths.txt'),capture=False)
    git(root,'diff','--cached','--check',capture=False)
    if git(root,'diff','--cached','--name-only'):
        git(root,'commit','-m',message,capture=False)
    git(root,'push','-u','origin',policy['branch'],capture=False)
    local=git(root,'rev-parse','HEAD');remote_sha=git(root,'ls-remote','origin','refs/heads/'+policy['branch']).split()[0]
    if local!=remote_sha:raise ValueError('Remote SHA does not match local HEAD')
    return {'commit':local,'repository':expected,'remote_verified':True}

def main():
    p=argparse.ArgumentParser();p.add_argument('command',choices=['prepare','verify','export','sync']);p.add_argument('--message');a=p.parse_args()
    result=sync(message=a.message) if a.command=='sync' else {'prepare':prepare,'verify':verify,'export':export}[a.command]()
    print(dump(result),end='')

if __name__=='__main__':main()
