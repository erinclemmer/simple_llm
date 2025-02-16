# simple_llm

A lightweight, tree-based conversational UI built on top of a local or remote language model (LLM). This project lets you interact with a GPT-like model in a graphical interface powered by Tkinter, enabling you to branch, edit, and regenerate responses.

## Overview

`simple_llm` provides a GUI for chatting with an LLM. The conversation is represented internally as a _tree_, allowing you to:

- Maintain multiple branching paths of conversation
- Edit previous messages (creating alternate branches)
- Regenerate the latest assistant response
- Include external text files into the conversation context

It uses:
- **Tkinter** for the GUI
- A custom `GptChat` client (from `gpt.py`) to communicate with the model
- A `key.py` file that provides API credentials (or other required keys)

## Features

1. **Conversation Tree**  
   Each user or assistant message is a node in a tree. When you edit a user message, a new branch is created, preserving the original path.

2. **Branch Selection**  
   If multiple responses are generated for a single user message (e.g., you edited the message), the UI provides a dropdown to choose which branch to follow.

3. **Commands**  
   Commands (prefixed with a backslash `\`) allow you to save, load, reset, and perform other actions directly in the chat interface:
   - **\help** – Display the help menu
   - **\save [file_name]** – Save the conversation and reset the app
   - **\load** – Load a conversation from file
   - **\reset** – Reset the conversation
   - **\change_model** – Open a dialog to change the current model
   - **\include [file_name]** – Include text from a file in the conversation
   - **\regen** – Regenerate the last assistant message

4. **File Menu**  
   A traditional menu bar (top of the window) with standard operations: **Save**, **Load**, **Reset**, **Quit**.

5. **Model Switching**  
   Easily swap between multiple model backends in the **Options** menu (for example, `gpt-4o`, `gpt-4o-mini`, etc.).

6. **Token Usage Display**  
   The status bar at the bottom shows the current model and total token usage.

## Installation & Setup

1. **Clone or Download** this repository.
2. Make sure you have **Python 3.7+** installed.
3. Install dependencies (e.g., `tkinter`, if not already available; typically on Linux you may need the `python3-tk` package). The code also depends on your own `gpt.py` and `key.py`, which provide:
   - `GptChat` class (for sending messages to the model)
   - `get_key()` function (for retrieving an API key or other secrets)

4. Prepare the required files:
   - **`sys_prompt.txt`** – Contains your system prompt or instructions for the conversation.
   - **`key.py`** – Must define `get_key()` to return the required API key or credentials.
   - **`gpt.py`** – Must define a `GptChat` class with:
     - `self.system_prompt` (string: system-level instructions)
     - `reset_chat()` (resets internal state)
     - `add_message(role, content)` (queues a message for context)
     - `send(message)` (sends the user message to the LLM and returns the assistant response)
     - `total_tokens` (tracks usage)
     - `change_model(model_name)` (updates the LLM model)

5. **Run the application**:

   ```bash
   python simple_llm.py
   ```

   Once running, the main window launches with:
   - A text area for user input.
   - A scrollable region displaying conversation messages.
   - A menu bar for file and settings operations.

## Usage

1. **Typing Messages**  
   - Enter your text in the bottom text box and press **Enter** to send.
   - Use **Shift+Enter** if you want to add a newline without sending.

2. **Commands**  
   If the first character of your input is a backslash (`\`), it is treated as a command.  
   Example:  
   ```txt
   \help
   ```
   The available commands are:
   - **help** – Shows help instructions in a pop-up
   - **save [filename]** – Saves the current conversation as a JSON file in `completions/`
   - **load** – Opens a file dialog to load a previously saved conversation
   - **reset** – Resets the conversation (with an option to save first)
   - **change_model** – Opens a dialog to pick a different model
   - **include [file_name]** – Includes the contents of the specified file in the conversation
   - **regen** – Deletes and regenerates the last assistant response
   - **quit** – Quits the application

3. **Menu Bar**  
   - **File Menu**: **Save**, **Load**, **Reset**, **Quit**  
   - **Options Menu**: **Change Model**, **Include File**, **Regenerate**  
   - **Help Menu**: **Help**  

4. **Editing and Branching**  
   - Each user message has an **Edit** button to revise your message retroactively.
   - When you edit a message, a new branch is created. You can select which branch of the conversation to continue from using the branch dropdown if multiple replies exist.

5. **Saving & Loading**  
   - Saves conversation as a structured JSON in the `completions/` folder.
   - Reloading the conversation re-creates the same conversation tree and re-displays it.

## Folder Structure

Below is a typical directory structure you might have:

```
simple_llm/
├─ completions/            <-- Saved conversation files are stored here
├─ data/                   <-- Optionally store documents to 'include' in conversation
├─ sys_prompt.txt          <-- System prompt instructions for the LLM
├─ key.py                  <-- Contains get_key() to return your LLM API key
├─ gpt.py                  <-- Contains GptChat class for model interaction
├─ simple_llm.py           <-- Main ChatApp script
└─ README.md               <-- This file
```

## Extending the Project

- **Customizing the LLM**: Modify `gpt.py` or replace it with your own model client.  
- **Adding Commands**: In the `run_command` method of `ChatApp`, add new commands to suit your workflow.  
- **User Interface**: The Tkinter widgets are built in the `build_gui` method. You can style or rearrange them.  
- **Conversation Persistence**: The logic for saving and loading the conversation tree is in `save_conversation` and `deserialize_conversation_tree`. Adjust it if you want to use a different storage format or location.

## Troubleshooting

- **Tkinter not found**: Install it (on Ubuntu/Debian, `sudo apt-get install python3-tk`; on Windows, it comes bundled with most Python installers).
- **Key/Model Issues**: Ensure `key.py` provides a valid `get_key()` and `gpt.py` is correctly configured for your model.
- **File not found**: When including files, make sure you select or specify the correct path.
