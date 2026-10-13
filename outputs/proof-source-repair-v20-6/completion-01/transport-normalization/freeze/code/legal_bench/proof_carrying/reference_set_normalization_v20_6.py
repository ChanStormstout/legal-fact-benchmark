"""Remove redundant members of citation sets, preserving the original separately.

Only SRC:n members in an array named refs are normalized. Evidence, prose,
component alternatives, order of first appearance and all other fields remain
unchanged. This is a transport correction, never source-semantic approval.
"""
import copy
import re


def normalize(value):
    result = copy.deepcopy(value)
    ledger = []

    def walk(node, path='$'):
        if isinstance(node, dict):
            for key, child in node.items():
                child_path = path + '/' + key
                if (key == 'refs' and isinstance(child, list)
                        and all(isinstance(v, str) and re.fullmatch(r'SRC:[1-9][0-9]*', v) for v in child)):
                    distinct = list(dict.fromkeys(child))
                    if distinct != child:
                        ledger.append({'path': child_path, 'original': child[:], 'normalized': distinct[:],
                            'reason': 'Identical citation-set member; no new source or evidence removed.'})
                        node[key] = distinct
                else:
                    walk(child, child_path)
        elif isinstance(node, list):
            for index, child in enumerate(node):
                walk(child, path + '/' + str(index))

    walk(result)
    return result, ledger
