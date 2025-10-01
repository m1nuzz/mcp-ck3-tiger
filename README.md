# MCP Server for ck3-tiger

This repository contains a Model Context Protocol (MCP) server that wraps the `ck3-tiger` command-line tool. It allows an AI model like Gemini to validate Crusader Kings 3 mods.

## Features

- Validate an entire mod with optional conflict analysis.
- Get a consolidated report of unique errors.
- Validate with custom rule sets.
- Validate a single file within a mod's context.
- Perform quick syntax-only checks.
- List available mods in the mods directory.

## Setup

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/m1nuzz/mcp-ck3-tiger.git
    cd mcp-ck3-tiger
    ```

2.  **Create a virtual environment and install dependencies:**
    ```bash
    python -m venv venv
    # Activate on Windows
    venv\Scripts\activate
    # Activate on Linux/macOS
    source venv/bin/activate

    pip install -r requirements.txt
    ```

3.  **Configure paths:**
    Create a `.env` file by copying the template:
    ```bash
    # On Windows
    copy .env.example .env
    # On Linux/macOS
    cp .env.example .env
    ```
    Now, edit the `.env` file and set the correct paths for `TIGER_PATH` and `MODS_BASE`.

## Integration with Gemini CLI

```json
{
  "mcpServers": {
    "ck3-tiger-validator": {
      "command": "C:/path/to/your/project/venv/Scripts/python.exe",
      "args": [
        "C:/path/to/your/project/tiger_mcp_server.py"
      ]
    }
  }
}
```

### Available Tools

- `validate_mod(mod_name: str, show_vanilla_errors: bool = False, show_other_mod_errors: bool = False)`
- `consolidate_errors(mod_name: str)`
- `validate_with_custom_config(mod_name: str, config_path: str)`
- `validate_file(file_path: str, mod_name: str)`
- `check_syntax_only(mod_name: str)`
- `list_available_mods()`