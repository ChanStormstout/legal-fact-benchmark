"""Record bounded constraint diagnosis and repair release; never generate or push."""
import csv
import hashlib
import json
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_views import write_new

ROOT = Path('outputs/json-constraint-diagnosis-v1')
OLD = Path('outputs/rules-verdict-v9-final-examples/runs/B')
read = lambda path: json.loads(path.read_text())
sha = lambda path: hashlib.sha256(path.read_bytes()).hexdigest()
start = read(ROOT / 'start-audit.json')
changed = [name for name, value in start['old_outputs'].items()
           if not Path(name).is_file() or sha(Path(name)) != value]
assert not changed, changed
frozen = read(ROOT / 'freeze/config.json')
for name, value in frozen['files'].items():
    assert sha(Path(name)) == value, name
live_changes = {name: {'frozen_hash': value, 'current_hash': sha(Path(name))}
                for name, value in frozen['live_code'].items() if sha(Path(name)) != value}
assert set(live_changes) == {'legal_bench/mlx_json_constraint.py',
                             'legal_bench/mlx_json_constraint_v2.py',
                             'tests/test_mlx_constraint_v2.py'}
write_new(ROOT / 'preservation-check.json', {
    'previous_output_files_checked': len(start['old_outputs']),
    'changed_previous_outputs': changed, 'frozen_run_files_unchanged': True,
    'intentional_post_run_public_integration': live_changes,
    'historical_reproduction': 'Use historical frozen source bytes. Live defaults now use the correction; do not reinterpret prior runs.'})
release_files = ['legal_bench/mlx_json_constraint.py', 'legal_bench/mlx_json_constraint_v2.py',
                 'tests/test_mlx_constraint_v2.py', 'scripts/replay_constraint_result_v1.py',
                 'scripts/report_constraint_diagnosis_v1.py']
for name in release_files:
    dest = ROOT / 'release/code' / name
    dest.parent.mkdir(parents=True, exist_ok=True)
    assert not dest.exists()
    dest.write_bytes(Path(name).read_bytes())
write_new(ROOT / 'release/manifest.json', {
    'files': {name: sha(Path(name)) for name in release_files},
    'role': 'Public adapter integration after frozen validation, no additional inference',
    'new_generation_calls_after_integration': 0,
    'tests': 'public-fix-tests.txt: 5 relevant tests passed in project MLX environment'})
results = read(ROOT / 'results.json')
legacy = read(OLD / 'run.json')
replay = read(ROOT / 'post-run-token-replay.json')
legacy_ids = read(OLD / 'token-ids.json')
fixed_ids = read(ROOT / 'runs/FIXED/token-ids.json')
index = next(i for i, (a, b) in enumerate(zip(legacy_ids, fixed_ids)) if a != b)
assert index == replay['first_legacy_disallowed_transition']['position']
write_new(ROOT / 'same-input-comparison.json', {
    'prior_legacy_call_reused': True, 'new_calls': 2,
    'first_legacy_vs_fixed_token_difference': index,
    'legacy_token_id': legacy_ids[index], 'fixed_token_id': fixed_ids[index],
    'matching_token_prefix': legacy_ids[:index] == fixed_ids[:index],
    'same_prompt_schema_rendered_input': all(
        (ROOT / 'runs' / mode / name).read_bytes() == (OLD / name).read_bytes()
        for mode in ['NONE', 'FIXED'] for name in ['prompt.txt', 'schema.json', 'rendered.txt']),
    'different_library_or_sampling_settings': False,
    'not_a_new_A_vs_B_legal_comparison': True})
rows = []
for mode, row in [('LEGACY_V9_B_REUSED', legacy)] + [(r['mode'], r) for r in results['rows']]:
    rows.append({'mode': mode, 'case': '69305', 'run_status': row['run_status'],
                 'input_tokens': row['prompt_tokens'], 'output_tokens': row['output_tokens'],
                 'seconds': round(row['elapsed_seconds'], 2),
                 'peak_mlx_memory_gb': row.get('peak_mlx_memory_gb'),
                 'finish_reason': row['finish_reason'],
                 'answer_status': None, 'legal_correctness': 'NOT_SCORED',
                 'raw': str((OLD if mode.startswith('LEGACY') else ROOT / 'runs' / mode) / 'raw-response.txt')})
write_new(ROOT / 'comparison-table.json', {'role': 'SAME_B_INPUT_TECHNICAL_DIAGNOSIS', 'rows': rows})
with (ROOT / 'comparison-table.csv').open('x') as handle:
    writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
    writer.writeheader()
    writer.writerows(rows)
write_new(ROOT / 'final-source-review.json', {
    'role': 'TECHNICAL_SOURCE_REVIEW_NOT_NEW_LEGAL_GOLD',
    'basis': ['Installed MLX-VLM 0.7.4 processor/streaming source',
              'Installed LM Format Enforcer 0.11.2 free-text shortcut source',
              'Real tokenizer fixture', 'Frozen input and emitted token replay'],
    'confirmed': ['Fast shortcut omits a legal composite string-ending token.',
                  'Closing standalone quote was allowed; not all quote endings blocked.',
                  'First actual divergence at token42 is legacy-blocked token10152.',
                  'Fixed processor prefix counts match emitted token IDs.',
                  'Decoded actual IDs equal raw, no duplicate append found.',
                  'No-mask and fixed outputs identical and schema-valid.'],
    'limitations': ['Only V9 B on case69305 was rerun; A and earlier failures were not rerun.',
                    'Formatting completion is not legal correctness or proof of structured analysis benefit.',
                    'Generated ground3 says SUPPORTED but its own explanation says unverified. This remains an answer-content issue, untouched by format repair.',
                    'Program tests cover specific delimiter/type/enum/reference-state behaviors, not all possible schema semantics.'],
    'web_calls': 0, 'new_reference_annotations': 0})
(ROOT / 'final-answer-slots.md').write_text(
    '# 同输入约束诊断输出\n\n本轮不是A/B法律质量比较。两份文件均为V9 B同一输入的最终生成。\n\n'
    '[无自定义约束完整输出](runs/NONE/parsed.json)；[修复约束完整输出](runs/FIXED/parsed.json)。'
    '两份输出原字节相同，均正常结束，法律正确性未评分。旧失败保留在V9。\n', encoding='utf-8')
report = '''JSON约束层诊断与最小修复（69305，开发诊断）

结论：找到并修复了约束层对合法字符串结束token的误屏蔽。本案V9 B的有界对照支持它是此次重复的直接触发因素；没有证据表明MLX-VLM发生崩溃或流式文本被重复追加。保留模型、框架、提示、Schema及生成设置，未继续改法律提示词。

错误发生在哪里
SchemaMask通过LM Format Enforcer 0.11.2取得允许token。该库的JSON自由文本快速路径缓存普通文本与以引号结束的token，随后只动态检查以引号开头的token；遗漏了以普通文字或标点开头、内部含结束引号并继续带JSON标点的合法token。Qwen的token10152是 .", 。逐字符Schema解析允许它，但原快速路径不允许。
独立合法JSON测试复现了该问题。单独引号token1仍允许，所以不能说模型根本无法关闭字符串；被排除的是更自然的一次性结束方式。

实际轨迹与比较
原V9 B与本轮两次成功输出的前42个token相同。第42个（零起算）位置，本轮使用10152关闭第一个point；旧约束不允许10152，原输出改为1973，随后不断延长该字符串并触发重复止损。修复版全部实际token都被修复解析器允许，642次处理器回调的前缀长度及上一token与实际生成一致。流式raw也与token解码一致。

方法                         状态                 输入token   输出token   秒
原V9 B（只复用历史结果）      REPETITION_ABORT       16983        99        33.90
同输入、无自定义约束          OK                     16983       641        58.84
同输入、修复版约束            OK                     16983       641        65.54

两份成功输出逐字相同，均finish_reason=stop，未触发重复保护，严格JSON解析与原Schema检查通过，没有格式修补。每次max_tokens仍3072，总上下文32768，完整输入未截断，thinking关闭。新调用2次、网页0次、重试0次；推理合计124.37秒。MLX峰值分别7.316/7.319GB，这不是整机总内存峰值。实际token IDs、参数、raw和回调轨迹均保留。
模型revision为8b2b98c00a6b4d291155e4890773ca8f769aee53，MLX-VLM0.7.4，LM Format Enforcer0.11.2。greedy、seed20261001、repetition_penalty1等保持不变。新对照没有跑A，因此不是恢复后的A/B方法收益比较。

修复方法及验证边界
新增版本化CompositeQuoteEnforcer：保留原Schema字符解析与快速缓存，仅对快速路径遗漏的复合引号token补做完整逐字符校验。实际tokenizer有471个此类候选，并非全部都准许；每个仍须通过当前解析状态。没有强制关闭字段、放宽Schema、删除重复文字或补齐答案。
先冻结修复版进行上述调用，随后默认mlx_json_constraint.py接入同一修复enforcer。运行时源码和后续公共接入源码分开保存在freeze/code与release/code。5项相关程序测试通过，覆盖复合结束、必要字段/额外字段、类型/枚举、转义引号、EOS及公共入口前缀处理。未追加模型调用。旧实验只能用对应冻结版本解释或复现，不能静默按新默认重跑。

不能推出什么
这足以解释本案B的局部技术失败，但没有重测V9 A或其他历史失败，不能概括全部截断/重复。生成完整不代表法律正确：新答案第三项assessment为SUPPORTED，explanation却说关键关系尚未核实，内容仍不一致。本轮不修这些语义错误，不报告法律准确率，也不据此证明结构化优于文本笔记。没有新增参考答案、案件、法源或网页任务。

交付与停止
comparison-table、post-run-token-replay、same-input-comparison、offline-audit、offline-fix-audit和runs包含完整证据。preservation-check逐一验证V1–V9原文件未改，公共修复另外存档。首次生成前的冻结prompt/schema/参数与来源哈希保留不变；prepare/verify仅更新本地审阅包，不提交或推送。已完成两次限定调用，停止本轮，不自动开启新实验。
'''
(ROOT / 'report-zh.txt').write_text(report, encoding='utf-8')
print(json.dumps({'preserved_previous_files': len(start['old_outputs']),
                  'new_calls': results['new_calls'], 'report': str(ROOT / 'report-zh.txt')}, indent=2))
