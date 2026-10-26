"""Local request measurements only. Never load model weights or call an endpoint."""
import json
import environment as env
from prepare import wire

TOKENIZER = env.REPO / '.runtime/qwen35-v1/model-cache/models--mlx-community--Qwen3.5-9B-4bit/snapshots/8b2b98c00a6b4d291155e4890773ca8f769aee53/tokenizer.json'
_tokenizer = None


def measure(w):
    global _tokenizer
    from tokenizers import Tokenizer
    if _tokenizer is None:
        _tokenizer = Tokenizer.from_file(str(TOKENIZER))
    content_tokens = sum(len(_tokenizer.encode(m['content'], add_special_tokens=False).ids)
                         for m in w['messages'])
    # This is not a certified copy of Together's tokenizer or chat template.
    return {'message_content_tokens_local': content_tokens,
            'message_utf8_bytes': sum(len(m['content'].encode()) for m in w['messages']),
            'request_bytes': len(json.dumps(w).encode()),
            'decoder_bytes': len(json.dumps(w.get('response_format', {})).encode()),
            'requested_output_capacity': w['max_tokens'],
            'local_tokenizer_path': str(TOKENIZER),
            'hosted_template_and_tokenizer_match_verified': False,
            'hosted_context_behavior': w.get('context_length_exceeded_behavior'),
            'input_truncated': False}


def request_measurement(req, cfg):
    return measure(wire(req, cfg))
