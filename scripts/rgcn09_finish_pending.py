"""Import the two authorized V09 gap tasks, preserving the earlier duplicate hold."""
import json
from pathlib import Path
from scripts import rgcn09_import as imp
from scripts import rgcn09_resume as prior

OUT = Path('outputs/rgcn-data-expansion-09/continuation-03')


def payload(task_id):
    if task_id in ('GRAPH-33810117', 'LABEL-1106992'):
        direct = OUT / 'web' / (task_id + '.download.json')
        if direct.exists():
            obj = imp.read(direct)
            if str(obj.get('case_id')) != task_id.split('-', 1)[1]:
                raise ValueError('CASE_ID_MISMATCH')
            return obj, str(direct), 'DOWNLOADED_JSON_UNCHANGED'
        blocks = OUT / 'web' / (task_id + '.codeblocks.json')
        if blocks.exists():
            found = []
            for block in imp.read(blocks):
                try:
                    obj = json.loads(block)
                except (TypeError, ValueError):
                    continue
                if isinstance(obj, dict) and str(obj.get('case_id')) == task_id.split('-', 1)[1]:
                    found.append(obj)
            if len(found) == 1:
                return found[0], str(blocks), 'COMPLETE_JSON_CODE_BLOCK_UNCHANGED'
            if len(found) > 1:
                raise ValueError('AMBIGUOUS_COMPLETE_PAYLOADS')
    return prior.recovered(task_id)


if __name__ == '__main__':
    if (OUT / 'imports/final-01').exists():
        raise ValueError('IMMUTABLE_IMPORT_ALREADY_EXISTS')
    imp.payload = payload
    imp.import_all('../../continuation-03/imports/final-01')
