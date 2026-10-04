"""Bounded legal-source acquisition and same-task additive web preparation; no inference."""
import hashlib
import io
import json
import re
import shutil
import subprocess
import urllib.request
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path('outputs/rules-verdict-v15-rule-supplement')
BASE = Path('outputs/rules-verdict-v14-web-direct')

def digest(data):
    return hashlib.sha256(data).hexdigest()

def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('x', encoding='utf-8') as f:
        json.dump(value, f, ensure_ascii=False, indent=2)
        f.write('\n')

class JudgmentHTML(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.depth = 0
        self.data = []
    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if not self.depth and tag == 'div' and ('judgments' in attrs.get('class','').split() or attrs.get('id') == 'judgments'):
            self.depth = 1
        elif self.depth and tag not in {'br','hr','img','input','meta','link'}:
            self.depth += 1
        if self.depth and tag in {'p','div','h2','h3'}:
            self.data.append('\n')
    def handle_endtag(self, tag):
        if self.depth and tag not in {'br','hr','img','input','meta','link'}:
            self.depth -= 1
        if tag in {'p','div'}:
            self.data.append('\n')
    def handle_data(self, data):
        if self.depth:
            self.data.append(data)

SOURCES = [
    ('GENERAL_RADIO', 'https://api.sci.gov.in/jonew/judis/9056.pdf', 'pdf'),
    ('HINDUSTAN_PETROLEUM', 'https://orderlawstorage.blob.core.windows.net/judgements/supreme_court/1988/YWRtaW4vanVkZ2VtZW50X2ZpbGUvanVkZ2VtZW50X3BkZi8xOTg4L1N1cHAuICgzKS9QYXJ0IEkvU18xOTg4XzQ0LTU5XzE3MDIxMDMwMDYucGRm.pdf', 'pdf'),
    ('TELESOUND', 'https://indiankanoon.org/doc/1299689/', 'html'),
    ('DELHI_ACT', 'https://www.indiacode.nic.in/bitstream/123456789/19223/1/a1958-59.pdf', 'pdf'),
]

def acquire():
    from pypdf import PdfReader
    for name, url, kind in SOURCES:
        folder = ROOT/'authorities'/name
        if (folder/'metadata.json').exists():
            continue
        started = datetime.now(timezone.utc).isoformat()
        try:
            req = urllib.request.Request(url, headers={'User-Agent':'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=45) as response:
                raw = response.read()
                resolved = response.url
            if kind == 'pdf':
                reader = PdfReader(io.BytesIO(raw))
                pages = [{'page':i+1, 'text':p.extract_text()} for i,p in enumerate(reader.pages)]
                text = '\n'.join('PAGE '+str(p['page'])+'\n'+p['text'] for p in pages)
                save(folder/'pages.json', pages)
            else:
                parser = JudgmentHTML(); parser.feed(raw.decode('utf-8'))
                text = ''.join(parser.data)
                assert len(text)>10000, 'Judgment container unavailable; do not publish site navigation as judgment'
            folder.mkdir(parents=True,exist_ok=True)
            (folder/'source-text.txt').write_text(text,encoding='utf-8')
            save(folder/'metadata.json', {'id':name,'url':url,'resolved_url':resolved,'retrieved_at':started,
                'raw_sha256':digest(raw),'text_sha256':digest(text.encode()),'raw_bytes':len(raw),'status':'ACQUIRED',
                'extraction':'pypdf pages' if kind=='pdf' else 'HTML judgment container, no rewrite',
                'raw_binary_not_published':True})
        except Exception as e:
            save(folder/'acquisition-failure.json',{'id':name,'url':url,'time':started,'error':str(e)})
        print(name, 'saved' if (folder/'metadata.json').exists() else 'failed',flush=True)

def prepare():
    assert not (ROOT/'freeze.json').exists(), 'Frozen input must not be replaced'
    cards = []; segments = []
    def page(name, number):
        return json.loads((ROOT/'authorities'/name/'pages.json').read_text())[number-1]['text']
    def span(text, start, end):
        first=re.search(r'\s+'.join(re.escape(x) for x in start.split()),text)
        assert first, start
        last=re.search(r'\s+'.join(re.escape(x) for x in end.split()),text[first.start():])
        assert last, end
        return text[first.start():first.start()+last.end()]
    gr6=page('GENERAL_RADIO',6)
    segments.append({'id':'LAW:V15:GENERAL_RADIO:P6','authority':'GENERAL_RADIO','locator':'PDF page 6; reporter p615',
        'text':gr6[gr6.index('On the basis'):], 'selection_note':'Continuous remainder of PDF p6'})
    # Keep original extracted spelling, whitespace and other-case facts; no target application.
    segments[-1]['text']=gr6[gr6.index('On the basis'):]
    segments[-1]['selection_note']='Continuous remainder of PDF p6; last sentence continues into p7'
    gr7=page('GENERAL_RADIO',7)
    segments.append({'id':'LAW:V15:GENERAL_RADIO:P7','authority':'GENERAL_RADIO','locator':'PDF page 7 opening; reporter p615-616',
        'text':span(gr7,'required under','written permission of the landlord.'),
        'selection_note':'Completes previous page sentence and preserves special-act/lease setting'})
    gr10=page('GENERAL_RADIO',10)
    segments.append({'id':'LAW:V15:GENERAL_RADIO:P10','authority':'GENERAL_RADIO','locator':'PDF page 10; reporter p620',
        'text':span(gr10,'On  appeal by  special','an involuntary sale.'),
        'selection_note':'This court describes Parasaram precedent, not an independently acquired Parasaram judgment'})
    hp15=page('HINDUSTAN_PETROLEUM',15); hp16=page('HINDUSTAN_PETROLEUM',16)
    segments.append({'id':'LAW:V15:HINDUSTAN_PETROLEUM:P15','authority':'HINDUSTAN_PETROLEUM','locator':'PDF page 15 bottom; reporter p58',
        'text':hp15[hp15.index('The Appellate Court was clearly in error'):],
        'selection_note':'Original scan OCR retained; sentence continues on p16'})
    segments.append({'id':'LAW:V15:HINDUSTAN_PETROLEUM:P16','authority':'HINDUSTAN_PETROLEUM','locator':'PDF page 16 opening; reporter p59',
        'text':span(hp16,'so desired','Co-operative\nSocieties Act, 1960.'),
        'selection_note':'Preserves acquisition notification, s396 amalgamation and s15A protection context'})
    tele=json.loads((ROOT/'authorities/TELESOUND/selected-passages.json').read_text())
    for n,text in tele.items():
        segments.append({'id':'LAW:V15:TELESOUND:PAR'+n,'authority':'TELESOUND','locator':'Judgment paragraph '+n,
            'text':text,'selection_note':'Selected noncontiguous complete sentences' if n=='12' else 'Complete paragraph, including reserved eviction jurisdiction'})
    cards=[
      {'rule_card_id':'V15-GR','source_kind':'SOURCE_ANCHORED_RULE_EXTRACTION_NOT_INDUCTION',
       'authority':'General Radio & Appliances Co. Ltd. v. M.A. Khader, Supreme Court of India, 17 April 1986, (1986) 2 SCC 656',
       'proposition':'Under the Andhra Pradesh rent-control Act and the lease in that case, court sanction of a company-proposed amalgamation did not make the transfer involuntary or exempt it from tenancy-transfer restrictions. The tenant company had dissolved and its tenancy interests and possession passed to the transferee, without written landlord permission.',
       'scope':'Andhra Pradesh Buildings (Lease, Rent and Eviction) Control Act 1960 ss10(ii)(a),2(ix); Companies Act 1956 ss391/394; Supreme Court appeal from rent proceedings.',
       'limits':['The principal holding applies the Andhra Pradesh Act and that lease; compare the relevant statutory language before migration.','The quoted Delhi discussion is this court describing Parasaram (1980), not a newly retrieved full Parasaram opinion.','Court sanction is distinct from a special statute expressly preserving a successor tenancy. The excerpts supply no general rule that every involuntary transaction is exempt.'],
       'evidence':['LAW:V15:GENERAL_RADIO:P6','LAW:V15:GENERAL_RADIO:P7','LAW:V15:GENERAL_RADIO:P10']},
      {'rule_card_id':'V15-HP','source_kind':'SOURCE_ANCHORED_RULE_EXTRACTION_NOT_INDUCTION',
       'authority':'Hindustan Petroleum Corporation Ltd. v. Shyam Co-operative Housing Society, Supreme Court of India, 19 September 1988, (1988) 4 SCC 747',
       'proposition':'The protected/deemed tenancy under Bombay Rent Act s15A continued through the specific statutory acquisition and subsequent vesting: Esso Acquisition Act ss3/5 made the Government tenant, followed by notification and s396 amalgamation. The successor corporation retained the specified statutory protection.',
       'scope':'Bombay Rent Act s15A; Esso (Acquisition of Undertakings in India) Act 1974 ss3/5; notification and Companies Act s396 order; challenge to co-operative eviction proceedings.',
       'limits':['The case involves a subsisting licence giving deemed-tenant status and particular statutory vesting provisions.','It is not a general holding that regulatory compliance or any court-approved merger defeats eviction under another rent statute.','The factual admissions and occupancy dates described here concern that other case only.'],
       'evidence':['LAW:V15:HINDUSTAN_PETROLEUM:P15','LAW:V15:HINDUSTAN_PETROLEUM:P16']},
      {'rule_card_id':'V15-TS','source_kind':'SOURCE_ANCHORED_RULE_EXTRACTION_NOT_INDUCTION',
       'authority':'In re Telesound India Ltd., Delhi High Court, 5 December 1980, (1983) 53 Company Cases 926',
       'proposition':'In company-scheme sanction proceedings, the court described statutory vesting of tenancy rights on amalgamation and expressed a prima facie view favorable to transfer without landlord consent. It expressly reserved whether the resulting transfer attracted Delhi Rent Control Act s14(1)(b), preserving landlord recourse before the appropriate rent authority or civil court.',
       'scope':'Companies Act ss391/394 scheme sanction, with Delhi rent-control issues raised by an objecting landlord.',
       'limits':['Paragraph 16 is expressly prima facie and reserves the eviction issue; do not promote it into a final rent-court exemption.','Transferred rights cannot be wider than the transferor rights described in paragraph 12.','Date of judgment is 1980; 1983 is the reporter citation. This High Court opinion must be assessed with the later Supreme Court opinions and their distinct statutory settings.'],
       'evidence':['LAW:V15:TELESOUND:PAR12','LAW:V15:TELESOUND:PAR16']}
    ]
    package={'role':'ADDITIONAL_LEGAL_MATERIAL_ONLY_NO_TARGET_APPLICATION','rule_cards':cards,'law_segments':segments,
        'source_review':'Codex source-checked extraction, not human gold; summaries remain interpretations alongside excerpts',
        'coverage_limits':['No independently verified historical FERA s29 text or actual target RBI directive is added.','No general compulsion exception, target court reasoning, target consent fact or target outcome is supplied.','Three earlier judgments are purposively selected for known development gaps, not an evaluated automatic retrieval algorithm.','Direct Delhi Act PDF retrieval timed out; no statutory text is guessed from that failure. Original supplied statutory formula remains unchanged.']}
    save(ROOT/'rule-package.json',package)
    (ROOT/'rule-package.md').write_text('# V15 supplementary authorities\n\n'+json.dumps(package,ensure_ascii=False,indent=2))
    d=ROOT/'tasks/1134266';d.mkdir(parents=True,exist_ok=True)
    for name in ['prompt.txt','schema.json','source.json','law-package.json','retrieval.json']:
        shutil.copyfile(BASE/'tasks/1134266'/name,d/('base-'+name))
    base=(d/'base-prompt.txt').read_text()
    addition='SUPPLEMENTARY LEGAL MATERIAL (other-case authorities, no target findings)\n'+json.dumps(package,ensure_ascii=False)+'\n'
    marker='TARGET INTERMEDIATE MATERIAL (UNVERIFIED)'
    assert base.count(marker)==1
    prompt=base.replace(marker,addition+marker)
    assert prompt.replace(addition,'',1)==base
    schema=json.loads((d/'base-schema.json').read_text())
    schema['properties']['grounds']['items']['properties']['law_refs']['items']['enum'] += [s['id'] for s in segments]
    (d/'prompt.txt').write_text(prompt)
    save(d/'schema.json',schema)
    execution=(BASE/'tasks/1134266/submission-text.txt').read_text()
    task=prompt+'\n\nOUTPUT SCHEMA (same answer fields; additional law source IDs only; no local token mask)\n'+json.dumps(schema,ensure_ascii=False,indent=2)
    task+='\n\nWEB EXECUTION REQUIREMENTS\n'+execution
    (d/'case_1134266_task.txt').write_text(task)
    (d/'submitted-message.txt').write_text('请完整读取所附自包含任务，按其中固定问题和JSON格式一次性回答。只依据提供的案情和法律材料，不进行外部搜索，不查找其他判决版本，不依赖其他对话。网页端没有本地逐token Schema约束。')
    save(ROOT/'selection-record.json',{'max_documents':5,'selected_documents':3,'direct_downloads':2,'web_passage_source':1,
        'candidates_considered':['GENERAL_RADIO','HINDUSTAN_PETROLEUM','TELESOUND','DELHI_ACT'],
        'not_adopted':{'DELHI_ACT':'Timeout; original statute framing retained, no new unverified text'},
        'selection_basis':'Known legal coverage gap from V14, covers tenant-favorable and contrary propositions with procedural limits; no selection based on V15 answer',
        'target_and_later_target_reproductions_excluded':True,'external_search_for_tested_model':False})
    save(ROOT/'evaluation-rules.json',{'model_input':False,'one_concentrated_source_review':True,
        'reference_status':'MODEL_ASSISTED_SOURCE_REVIEW_NOT_HUMAN_GOLD',
        'checks':['same known facts and court/party status preserved','statutory vesting vs rent restriction','voluntary/compulsion positions and counterarguments addressed','Telesound prima facie and forum reservation retained','HP special statutory protection not generalized','AP/Delhi law migration explicit','consent allegation not established through added law','supported legal analysis without requiring withheld target reasoning','no other-case facts imported','outcome and assessments consistent'],
        'success_not_defined_by_determinate_outcome':True,'single_run_net_material_addition_not_causal_or_statistical_proof':True,
        'decisions':['CONTINUE_SOURCE_GROUNDED_RULE_EXTRACTION_AND_APPLICATION','RULE_INTEGRATION_STILL_UNRELIABLE','FACT_GAP_LIMITS_DETERMINATE_OUTCOME','INSUFFICIENT_EVIDENCE']})
    save(ROOT/'protocol.json',{'version':'V15','case':'1134266','baseline':'V14 WEB_HIGH_D, reused without regeneration',
        'max_new_web_answers':1,'retries':0,'local_model_calls':0,'paid_api_calls':0,'requested_mode':'ordinary High, not Pro',
        'no_baseline_answer_or_review_in_task':True,'no_reextraction_or_algorithm_changes':True,
        'allowed_change':'Additional frozen authority excerpts and rule interpretations; source-ID enum extension only',
        'same_case_original_law_examples_question_and_final_requirements':True,
        'comparison':'single exposed-case net change after source addition; web model identity opaque; no independent test',
        'stop':'One new answer (or failure) and one concentrated review; no follow-up generation, next round, commit or push',
        'source_transport_failures_recorded_not_model_retries':True})
    save(ROOT/'freeze.json',{'time':datetime.now(timezone.utc).isoformat(),'head':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),
        'files':{str(p):digest(p.read_bytes()) for p in ROOT.rglob('*') if p.is_file()},
        'actual_preparation_script_sha256':digest(Path(__file__).read_bytes()),'before_first_generation':True})
    print(json.dumps({'frozen':str(ROOT),'authorities':3,'new_law_segments':len(segments),'task_chars':len(task),'max_answers':1}))

if __name__ == '__main__':
    import sys
    if '--prepare' in sys.argv:
        prepare()
    else:
        acquire()
