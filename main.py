import os
import sys
import json
from key import get_key
from gpt import GptChat

print('Loading client...')
client = GptChat('sys_prompt.txt', get_key())
print('Welcome to simple chat!\n\n')

def regen_message():
    print('Regenerating last message')
    client.messages.pop()
    last_message = client.messages.pop()
    res = client.send(last_message.content)
    print(f'\n\n{client.model}:\n{res}')

def model_menu():
    models = [
        'gpt-4o',
        'gpt-4o-mini',
        'o1-preview',
        'o1-mini'
    ]
    i = 1
    for model in models:
        print(f'{i}. {model}')
        i += 1
    print(f'{i}. Main menu')
    try:
        selection = int(input('> '))
    except:
        print('\nERROR: Could not parse selection\n')
        model_menu()
        return
    if selection < 1 or selection > len(models) + 1:
        print('\nERROR: selection out of bounds')
        model_menu()
        return
    if selection == i:
        return
    model = models[selection - 1]
    client.change_model(model)
    print(f'\nModel changed to {model}\n')

def help_menu():
    print('''\n\n
HELP MENU:       
save [file_name]: saves the file to "comletions/[file_name]_[today].json"
load: go to load menu
reset: reset conversation
change_model: change current model
include [file_name]: include file data in the current context
regen: rerun last message again
\n\n''')

def include(file_name: str):
    full_name = f'data/{file_name}'
    if not os.path.exists(full_name):
        print(f'\n\nERROR: file {full_name} does not exist')
        return
    with open(full_name, 'r', encoding='utf-8') as f:
        text = f.read()
    client.add_message("user", f'Here is a document that I want to include in our conversation:\n{text}')
    client.add_message("assistant", "Ok")
    print(f'Including data in conversation from {full_name}:\n{text}')

def load_file(file_name: str):
    full_name = f'completions/{file_name}'
    if not os.path.exists(full_name):
        print(f'\nERROR: could not find file {full_name}\n')
    with open(full_name, 'r', encoding='utf-8') as f:
        try:
            data = json.load(f)
        except:
            print(f'\nERROR: could not load file {full_name}')
            return
    print('\nConversation Loaded')

    client.reset_chat()
    client.messages = []
    model = data['model']
    for msg in data["conversation"]:
        role = msg['role']
        content = msg['content']
        client.add_message(role, content)
        print(f'\n\n{role}:\n{content}')
    client.change_model(model)

def ask_save():
    if len(client.messages) < 2:
        return
    print('\nNOTE: Message history not empty, save current conversation?')
    cmd = input('save? (y/n): ').lower()
    if cmd == 'y':
        file_name = input('File Name: ')
        client.save_completions(file_name)
        client.reset_chat()

def load_menu():
    ask_save()
    if not os.path.exists('completions'):
        print('\nERROR: No completions folder found\n')
        return
    i = 1
    print('\n\nLOAD MENU:')
    files = os.listdir('completions')
    for file in files:
        print(f'{i}. {file}')
        i += 1
    print(f'{i}. Main Menu')
    try:
        selection = int(input('> '))
    except:
        print('\nERROR: Could not parse input\n')
        load_menu()
        return

    if selection < 0 or selection > len(files) + 1:
        print('\nERROR: invalid selection')
        load_menu()
        return
    if selection == i:
        return
    load_file(files[selection - 1])

def run_command(cmd: str):
    parts = cmd.split(' ')
    if parts[0] == 'help':
        help_menu()
    if parts[0] == 'save':
        if not len(parts) == 2:
            print('\nERROR: \\save usage: \\save [file_name]\n')
            return
        client.save_completions(parts[1])
        print(f'Conversation saved to completions/{parts[1]}')
    if parts[0] == 'reset':
        ask_save()
        client.reset_chat()
    if parts[0] == 'load':
        load_menu()
    if parts[0] == 'change_model':
        model_menu()
    if parts[0] == 'include':
        include(parts[1])
    if parts[0] == 'regen':
        regen_message()
    if parts[0] == 'quit':
        sys.exit()

def loop(current_input: str = ''):
    print(f'Usage: {client.total_tokens} tokens')
    inp = current_input + input('User> ')
    if len(inp) == 0:
        return
    if inp[0] == '\\':
        run_command(inp[1:])
        return
    if inp[-1] == '\\':
        loop(inp + '\n')
        return
    res = client.send(inp)
    print(f'\n{client.model}:\n{res}\n\n')

while True:
    loop()