# TODO: Regeneration should use tree too

import os
import json
import datetime
from uuid import uuid4
from typing import List, Dict

import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk

from key import get_key
from gpt import GptChat

class MessageNode:
    def __init__(self, message: str, role: str, parent=None, id=None):
        self.id = str(uuid4()) if id is None else id
        self.message = message
        if role != 'user' and role != 'assistant' and role != 'system':
            raise Exception(f'Bad role argument for Message node: {role}')
        self.role = role  # 'user' or 'assistant'
        self.parent = parent  # Reference to parent MessageNode
        self.children = []  # List of MessageNode
        self.selected_child = None  # Currently selected child node

    def add_child(self, node):
        self.children.append(node)
        node.parent = self
        self.selected_child = node

    def select_child(self, index: int):
        if index < 0 or index > len(self.children):
            raise Exception(f'Child selection out of range: {index} must be less than {len(self.children)}')
        self.selected_child = self.children[index]
        return self.selected_child
    
    def selected_child_index(self):
        if self.selected_child is None:
            return -1
        for i in range(len(self.children)):
            child: MessageNode = self.children[i]
            if child.id == self.selected_child.id:
                return i
        return -1

class ConversationTree:
    def __init__(self, sys_prompt: str):
        self.root = MessageNode(sys_prompt, 'system', None)  # Starting MessageNode
        self.current_node = self.root  # Current position in the conversation

    def add_message(self, message: str, role: str):
        new_node = MessageNode(message, role, parent=self.current_node)
        self.current_node.add_child(new_node)
        self.current_node = new_node
        return new_node

    def edit_message(self, edit_node: MessageNode, new_message: str):
        new_node = MessageNode(new_message, 'user', edit_node.parent)
        parent_node: MessageNode = edit_node.parent
        parent_node.add_child(new_node)
        self.current_node = new_node
        return new_node

    def get_path_from_root(self, node: MessageNode = None):
        if node is None:
            node = self.current_node
        path = []
        while node:
            path.insert(0, node)
            node = node.parent
        return path
    
    def reset_root(self, root_node: MessageNode):
        self.root = root_node
        current: MessageNode = self.root.selected_child
        while True:
            if current.selected_child is None:
                break
            current: MessageNode = current.selected_child
        self.current_node = current

class ChatApp:
    root: tk.Tk
    message_widgets: Dict[str, tk.Frame]

    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Simple Chat")
        self.client = GptChat('sys_prompt.txt', get_key())
        self.conversation_tree = ConversationTree(self.client.system_prompt)
        self.message_widgets = {}  # Map message IDs to their widgets
        self.build_gui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_quit)

    def build_gui(self):
        # Main frame
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(expand=True, fill='both')

        self.message_frame = tk.Frame(self.main_frame)
        self.message_frame.pack(expand=True, fill='both')

        # Canvas for scrolling
        self.canvas = tk.Canvas(self.message_frame)
        self.canvas.pack(side='left', fill='both', expand=True)

        # Scrollbar for canvas
        self.scrollbar = tk.Scrollbar(self.message_frame, orient='vertical', command=self.canvas.yview)
        self.scrollbar.pack(side='right', fill='y')

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))

        # Frame inside the canvas
        self.chat_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.chat_frame, anchor='nw')

        # Input area
        self.input_frame = tk.Frame(self.main_frame)
        self.input_frame.pack(fill='x')

        self.input_text = tk.Text(self.input_frame, height=3)
        self.input_text.pack(side='left', expand=True, fill='both')

        # Scrollbar for input
        self.input_scrollbar = tk.Scrollbar(self.input_text, command=self.input_text.yview)
        self.input_text['yscrollcommand'] = self.input_scrollbar.set
        self.input_scrollbar.pack(side='right', fill='y')

        # Bind Enter and Shift+Enter
        self.input_text.bind('<Return>', self.on_enter_pressed)

        # Status bar
        self.status_bar = tk.Label(self.main_frame, text="", bd=1, relief=tk.SUNKEN, anchor=tk.W)
        self.status_bar.pack(side=tk.BOTTOM, fill=tk.X)

        # Menu bar
        self.menu_bar = tk.Menu(self.root)
        self.build_menu()
        self.root.config(menu=self.menu_bar)

    def build_menu(self):
        # File menu
        file_menu = tk.Menu(self.menu_bar, tearoff=0)
        file_menu.add_command(label="Save", command=lambda: self.run_command("save"))
        file_menu.add_command(label="Load", command=lambda: self.run_command("load"))
        file_menu.add_separator()
        file_menu.add_command(label="Reset", command=lambda: self.run_command("reset"))
        file_menu.add_separator()
        file_menu.add_command(label="Quit", command=self.on_quit)
        self.menu_bar.add_cascade(label="File", menu=file_menu)

        # Options menu
        options_menu = tk.Menu(self.menu_bar, tearoff=0)
        options_menu.add_command(label="Change Model", command=lambda: self.run_command("change_model"))
        options_menu.add_command(label="Include File", command=self.include)
        options_menu.add_command(label="Regenerate", command=lambda: self.run_command("regen"))
        self.menu_bar.add_cascade(label="Options", menu=options_menu)

        # Help menu
        help_menu_bar = tk.Menu(self.menu_bar, tearoff=0)
        help_menu_bar.add_command(label="Help", command=lambda: self.run_command("help"))
        self.menu_bar.add_cascade(label="Help", menu=help_menu_bar)

    def get_and_reset_user_input(self):
        user_input = self.input_text.get("1.0", tk.END).strip()
        if not user_input:
            return
        self.input_text.delete("1.0", tk.END)
        return user_input

    def send_message(self):
        user_input = self.get_and_reset_user_input()
        if user_input.startswith('\\'):
            self.run_command(user_input[1:])
        else:
            user_node = self.conversation_tree.add_message(user_input, 'user')  # Add to conversation tree first
            self.add_message_box(user_node)
            self.get_response(user_node)

    def add_message_box(self, node: MessageNode):
        # If the message already has a widget, don't create it again
        if node.id in self.message_widgets:
            return

        frame = tk.Frame(self.chat_frame, bd=2, relief='groove', padx=5, pady=5)
        frame.pack(fill='x', padx=5, pady=5)

        message_label = tk.Text(frame, wrap='word', height=4, bg='#f0f0f0' if node.role == 'assistant' else '#e0ffe0')
        message_label.insert('1.0', node.message)
        message_label.config(state='disabled')
        message_label.pack(side='left', fill='both', expand=True)

        controls_frame = tk.Frame(frame)
        controls_frame.pack(side='right', fill='y')

        if node.role == 'user':
            edit_button = tk.Button(controls_frame, text='Edit', command=lambda n=node: self.edit_message(n))
            edit_button.pack(side='top')

        parent: MessageNode = node.parent
        children: List[MessageNode] = parent.children

        if len(children) > 1:
            # If multiple branches exist, provide a dropdown to select
            branch_options = [f"Branch {i+1}" for i in range(len(children))]
            selected_branch = tk.StringVar()
            selected_branch.set(branch_options[parent.selected_child_index()])

            branch_menu = ttk.Combobox(controls_frame, textvariable=selected_branch, values=branch_options, state='readonly')
            branch_menu.pack(side='top')
            branch_menu.bind('<<ComboboxSelected>>', lambda event, n=node, sv=selected_branch: self.select_branch(n, sv.get()))

        self.message_widgets[node.id] = frame
        self.root.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        self.canvas.yview_moveto(1)

    def select_branch(self, node: MessageNode, branch_label: str):
        branch_index = int(branch_label.split(' ')[1]) - 1
        parent: MessageNode = node.parent
        children: List[MessageNode] = parent.children
        if 0 <= branch_index < len(children):
            # Remove existing message boxes after this node
            self.remove_messages_after(parent)
            selected_node = parent.select_child(branch_index)
            # Display the selected branch
            self.display_from_node(selected_node)
        else:
            messagebox.showerror("Error", "Invalid branch selected.")

    def display_from_node(self, node: MessageNode):
        # Display messages starting from the given node
        current = node
        while current:
            self.add_message_box(current)
            current = current.selected_child

    def edit_message(self, node: MessageNode):
        # Prompt user to edit the message
        new_message = simpledialog.askstring("Edit Message", "Edit your message:", initialvalue=node.message)
        if new_message is None:
            return  # User cancelled
        # Remove message boxes after this node
        self.remove_messages_after(node.parent)
        # Update the message in the conversation tree
        edited_node = self.conversation_tree.edit_message(node, new_message)
        self.add_message_box(edited_node)
        # Regenerate conversation from this point
        self.get_response(edited_node)

    def remove_messages_after(self, node: MessageNode):
        # Remove all message boxes after the given node
        nodes_to_remove: List[MessageNode] = []
        current: MessageNode = node.selected_child
        while current:
            nodes_to_remove.append(current)
            current: MessageNode = current.selected_child

        for n in nodes_to_remove:
            frame = self.message_widgets[n.id]
            if frame:
                frame.destroy()
                del self.message_widgets[n.id]

    def display_message(self, node):
        self.add_message_box(node)

    def get_response(self, node):
        # Build the message path up to the current node
        path = self.conversation_tree.get_path_from_root(node)
        self.client.reset_chat()
        for node in path[:-1]:
            self.client.add_message(node.role, node.message)
        # Send the messages to the client
        response = self.client.send(path[-1].message)
        # Add assistant's response to the conversation tree
        assistant_node = self.conversation_tree.add_message(response, 'assistant')
        self.root.after(0, self.display_message, assistant_node)
        self.root.after(0, self.update_status)

    def update_status(self):
        self.status_bar.config(text=f"Usage: {self.client.total_tokens} tokens, Model: {self.client.model}")

    def run_command(self, cmd: str):
        parts = cmd.strip().split(' ')
        command = parts[0]
        args = parts[1:]
        if command == 'help':
            self.help_menu()
        elif command == 'save':
            self.save_conversation(args)
        elif command == 'reset':
            self.reset_app()
        elif command == 'load':
            self.load_menu()
        elif command == 'change_model':
            self.model_menu()
        elif command == 'include':
            self.include(args[0] if args else None)
        elif command == 'regen':
            self.regen_message()
        elif command == 'quit':
            self.on_quit()
        else:
            messagebox.showerror("Error", f"Unknown command: {cmd}")

    def help_menu(self):
        help_text = '''
HELP MENU:
save [file_name]: saves the conversation tree to "completions/[file_name]_[today].json" and resets the app
load: go to load menu (app will be reset)
reset: reset conversation (app will be reset)
change_model: change current model
include [file_name]: include file data in the current context
regen: rerun last message again
'''
        messagebox.showinfo("Help", help_text)

    def ask_save(self):
        if len(self.conversation_tree.root.children) == 0:
            return
        if messagebox.askyesno("Save", "Conversation not empty, save current conversation?"):
            file_name = simpledialog.askstring("Save", "File Name:")
            if file_name:
                self.save_conversation([file_name])

    def save_conversation(self, args):
        if args:
            file_name = args[0]
        else:
            file_name = simpledialog.askstring("Save", "File Name:")
            if not file_name:
                return
        if not os.path.exists('completions'):
            os.makedirs('completions')
        today = datetime.date.today().strftime("%Y-%m-%d")
        full_name = f'completions/{file_name}_{today}.json'
        # Serialize the conversation tree
        data = self.serialize_conversation_tree()
        with open(full_name, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4)
        messagebox.showinfo("Save", f"Conversation saved to {full_name}")
        self.reset_app(False)

    def serialize_conversation_tree(self):
        # Serialize the conversation tree into a JSON-serializable format
        def serialize_node(node):
            data = {
                'id': node.id,
                'message': node.message,
                'role': node.role,
                'children': [serialize_node(child) for child in node.children],
                'selected_child_id': node.selected_child.id if node.selected_child else None,
            }
            return data
        root_node = self.conversation_tree.root
        return {
            'model': self.client.model,
            'total_tokens': self.client.total_tokens,
            'conversation_tree': serialize_node(root_node) if root_node else None,
        }

    def reset_app(self, ask_save: bool = False):
        if ask_save:
            self.ask_save()
        self.main_frame.destroy()
        self.client = GptChat('sys_prompt.txt', get_key())
        self.conversation_tree = ConversationTree(self.client.system_prompt)
        self.message_widgets = {}
        self.build_gui()
        self.update_status()

    def include(self, file_name: str = None):
        if file_name is None:
            file_name = filedialog.askopenfilename(initialdir='data', title="Select file to include",
                                                   filetypes=(("Text files", "*.txt"), ("All files", "*.*")))
            if not file_name:
                return
        full_name = file_name
        if not os.path.exists(full_name):
            messagebox.showerror("Error", f"File {full_name} does not exist")
            return
        with open(full_name, 'r', encoding='utf-8') as f:
            text = f.read()
        self.conversation_tree.add_message(f'Here is a document that I want to include in our conversation:\n{text}', 'user')
        node = self.conversation_tree.current_node
        self.add_message_box(node)
        self.get_response(node)

    def load_file(self, full_name: str):
        if not os.path.exists(full_name):
            messagebox.showerror("Error", f"Could not find file {full_name}")
            return
        with open(full_name, 'r', encoding='utf-8') as f:
            try:
                data = json.load(f)
            except Exception as e:
                messagebox.showerror("Error", f"Could not load file {full_name}\n{e}")
                return
        self.reset_app()
        self.client.change_model(data.get('model', self.client.model))
        self.client.total_tokens = data.get('total_tokens', 0)
        self.deserialize_conversation_tree(data.get('conversation_tree'))
        self.display_from_node(self.conversation_tree.root.selected_child)
        self.update_status()
        messagebox.showinfo("Load", f"Conversation loaded. Model set to {self.client.model}")

    def deserialize_conversation_tree(self, data):
        if not data:
            return
        
        # Reconstruct the conversation tree from the serialized data
        def deserialize_node(data, parent=None):
            node = MessageNode(data['message'], data['role'], parent=parent, id=data['id'])
            # Deserialize children
            for child_data in data.get('children', []):
                child_node = deserialize_node(child_data, parent=node)
                node.add_child(child_node)
            return node

        self.conversation_tree.reset_root(deserialize_node(data))

    def load_menu(self):
        self.ask_save()
        if not os.path.exists('completions'):
            messagebox.showerror("Error", "No completions folder found")
            return
        file_name = filedialog.askopenfilename(initialdir='completions', title="Select file",
                                               filetypes=(("JSON files", "*.json"), ("All files", "*.*")))
        if file_name:
            self.load_file(file_name)

    def model_menu(self):
        models = [
            'gpt-4o',
            'gpt-4o-mini',
            'o1-preview',
            'o1-mini'
        ]
        def set_model(model):
            self.client.change_model(model)
            messagebox.showinfo("Model Changed", f"Model changed to {model}")
            self.update_status()
            model_window.destroy()
        model_window = tk.Toplevel(self.root)
        model_window.title("Select Model")
        tk.Label(model_window, text="Select a model:").pack()
        for model in models:
            tk.Button(model_window, text=model, command=lambda m=model: set_model(m)).pack(fill='x')
        tk.Button(model_window, text="Cancel", command=model_window.destroy).pack(fill='x')

    def regen_message(self):
        if self.conversation_tree.current_node and self.conversation_tree.current_node.role == 'assistant':
            # Remove the assistant's last message and regenerate
            parent_node = self.conversation_tree.current_node.parent
            self.remove_messages_after(parent_node)
            self.conversation_tree.current_node = parent_node
            self.conversation_tree.current_node.children.remove(self.conversation_tree.current_node.selected_child)
            self.conversation_tree.current_node.selected_child = None
            self.get_response(self.conversation_tree.current_node)
        else:
            messagebox.showerror("Error", "No assistant message to regenerate.")

    # Handle Enter and Shift+Enter in input_text
    def on_enter_pressed(self, event):
        if (event.state & 0x0001) == 0x0001:
            # Shift is pressed, insert newline
            self.input_text.insert(tk.INSERT, '\n')
            return 'break'
        else:
            # Shift is not pressed, send message
            self.send_message()
            return 'break'

    def on_quit(self):
        self.root.quit()
        self.root.destroy()

def main():
    root = tk.Tk()
    root.geometry("1280x720")
    ChatApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
