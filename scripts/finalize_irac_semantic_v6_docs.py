# -*- coding: utf-8 -*-
"""Local publication metadata only; never stage, commit or push."""
import json
from pathlib import Path
from irac_semantic_v6 import R, read, save


def main():
    report=str(R/'report-zh.txt')
    summary='All six local calls across two cases completed in 12.44 minutes: two P proposals and four final answers, without retries, browser calls, or C. Twenty-three tests and 17 real-tokenizer examples passed; E passed, M/L did not. B added alternative-branch/source errors for 112400 and corrected some 188721101 errors without reliable overall net benefit. Further prompts/fields and mandatory P for the current 9B model were paused. All 2,595 historical files and old IRAC code were retained; no SEALED access, commit, or push occurred.'
    policy=read('docs/repository-artifacts.json')
    links=[('Report','report-zh.txt'),('Case comparison','case-comparison.csv'),('Complete answers and P','answers.md'),
           ('Single source review','final-source-review.json'),('E/M/L','acceptance.json'),('Per-call costs','call-costs.csv'),
           ('Frozen configuration','freeze/config.json'),('Engineering acceptance','engineering/acceptance.json'),
           ('Actual-input checks','delivery-validation.json'),('Historical preservation checks','preservation-after.json')]
    current={'contract_version':2,'review_kind':'IRAC_SEMANTIC_INTERFACE_V6_COMPLETED',
        'title':'IRAC V6 two-case complete-flow comparison after semantic-interface repair','report':report,'summary':summary,
        'status':'COMPLETED_E_PASS_M_L_NOT_PASSED_STOPPED_LOCAL_ONLY',
        'links':[{'label':label,'path':str(R/path)} for label,path in links]+[{'label':'Implementation notes','path':'docs/IRAC_SEMANTIC_INTERFACE_V6.md'}],
        'review_request':'Read-only review of actual V6 code, frozen inputs, and four complete answers. Check separation of evidence relevance from condition truth, independent records and uses across arrangements, local source-role/limitation checks, and rejection of empty/omitted/duplicate final requests. Distinguish E engineering, M arrangements/uses, and L complete legal analysis. B reads raw P, not check blocks, so improvements cannot be attributed to program hints. Inspect residential use, residence quantifiers, and personal alternative routes in 112400; lease date, counterarguments, wage documents, and consequences of unknown consent in 188721101. Evaluation files absent from inputs are not tested sources. Uniform DENY predictions are not gold. Review does not authorize new runs, changed answers, or publication.'}
    policy['current_review']=current
    for p in ['scripts/report_irac_semantic_v6.py','scripts/review_irac_semantic_v6.py','scripts/finalize_irac_semantic_v6_docs.py']:
        if p not in policy['code_review_files']:policy['code_review_files'].append(p)
    save('docs/repository-artifacts.json',policy)
    cat=read('docs/EXPERIMENTS.json')
    assert not any(x['id']=='irac-semantic-interface-v6' for x in cat['experiments'])
    cat['experiments'].append({'id':'irac-semantic-interface-v6','role':'two_exposed_cases_semantic_interface_development',
                             'report':report,'note':summary})
    save('docs/EXPERIMENTS.json',cat)
    readme=Path('README.md');text=readme.read_text()
    assert text.startswith('# Current work: IRAC V5')
    text=text.replace('# Current work: IRAC V5 two-case complete-flow acceptance completed','# Historical: IRAC V5 two-case complete-flow acceptance',1)
    intro='# Current work: IRAC V6 two-case complete comparison completed\n\n'+summary+' See [Report]('+report+') / [Case comparison]('+str(R/'case-comparison.csv')+') / [Complete answers]('+str(R/'answers.md')+') and [Implementation notes](docs/IRAC_SEMANTIC_INTERFACE_V6.md). These two cases remain development materials; results do not establish legal accuracy or graph-method effectiveness. A same-interface stronger-model comparison is proposed only, not executed.\n\n'
    readme.write_text(intro+text)
    log=Path('docs/CHANGELOG.md')
    log.write_text('## 2026-10-08 IRAC V6: evidence relevance separated from condition assessment; two-case A/P/B completed\n\n'+summary+' Repairs cover independent evidence/local uses, program-determined source roles, readable valid-condition catalogs, and exactly-once final requests. The method was unchanged after freezing. Checks were offline, with raw P passed directly to B. B including P cost 252.80/298.54 seconds versus A 75.61/119.17; complete-answer benefit remained insufficient. Raw outputs, failures, and snapshots were retained. Work stopped after one consolidated source review.\n\n'+log.read_text())
    print('Local docs updated; prepare/verify still required')


if __name__=='__main__':main()
