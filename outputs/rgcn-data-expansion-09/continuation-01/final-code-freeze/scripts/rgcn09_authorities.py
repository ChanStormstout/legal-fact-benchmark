"""Build V09 candidate authorities from original, addressed source passages.

Passage boundaries are explicit and reviewable. Distinct units are distinct uses,
not assertions that there are equally many independent judgments. No labels or
target outcomes are generated here; this is not automatic rule induction.
"""
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from legal_bench.rules_verdict_v1.source_identity_v2 import parse_responses, merge_windows
from scripts.rgcn09_data import ROOT, read, save, sha

# Each specification: source, name, addressed ranges, date, legal scope, mechanism,
# status and a substantive limitation retained with the exact original passage.
SPECS = [
 ('18143401','DRC14_4',[(44,44)],'1958','Delhi DRC14(4)', 'partnership_company;temporal_applicability','STATUTE','Extract only subsection (4); 16 August 1958 threshold, business/profession, ostensible partnership and real subletting are all required. Current online consolidation is not a certified historical version.'),
 ('114533','KR_PERMISSIVE_FAMILY',[(154,156)],'1973-11-29','Delhi DRC14(1)(b)','family_occupation;licence_sublease','COURT_ADOPTED','Living as husband and wife is contextual evidence, not blanket immunity for relatives; do not invent continued control or disregard contrary evidence.'),
 ('114533','KR_PARTNERSHIP_SCOPE',[(161,164)],'1973-11-29','Delhi DRC14(4)','family_occupation;partnership_company;temporal_applicability','COURT_ADOPTED','Statutory deeming of sham business partnership is not a presumption applicable to every family occupation.'),
 ('114533','KR_BURDEN',[(165,166)],'1973-11-29','Delhi DRC14(1)(b)','control_exclusive_possession','COURT_ADOPTED','Initial burden and rebuttal depend on the proof stated; mere presence alone is not equivalent to exclusive possession for consideration.'),
 ('1312881','CEL_CONTROL',[(186,190)],'2009-10-30','Goa rent statute; Supreme Court synthesis including Delhi precedents','partnership_company;control_exclusive_possession','COURT_ADOPTED_SYNTHESIS','Analogical principles; original target statute Goa22(2)(b)(i), not Delhi. Retention of control and genuine partnership are factual requirements.'),
 ('1312881','CEL_SHAM_PROOF',[(195,199)],'2009-10-30','Goa rent statute; pleading/evidence scope','partnership_company','COURT_ADOPTED','No universal waiver of pleading requirements. Surprise/prejudice and actual pleaded subletting matter; use only compatible reasoning.'),
 ('1312881','CEL_BURDEN',[(183,194)],'2009-10-30','Goa rent statute; general subletting synthesis','control_exclusive_possession;licence_sublease','COURT_ADOPTED_SYNTHESIS','Presumption is rebuttable. Different formulations in subparagraphs (i),(v),(vi) must be read together; do not apply consideration to every Delhi assignment/parting-with-possession alternative.'),
 ('1378557','HELP_GENUINENESS',[(369,371),(374,375)],'1987-05-06','Bombay rent statute; Partnership Act4 and6','partnership_company;control_exclusive_possession','COURT_ADOPTED','Agency, real agreement and conduct matter; a deed or label alone is insufficient. Bombay revisional standard is not Delhi substantive law.'),
 ('923000','AH_LICENCE',[(213,227)],'1967-12-07','Delhi and Ajmer Rent Control Act1952; analogous licence/lease inquiry','licence_sublease;control_exclusive_possession','COURT_ADOPTED','Exclusive possession is important but not conclusive; written agreement and retained control must be assessed. Do not replace 1958 Act with1952 Act.'),
 ('923000','AH_BURDEN',[(213,215)],'1967-12-07','Delhi and Ajmer Rent Control Act1952; evidential principle later cited','control_exclusive_possession','COURT_ADOPTED','Prima facie exclusive possession plus valuable consideration; withheld best evidence matters. Not a rule making every evidential omission conclusive.'),
 ('923000','AH_CONSENT_SCOPE',[(235,241)],'1967-12-07','Delhi and Ajmer Rent Control Act1952; contract and specific subtenancies','written_consent;temporal_applicability','COURT_ADOPTED','Consent must concern relevant subtenancy/time; a lease purpose or letter about earlier occupation is not blanket written permission for later sublettings.'),
 ('1707845','CK_REGULATORY_TRANSFER',[(88,94)],'1996-12-12','Delhi DRC14(1)(b)','amalgamation;partnership_company;written_consent','COURT_ADOPTED','FERA-driven business assignment is distinguished from direct statutory vesting. Same business does not establish same tenant; exact assignment and written consent matter.'),
 ('1707845','CK_ASSIGNMENT_SCOPE',[(95,102)],'1996-12-12','Delhi DRC14(1)(b), quoting Parasram Harnand Rao','statutory_succession;amalgamation','ADOPTED_REPORTED_AUTHORITY','Court-confirmed liquidator sale is not direct nationalisation/vesting. Do not generalise this quoted authority to every involuntary statutory succession; exclude106222 as a target.'),
 ('614998','GL_WRITTEN_CONSENT',[(289,299)],'1986-02-26','Delhi DRC17 and18, independent subtenant protection','written_consent;licence_sublease','COURT_ADOPTED','Specific documentary consent and notice; not blanket acceptance of any landlord signature. Read with separately retained concurring caution.'),
 ('614998','GL_CONCURRING_LIMIT',[(306,314)],'1986-02-26','Delhi DRC17 and18','written_consent','CONCURRING_LIMITATION','KhalidJ concurs in result but stresses exceptional facts and normal strict twin conditions; preserve this status, not an independently universal majority exception.'),
 ('1887042','GD_COMMERCIAL_SUCCESSION',[(648,656)],'1985-05-01','Delhi commercial tenancy; ordinary inheritance','family_occupation;statutory_succession','COURT_ADOPTED','Death/inheritance of commercial tenancy; residential statutory limitations and corporate amalgamation are different. Later changes not audited; retrospective research only.'),
]


def main():
    raw_files = sorted((ROOT/'sources/raw').glob('authority-open-*.txt'))
    responses = []
    for p in raw_files:
        responses.extend(parse_responses(p.read_text(),p))
    docs = merge_windows(responses)
    old = read('outputs/rgcn-ranking-development-06/sources/laws.json')
    units = list(old)
    for cid, name, ranges, date, scope, mechanisms, status, limit in SPECS:
        doc = docs[cid]
        if doc['conflicts']:
            raise ValueError('Conflicting source windows '+cid)
        rows = {s['original_line']:s for s in doc['segments']}
        segs = []
        for first,last in ranges:
            for n in range(first,last+1):
                if n not in rows:raise ValueError('Missing required passage '+cid+':'+str(n))
                segs.append(rows[n])
        if name=='DRC14_4':
            s=segs[0];start=s['text'].index('For the purposes of clause (b)');end=s['text'].index('cite23†(5)')
            text=s['text'][start:end]
            address=[{'id':s['id'],'start':start,'end':end}]
        else:
            text='\n'.join(s['text'] for s in segs)
            address=[{'id':s['id'],'start':0,'end':len(s['text'])} for s in segs]
        units.append({'id':'LAW:V09:'+name,'text':text,
            'source':{'document_id':cid,'url':doc['url'],'date':date,
                      'court_or_publisher':'NCT Delhi statute' if cid=='18143401' else 'Supreme Court of India',
                      'passage_addresses':address,'raw_provenance':[s['provenance'] for s in segs]},
            'version_status':'AS_REPORTED_NO_HISTORICAL_CONSOLIDATION_CERTIFICATE',
            'scope':scope,'mechanisms':mechanisms.split(';'),'legal_status':status,
            'coverage_limit':limit,'dependencies': ['LAW:S02:DRC14:1b'] if name=='DRC14_4' else ['LAW:V09:GL_WRITTEN_CONSENT'] if name=='GL_CONCURRING_LIMIT' else [],
            'source_status':'ADDRESSED_PASSAGE_RECOVERED_SOURCE_REVIEW_NOT_HUMAN_GOLD',
            'full_source_status':doc['status'],
            'allowed_role':'AUTHORITY_SOURCE_NOT_TARGET_CASE',
            'annotation_status':'RESEARCHER_SELECTED_SOURCE_REVIEWED_PASSAGE; CASE_USE_NOT_YET_LABELLED'})
    reserved={cid for cid,*_ in SPECS if cid!='18143401'}|{'106222'}
    save(ROOT/'authority-pool/laws.json',units)
    for cid in sorted({x[0] for x in SPECS}):
        save(ROOT/('authority-pool/documents/'+cid+'.json'),docs[cid])
    save(ROOT/'authority-pool/manifest.json',{'units':len(units),'old_units':14,'new_units':len(SPECS),
        'count_basis':'Functionally distinct original-passage units, NOT independent judgments; related units retained with dependencies/limits',
        'distinct_source_document_keys':sorted({u['source']['document_id'] for u in units}),
        'reserved_authority_case_ids':sorted(reserved),
        'provenance_check':'Required addressed source passages present; identity envelope maintained; not semantic correctness proof',
        'mechanism_coverage': sorted({m for _,_,_,_,_,mm,_,_ in SPECS for m in mm.split(';')}),
        'pool_sha256':sha(ROOT/'authority-pool/laws.json'),
        'target_answer_leakage_policy':'Reserve authority source cases and adopted reported target106222. Never select any as train/test targets. Old ten and dev six not authority source cases.'})
    print('Prepared',len(units),'authority units;',len(SPECS),'new original-passage units')


if __name__=='__main__':main()
