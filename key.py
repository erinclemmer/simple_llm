import os
import json
import openai

def get_key():
    if not os.path.exists('config.json'):
        raise "Cannot find config.json"

    with open('config.json', 'r', encoding='utf-8') as f:
        try:
            config = json.load(f)
        except:
            raise "Could not load config.json"

    if not 'openai_key' in config:
        raise "Could not find \"openai_key\" in config.json"

    return config['openai_key']