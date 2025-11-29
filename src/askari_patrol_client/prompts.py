from pathlib import Path


def load_whatsapp_system_prompt():
    prompt_file = Path(__file__).parent / "prompts" / "WhatsApp.md"
    with open(prompt_file, encoding="utf-8") as f:
        return f.read()


def load_cli_system_prompt():
    prompt_file = Path(__file__).parent / "prompts" / "cli.md"
    with open(prompt_file, encoding="utf-8") as f:
        return f.read()


CLI_SYSTEM_PROMPT = load_cli_system_prompt()
WHATSAPP_SYSTEM_PROMPT = load_whatsapp_system_prompt()
