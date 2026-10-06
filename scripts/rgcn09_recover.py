"""Read-only recovery import using the unchanged V09 validators and graph builder."""
import json
import shutil
from pathlib import Path
from scripts import rgcn09_import as importer

BASE = Path('outputs/rgcn-data-expansion-09')
OUT = BASE / 'recovery-03'
MAPPING = {
 '6ac3593f-4844-83e8-ae3c-1a30224f4f30': 'GRAPH-183917167',
 '6ac357ed-7e8c-83e8-a6d6-832c07ef207a': 'GRAPH-52547606',
 '6ac35830-6f10-83e8-9569-560390cf1781': 'GRAPH-191402169',
 '6ac35717-63f0-83e8-92cd-524e03e0c8be': 'GRAPH-68096693',
 '6ac3593c-bd70-83e8-8be6-7ab407408126': 'LABEL-183917167',
 '6ac3582c-55c0-83e8-a621-6fab6afedb48': 'LABEL-191402169',
 '6ac35833-0aa4-83e8-b210-60cdb0804cce': 'LABEL-52547606',
}

def run():
    evidence=[]
    for conversation, tid in MAPPING.items():
        for suffix in ('.response.txt', '.codeblocks.json'):
            original=OUT/'web'/('UNMAPPED-'+conversation+suffix)
            target=OUT/'web'/(tid+suffix)
            if target.exists():
                assert target.read_bytes()==original.read_bytes()
            else: shutil.copyfile(original,target)
        evidence.append({'task_id':tid,'url':'https://chatgpt.com/c/'+conversation,
                         'identity_basis':'visible uploaded-task timestamp and response case ID/file name',
                         'new_generation':False})
    importer.save(OUT/'conversation-mapping.json',evidence)
    original_payload=importer.payload
    def recovered(tid):
        blocks=OUT/'web'/(tid+'.codeblocks.json')
        if blocks.exists():
            valid=[]
            for text in importer.read(blocks):
                try: p=json.loads(text)
                except (ValueError,TypeError): continue
                if isinstance(p,dict) and str(p.get('case_id'))==tid.split('-',1)[1]:
                    valid.append(p)
            if len(valid)==1:return valid[0],str(blocks),'COMPLETE_JSON_CODE_BLOCK_UNCHANGED'
            if valid:raise ValueError('AMBIGUOUS_RECOVERED_PAYLOAD')
        if tid=='ALIGN-1859043':
            p=BASE/'recovery-02/web/ALIGN-1859043.json'
            return importer.read(p),str(p),'PRIOR_RECOVERY_UNCHANGED_JSON'
        return original_payload(tid)
    importer.payload=recovered
    importer.import_all('../../recovery-03/imports')

if __name__=='__main__':run()
