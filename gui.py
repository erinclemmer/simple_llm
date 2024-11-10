import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog
import threading
import os
import json
import sys
from key import get_key
from gpt import GptChat

class ChatApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Simple Chat")
        self.client = GptChat('sys_prompt.txt', get_key())
        self.build_gui()
        self.root.protocol("WM_DELETE_WINDOW", self.on_quit)

    def build_gui(self):
        # Main frame
        self.main_frame = tk.Frame(self.root)
        self.main_frame.pack(expand=True, fill='both')

        # Conversation display area
        self.conversation_text = tk.Text(self.main_frame, wrap='word', state='disabled')
        self.conversation_text.pack(expand=True, fill='both')

        # Scrollbar for conversation
        self.conversation_scrollbar = tk.Scrollbar(self.conversation_text, command=self.conversation_text.yview)
        self.conversation_text['yscrollcommand'] = self.conversation_scrollbar.set
        self.conversation_scrollbar.pack(side='right', fill='y')

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
        self.status_bar = tk.Label(self.main_frame, text=f"Usage: {self.client.total_tokens} tokens", bd=1, relief=tk.SUNKEN, anchor=tk.W)
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
        self.display_message("User", user_input)
        if user_input[0] == '\\':
            self.run_command(user_input[1:])
        else:
            self.get_response(user_input)

    def display_message(self, sender, message):
        self.conversation_text.config(state='normal')
        self.conversation_text.insert(tk.END, f"{sender}:\n{message}\n\n")
        self.conversation_text.config(state='disabled')
        self.conversation_text.see(tk.END)

    def get_response(self, user_input):
        def worker():
            try:
                response = self.client.send(user_input)
                self.root.after(0, self.display_message, self.client.model, response)
                self.root.after(0, self.update_status)
            except Exception as e:
                self.root.after(0, messagebox.showerror, "Error", str(e))
        threading.Thread(target=worker).start()

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
save [file_name]: saves the file to "completions/[file_name]_[today].json" and resets the app
load: go to load menu (app will be reset)
reset: reset conversation (app will be reset)
change_model: change current model
include [file_name]: include file data in the current context
regen: rerun last message again
'''
        messagebox.showinfo("Help", help_text)

    def ask_save(self):
        if len(self.client.messages) < 2:
            return
        if messagebox.askyesno("Save", "Message history not empty, save current conversation?"):
            file_name = simpledialog.askstring("Save", "File Name:")
            if file_name:
                self.client.save_completions(file_name)
                messagebox.showinfo("Save", f"Conversation saved to completions/{file_name}")

    def save_conversation(self, args):
        if args:
            file_name = args[0]
        else:
            file_name = simpledialog.askstring("Save", "File Name:")
            if not file_name:
                return
        self.client.save_completions(file_name)
        messagebox.showinfo("Save", f"Conversation saved to completions/{file_name}")
        self.reset_app()

    def reset_app(self):
        self.ask_save()
        self.main_frame.destroy()
        self.client = GptChat('sys_prompt.txt', get_key())
        self.build_gui()
        self.display_message('System', 'Chat reset')

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
        self.client.add_message("user", f'Here is a document that I want to include in our conversation:\n{text}')
        self.client.add_message("assistant", "Ok")
        self.display_message("System", f"Including data in conversation from {full_name}:\n{text}")

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
        self.display_message("System", f"Conversation loaded. Model changed to {model}")
        model = data['model']
        for msg in data["conversation"]:
            role = msg['role']
            content = msg['content']
            self.client.add_message(role, content)
            self.display_message(role, content)
        self.client.change_model(model)

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
        try:
            self.client.messages.pop()
            last_message = self.client.messages.pop()
            self.display_message("System", "Regenerating last message...")
            self.get_response(last_message.content)
        except IndexError:
            messagebox.showerror("Error", "No messages to regenerate.")

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
