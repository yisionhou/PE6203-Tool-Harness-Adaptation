"""Public, credential-free inference settings shared by every strategy."""
import hashlib
import json
import math
from pathlib import Path

DEFAULTS = {
    'model': 'deepseek-v4-flash-ga-260731',
    'base_url': 'https://ark.cn-beijing.volces.com/api/v3',
    'temperature': 0.2, 'max_completion_tokens': 4096, 'max_round': 10,
    'request_timeout': 60, 'stop_policy': 'final_text_after_tool_result',
}


def canonical_hash(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True,
        separators=(',', ':')).encode('utf-8')).hexdigest()


def validate_config(config):
    if not isinstance(config, dict) or set(config) != set(DEFAULTS):
        raise ValueError(f'run_config must contain exactly {list(DEFAULTS)}; credentials are not accepted')
    for key in ('model', 'base_url'):
        if not isinstance(config[key], str) or not config[key].strip():
            raise ValueError(f'{key} must be a nonempty string')
    for key in ('max_completion_tokens', 'max_round', 'request_timeout'):
        if type(config[key]) is not int or config[key] < 1:
            raise ValueError(f'{key} must be a positive integer')
    value = config['temperature']
    if type(value) not in (int, float) or not math.isfinite(value) or not 0 <= value <= 2:
        raise ValueError('temperature must be between 0 and 2')
    if config['stop_policy'] != DEFAULTS['stop_policy']:
        raise ValueError('Unsupported stop_policy')
    return dict(config)


def load_config(path):
    return validate_config(json.loads(Path(path).read_text(encoding='utf-8-sig')))
