from mcp.server.fastmcp import FastMCP
import subprocess
import json
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Initialize MCP server
mcp = FastMCP("ck3-tiger-validator")

# Get paths from environment variables
TIGER_PATH = os.environ.get("TIGER_PATH")
MODS_BASE = os.environ.get("MODS_BASE")

# Validate that paths are set
if not TIGER_PATH:
    raise ValueError("TIGER_PATH is not set in your .env file or environment variables.")
if not MODS_BASE:
    # Fallback to a default path if MODS_BASE is not set
    print("Warning: MODS_BASE not set, falling back to default. Consider setting it in .env")
    MODS_BASE = os.path.expanduser(r"~/Documents/Paradox Interactive/Crusader Kings III/mod")

def _run_tiger_and_parse(mod_descriptor: str, extra_args: list = None) -> dict:
    """A helper function to run tiger, handle subprocess calls, and parse JSON."""
    if not os.path.exists(mod_descriptor):
        return {"success": False, "error": f"Mod file not found: {mod_descriptor}"}

    command = [TIGER_PATH, "--json", mod_descriptor]
    if extra_args:
        command.extend(extra_args)

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
            encoding='utf-8'
        )

        if result.stdout:
            errors = json.loads(result.stdout)
            errors_by_severity = {}
            for error in errors:
                severity = error.get("severity", "unknown")
                if severity not in errors_by_severity:
                    errors_by_severity[severity] = []
                errors_by_severity[severity].append(error)

            return {
                "success": True,
                "valid": len(errors) == 0,
                "total_errors": len(errors),
                "errors": errors,
                "errors_by_severity": errors_by_severity,
                "summary": f"Found errors: {len(errors)}"
            }
        else:
            if result.stderr:
                return {"success": False, "error": "Tiger process produced an error", "stderr": result.stderr}
            return {
                "success": True, "valid": True, "total_errors": 0, "errors": [], "summary": "No errors found"
            }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Validation took too long (120 second timeout)"}
    except json.JSONDecodeError as e:
        return {"success": False, "error": f"JSON parsing error: {str(e)}"}
    except FileNotFoundError:
        return {"success": False, "error": f"TIGER_PATH is incorrect or ck3-tiger.exe not found at: {TIGER_PATH}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}


@mcp.tool()
def validate_mod(mod_name: str, show_vanilla_errors: bool = False, show_other_mod_errors: bool = False) -> dict:
    """Validates a CK3 mod, with optional checks for vanilla and other mod conflicts.

    Args:
        mod_name: The name of the mod.
        show_vanilla_errors: If true, shows errors from base game files.
        show_other_mod_errors: If true, shows errors from other enabled mods.

    Returns:
        A dictionary with validation results.
    """
    mod_descriptor = os.path.join(MODS_BASE, f"{mod_name}.mod")
    extra_args = []
    if show_vanilla_errors:
        extra_args.append("--show-vanilla")
    if show_other_mod_errors:
        extra_args.append("--show-mods")
    
    return _run_tiger_and_parse(mod_descriptor, extra_args)

@mcp.tool()
def consolidate_errors(mod_name: str) -> dict:
    """Validates a mod, but only logs the first occurrence of each error type.

    Args:
        mod_name: The name of the mod.

    Returns:
        A dictionary containing the raw consolidated output from the validator.
    """
    mod_descriptor = os.path.join(MODS_BASE, f"{mod_name}.mod")
    if not os.path.exists(mod_descriptor):
        return {"success": False, "error": f"Mod file not found: {mod_descriptor}"}

    command = [TIGER_PATH, mod_descriptor, "--consolidate"]

    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=120,
            encoding='utf-8'
        )

        if result.stderr:
            return {"success": False, "error": "Tiger process produced an error", "stderr": result.stderr}
        
        return {
            "success": True,
            "output": result.stdout
        }

    except subprocess.TimeoutExpired:
        return {"success": False, "error": "Validation took too long (120 second timeout)"}
    except FileNotFoundError:
        return {"success": False, "error": f"TIGER_PATH is incorrect or ck3-tiger.exe not found at: {TIGER_PATH}"}
    except Exception as e:
        return {"success": False, "error": f"Unexpected error: {str(e)}"}

@mcp.tool()
def validate_with_custom_config(mod_name: str, config_path: str) -> dict:
    """Validates a mod using a custom configuration file.

    Args:
        mod_name: The name of the mod.
        config_path: The absolute path to the .conf configuration file.

    Returns:
        A dictionary with validation results.
    """
    if not os.path.exists(config_path):
        return {"success": False, "error": f"Configuration file not found: {config_path}"}
    
    mod_descriptor = os.path.join(MODS_BASE, f"{mod_name}.mod")
    return _run_tiger_and_parse(mod_descriptor, ["--config", config_path])


@mcp.tool()
def validate_file(file_path: str, mod_name: str) -> dict:
    """Validates a specific file in the context of a mod

    Args:
        file_path: Relative path to the file within the mod
        mod_name: Mod name

    Returns:
        A dictionary with errors for that file
    """
    try:
        # First, validate the entire mod
        full_result = validate_mod(mod_name)
        if not full_result.get("success"):
            return full_result

        all_errors = full_result.get("errors", [])

        # Filter for errors related to the specified file only
        file_errors = []
        for error in all_errors:
            for location in error.get("locations", []):
                if location.get("path") == file_path:
                    file_errors.append(error)
                    break  # Avoid duplicating errors if a single error has multiple locations in the same file

        return {
            "success": True,
            "file": file_path,
            "valid": len(file_errors) == 0,
            "errors_count": len(file_errors),
            "errors": file_errors
        }
    except Exception as e:
        return {"success": False, "error": f"Error during file validation: {str(e)}"}

@mcp.tool()
def check_syntax_only(mod_name: str) -> dict:
    """Performs a quick syntax-only check without deep analysis

    Args:
        mod_name: Mod name

    Returns:
        A dictionary with syntax errors
    """
    try:
        mod_descriptor = os.path.join(MODS_BASE, f"{mod_name}.mod")
        if not os.path.exists(mod_descriptor):
            return {"success": False, "error": f"Mod file not found: {mod_descriptor}"}

        # Running with a filter for syntax errors only
        result = subprocess.run(
            [TIGER_PATH, "--json", mod_descriptor],
            capture_output=True,
            text=True,
            timeout=60,
            encoding='utf-8'
        )

        if result.stdout:
            all_errors = json.loads(result.stdout)
            syntax_errors = [e for e in all_errors if e.get("key") in ["syntax", "structure", "encoding"]]
            return {
                "success": True,
                "valid": len(syntax_errors) == 0,
                "syntax_errors_count": len(syntax_errors),
                "errors": syntax_errors
            }
        else:
            return {
                "success": True,
                "valid": True,
                "syntax_errors_count": 0,
                "errors": []
            }
    except Exception as e:
        return {"success": False, "error": str(e)}

@mcp.tool()
def list_available_mods() -> dict:
    """Returns a list of available mods in the directory

    Returns:
        A list of found .mod files
    """
    try:
        if not os.path.exists(MODS_BASE):
            return {"success": False, "error": f"Mods directory not found: {MODS_BASE}"}

        mod_files = [f[:-4] for f in os.listdir(MODS_BASE) if f.endswith('.mod')]
        return {
            "success": True,
            "mods": mod_files,
            "count": len(mod_files),
            "base_path": MODS_BASE
        }
    except Exception as e:
        return {"success": False, "error": str(e)}

def main():
    """Starts the MCP server via stdio transport"""
    import sys
    import logging

    # Configure logging (to stderr, so it doesn't interfere with the MCP protocol)
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        stream=sys.stderr
    )
    logging.info("Starting ck3-tiger MCP server...")

    mcp.run(transport='stdio')

if __name__ == "__main__":
    main()