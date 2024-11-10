import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog, ttk
import threading
import os
import json
import sys
from key import get_key
from gpt import GptChat
from uuid import uuid4

class MessageNode:
    def __init__(self, message, role, parent=None):
        self.id = str(uuid4())
        self.message = message
        self.role = role  # 'user' or 'assistant'
        self.parent = parent  # Reference to parent MessageNode
        self.children = []  # List of MessageNode
        self.selected_child = None  # Currently selected child node

class ConversationTree:
    def __init__(self):
        self.root = None  # Starting MessageNode
        self.current_node = None  # Current position in the conversation

    def add_message(self, message, role):
        new_node = MessageNode(message, role, parent=self.current_node)
        if self.current_node:
            # Add new_node as a child of current_node
            self.current_node.children.append(new_node)
            self.current_node.selected_child = new_node
        else:
            self.root = new_node
        self.current_node = new_node

    def edit_message(self, node, new_message):
        node.message = new_message
        # Remove all child nodes and regenerate conversation from this point
        node.children = []
        node.selected_child = None
        self.current_node = node

    def get_path_from_root(self, node=None):
        if node is None:
            node = self.current_node
        path = []
        while node:
            path.insert(0, node)
            node = node.parent
        return path

    def reset_to_node(self, node):
        self.current_node = node
        node.children = []
        node.selected_child = None

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple Chat")
        self.client = GptChat('sys_prompt.txt', get_key())
        self.conversation_tree = ConversationTree()
        self.message_widgets = {}  # Map message IDs to their widgets
        self.build_gui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_quit)

    def build_gui(self):
        # Main frame
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(expand=True, fill='both')

        # Canvas for scrolling
        self.canvas = tk.Canvas(self.main_frame)
        self.canvas.pack(side='left', fill='both', expand=True)

        # Scrollbar for canvas
        self.scrollbar = tk.Scrollbar(self.main_frame, orient='vertical', command=self.canvas.yview)
        self.scrollbar.pack(side='right', fill='y')

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind('<Configure>', lambda e: self.canvas.configure(scrollregion=self.canvas.bbox('all')))

        # Frame inside the canvas
        self.chat_frame = tk.Frame(self.canvas)
        self.canvas.create_window((0, 0), window=self.chat_frame, anchor='nw')

        # Input area
        self.input_frame = tk.Frame(self.root)
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
        self.status_bar = tk.Label(self.root, text=f"Usage: {self.client.total_tokens} tokens", bd=1, relief=tk.SUNKEN, anchor=tk.W)
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

    def send_message(self):
        user_input = self.input_text.get("1.0", tk.END).strip()
        if not user_input:
            return
        self.input_text.delete("1.0", tk.END)
        if user_input.startswith('\\'):
            self.run_command(user_input[1:])
        else:
            self.conversation_tree.add_message(user_input, 'user')  # Add to conversation tree first
            node = self.conversation_tree.current_node
            self.add_message_box(node)
            self.get_response(node)

    def add_message_box(self, node):
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

        if len(node.children) > 1:
            # If multiple branches exist, provide a dropdown to select
            branch_options = [f"Branch {i+1}" for i in range(len(node.children))]
            selected_branch = tk.StringVar()
            selected_branch.set(branch_options[0])

            branch_menu = ttk.Combobox(controls_frame, textvariable=selected_branch, values=branch_options, state='readonly')
            branch_menu.pack(side='top')
            branch_menu.bind('<<ComboboxSelected>>', lambda event, n=node, sv=selected_branch: self.select_branch(n, sv.get()))
        else:
            # If only one branch exists, check if future branches are possible
            if node.children:
                # Automatically select the only child
                node.selected_child = node.children[0]

        self.message_widgets[node.id] = frame
        self.root.update_idletasks()
        self.canvas.configure(scrollregion=self.canvas.bbox('all'))
        self.canvas.yview_moveto(1)

    def select_branch(self, node, branch_label):
        branch_index = int(branch_label.split(' ')[1]) - 1
        if 0 <= branch_index < len(node.children):
            node.selected_child = node.children[branch_index]
            # Remove existing message boxes after this node
            self.remove_messages_after(node)
            # Display the selected branch
            self.display_from_node(node.selected_child)
        else:
            messagebox.showerror("Error", "Invalid branch selected.")

    def display_from_node(self, node):
        # Display messages starting from the given node
        current = node
        while current:
            self.add_message_box(current)
            current = current.selected_child

    def edit_message(self, node):
        # Prompt user to edit the message
        new_message = simpledialog.askstring("Edit Message", "Edit your message:", initialvalue=node.message)
        if new_message is None:
            return  # User cancelled
        # Remove message boxes after this node
        self.remove_messages_after(node)
        # Update the message in the conversation tree
        self.conversation_tree.edit_message(node, new_message)
        # Update the message box
        self.update_message_box(node, new_message)
        # Regenerate conversation from this point
        self.get_response(node)

    def update_message_box(self, node, new_message):
        frame = self.message_widgets.get(node.id)
        if frame:
            for widget in frame.winfo_children():
                if isinstance(widget, tk.Text):
                    widget.config(state='normal')
                    widget.delete('1.0', tk.END)
                    widget.insert('1.0', new_message)
                    widget.config(state='disabled')

    def remove_messages_after(self, node):
        # Remove all message boxes after the given node
        nodes_to_remove = []
        current = node.selected_child
        while current:
            nodes_to_remove.append(current)
            current = current.selected_child

        for n in nodes_to_remove:
            frame = self.message_widgets.pop(n.id, None)
            if frame:
                frame.destroy()

    def display_message(self, message, role, node):
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
        self.conversation_tree.add_message(response, 'assistant')
        assistant_node = self.conversation_tree.current_node
        self.root.after(0, self.display_message, response, 'assistant', assistant_node)
        self.root.after(0, self.update_status)

    def update_status(self):
        self.status_bar.config(text=f"Usage: {self.client.total_tokens} tokens")

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
        if self.conversation_tree.root is None:
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
        full_name = f'completions/{file_name}.json'
        # Serialize the conversation tree
        data = self.serialize_conversation_tree()
        with open(full_name, 'w', encoding='utf-8') as f:
            json.dump(data, f)
        messagebox.showinfo("Save", f"Conversation saved to {full_name}")
        self.reset_app()

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
            'conversation_tree': serialize_node(root_node) if root_node else None,
        }

    def reset_app(self):
        self.ask_save()
        self.main_frame.destroy()
        self.client = GptChat('sys_prompt.txt', get_key())
        self.conversation_tree = ConversationTree()
        self.message_widgets = {}
        self.build_gui()

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
        self.deserialize_conversation_tree(data.get('conversation_tree'))
        messagebox.showinfo("Load", f"Conversation loaded. Model set to {self.client.model}")

    def deserialize_conversation_tree(self, data):
        # Reconstruct the conversation tree from the serialized data
        def deserialize_node(data, parent=None):
            node = MessageNode(data['message'], data['role'], parent=parent)
            node.id = data['id']
            self.add_message_box(node)
            # Deserialize children
            for child_data in data.get('children', []):
                child_node = deserialize_node(child_data, parent=node)
                node.children.append(child_node)
            # Set selected child
            selected_child_id = data.get('selected_child_id')
            if selected_child_id:
                for child in node.children:
                    if child.id == selected_child_id:
                        node.selected_child = child
                        break
            return node

        if data:
            self.conversation_tree.root = deserialize_node(data)
            # Set the current node to the last node in the selected path
            current = self.conversation_tree.root
            while current.selected_child:
                current = current.selected_child
            self.conversation_tree.current_node = current

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
    app = ChatApp(root)
    root.mainloop()

if __name__ == '__main__':
    main()
