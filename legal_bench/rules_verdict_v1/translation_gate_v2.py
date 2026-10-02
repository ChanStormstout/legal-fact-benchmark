"""A model's predicate hint cannot license a semantic query translation."""
from .compile_rules_v2 import compile_card
from .source_views import digest


def compile_reviewed_fragments(card, reviewed_translations=None):
    reviewed_translations=reviewed_translations or {}
    mappings={}
    proposals=[]
    for condition in card['conditions']:
        key=card['id']+':'+condition['id']
        proposals.append({'condition_key':key,'text':condition['text'],
                          'model_predicate_hint':condition.get('factual_predicate'),
                          'model_polarity_hint':condition.get('polarity'),
                          'automatically_accepted':False})
        review=reviewed_translations.get(key)
        if review is None:
            mappings[condition['id']]={'unsupported_reason':'NO_REVIEWED_SEMANTIC_TRANSLATION; predicate and polarity hints alone do not specify a condition.'}
        else:
            if review.get('condition_hash')!=digest(condition) or not review.get('source_basis') or review.get('status')!='APPROVED_FRAGMENT':
                raise ValueError('Translation review must identify exact source condition and basis')
            mappings[condition['id']]={'query':review['query'],'translation_note':review['source_basis']}
    compiled=compile_card(card,mappings)
    compiled['translation_proposals']=proposals
    return compiled
