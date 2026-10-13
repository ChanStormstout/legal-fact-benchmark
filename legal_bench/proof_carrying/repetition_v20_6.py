"""Exact cross-item repetition in one explanatory array; no text deletion."""
import json
from .string_guard_v19_compact import StringGuard as PreviousGuard, RepetitionAbort


class StringGuard(PreviousGuard):
    FIELDS = {'coverage_limits', 'gaps', 'limits', 'assumptions'}

    def __init__(self):
        super().__init__()
        self.cross_array = None
        self.next_array = 0
        self.seen = {}

    def feed(self, chunk):
        for char in chunk:
            opening = not self.inside and char == '['
            if opening:
                self.next_array += 1
            completing = self.inside and char == '"' and not self.escape
            value = json.loads('"'+self.raw+'"') if completing else None
            scope = self.cross_array
            field = getattr(self, 'field', None)
            was_key = self.is_key
            super().feed(char)
            if opening and self.stack:
                self.stack[-1]['scope_id'] = self.next_array
            if not completing and self.inside and char == '"':
                self.cross_array = (self.stack[-1].get('scope_id')
                    if self.stack and self.stack[-1]['kind'] == 'array' else None)
            if completing and not was_key and scope is not None and field in self.FIELDS:
                key = (scope, value)
                if len(value) >= 64 and key in self.seen:
                    self.hit = {'kind': 'EXACT_REPEATED_EXPLANATORY_ITEM', 'field': field,
                        'characters': len(value), 'same_array_scope': scope,
                        'fragment': value[:128], 'no_rewrite': True}
                    raise RepetitionAbort('Repeated explanatory item in the same array')
                self.seen[key] = True


def duplicates(value):
    result = []
    def walk(node, path=()):
        if isinstance(node, dict):
            for key, child in node.items():
                if key in StringGuard.FIELDS and isinstance(child, list):
                    seen = {}
                    for i, item in enumerate(child):
                        if isinstance(item, str):
                            if item in seen:
                                result.append({'path': list(path+(key,)),
                                    'first': seen[item], 'second': i, 'characters': len(item)})
                            seen[item] = i
                walk(child, path+(key,))
        elif isinstance(node, list):
            for i, child in enumerate(node):
                walk(child, path+(i,))
    walk(value)
    return result
