import os
import json
import time
import datetime
from typing import List

from openai import OpenAI

class Message:
    role: str
    content: str

    def __init__(self, role: str, content: str):
        self.role = role
        self.content = content

    def to_obj(self):
        return {
            "role": self.role,
            "content": self.content
        }

class GptChat:
    messages: List[Message]

    def __init__(self, system_prompt_file: str, api_key: str) -> None:
        if not os.path.exists(system_prompt_file):
            raise Exception(f"Could not find sys prompt file at {system_prompt_file}")
        with open(system_prompt_file, 'r', encoding='utf-8') as f:
            self.system_prompt = f.read()
        
        self.model = 'gpt-4o'
        self.openai_client = OpenAI(api_key=api_key)
        self.messages = []
        self.reset_chat()
        self.total_tokens = 0

    def to_obj_list(self):
        l = []
        for msg in self.messages:
            l.append(msg.to_obj())
        return l

    def change_model(self, model: str):
        self.model = model

    def save_completions(self, file_name):
        if len(self.messages) == 0:
            return
        today = datetime.date.today().strftime("%Y-%m-%d")
        if not os.path.exists('completions'):
            os.mkdir('completions')
        with open(f'completions/{file_name}_{today}.json', 'w', encoding='utf-8') as f:
            json.dump({
                "model": self.model,
                "conversation": self.to_obj_list()
            }, f, indent=4)

    def add_message(self, role: str, message: str):
        self.messages.append(Message(role, message))

    def reset_chat(self):
        self.messages = [ ]
        self.add_message("system", self.system_prompt)

    def send(self, message: str, max_tokens=1000) -> str:
        if self.total_tokens >= 64000 - max_tokens:
            raise "Chat Error too many tokens"
        
        self.add_message("user", message)
        
        defaultConfig = {
            "model": self.model,
            "max_tokens": max_tokens,
            "messages": self.to_obj_list(),
            "temperature": 0.5
        }

        try:
            res = self.openai_client.chat.completions.create(**defaultConfig)
        except:
            print('Error when sending chat, retrying in one minute')
            time.sleep(60)
            self.messages = self.messages[:-1]
            self.send(message, max_tokens)
        msg = res.choices[0].message.content.strip()
        print(f"Sending chat with {res.usage.prompt_tokens} tokens")
        print(f"GPT API responded with {res.usage.completion_tokens} tokens")
        self.add_message("assistant", msg)
        self.total_tokens = res.usage.total_tokens
        return msg