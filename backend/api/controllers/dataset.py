"""Load immutable, versioned simulation inputs at application startup."""

import copy
import hashlib
import json
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / 'data'
_dataset: dict | None = None


def load_dataset() -> dict:
    global _dataset
    if _dataset is None:
        names = ('city_data.json', 'measures.json', 'rules.json')
        raw = {name: (DATA_DIR / name).read_bytes() for name in names}
        digest = hashlib.sha256()
        for name in names:
            digest.update(name.encode())
            digest.update(b'\0')
            digest.update(raw[name])
        city = json.loads(raw['city_data.json'])
        measures = json.loads(raw['measures.json'])
        rules = json.loads(raw['rules.json'])
        if abs(sum(d['population_share'] for d in city['districts']) - 1) >= 1e-9:
            raise ValueError('District population shares must sum to one')
        if abs(sum(i['weight'] for i in city['indicators']) - 1) >= 1e-9:
            raise ValueError('Indicator weights must sum to one')
        if len({d['code'] for d in city['districts']}) != len(city['districts']):
            raise ValueError('District codes must be unique')
        if any(
            not -90 <= district['map_anchor']['latitude'] <= 90
            or not -180 <= district['map_anchor']['longitude'] <= 180
            for district in city['districts']
        ):
            raise ValueError('District map anchors must be valid coordinates')
        if len({m['id'] for m in measures['measures']}) != len(measures['measures']):
            raise ValueError('Measure IDs must be unique')
        _dataset = {**city, **measures, **rules, 'dataset_hash': digest.hexdigest()}
    return _dataset


def public_data() -> dict:
    """Return a copy so callers cannot mutate the cached source data."""
    return copy.deepcopy(load_dataset())
