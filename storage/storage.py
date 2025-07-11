#storage.py
import json
import os
import time
from config import DATA_FILE

def _load():
    if not os.path.exists(DATA_FILE):
        return {'bindings': {}, 'promos': {}, 'trust': {}, 'settings': {}, 'scheduled': {}}
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, ValueError):
        return {'bindings': {}, 'promos': {}, 'trust': {}, 'settings': {}, 'scheduled': {}}

def _save(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

class Storage:
    @staticmethod
    def save_binding(chat_id, channel_username, owner_id):
        data = _load()
        data['bindings'][str(chat_id)] = {'channel': channel_username, 'owner': owner_id}
        _save(data)

    @staticmethod
    def get_binding(chat_id):
        entry = _load()['bindings'].get(str(chat_id))
        return entry['channel'] if entry else None

    @staticmethod
    def get_owner(chat_id):
        entry = _load()['bindings'].get(str(chat_id))
        return entry['owner'] if entry else None

    @staticmethod
    def add_promo(code, days):
        data = _load()
        data['promos'][code] = int(time.time()) + days * 86400
        _save(data)

    @staticmethod
    def check_promo(code):
        data = _load()
        exp = data['promos'].get(code)
        return exp and exp > time.time()

    @staticmethod
    def grant_trust(chat_id, username):
        data = _load()
        trust = data['trust'].setdefault(str(chat_id), [])
        if username not in trust:
            trust.append(username)
        _save(data)

    @staticmethod
    def is_trusted(chat_id, username):
        return username in _load()['trust'].get(str(chat_id), [])

    @staticmethod
    def save_settings(chat_id, settings):
        data = _load()
        data['settings'][str(chat_id)] = settings
        _save(data)

    @staticmethod
    def get_settings(chat_id):
        return _load()['settings'].get(str(chat_id), {})

    @staticmethod
    def add_scheduled(chat_id, ts):
        data = _load()
        sched = data.setdefault('scheduled', {}).setdefault(str(chat_id), [])
        if ts not in sched:
            sched.append(ts)
        _save(data)

    @staticmethod
    def remove_scheduled(chat_id, ts):
        data = _load()
        sched = data.get('scheduled', {}).get(str(chat_id), [])
        if ts in sched:
            sched.remove(ts)
        _save(data)

    @staticmethod
    def get_scheduled(chat_id):
        return _load().get('scheduled', {}).get(str(chat_id), [])
