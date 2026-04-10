import re
from typing import Optional

from jinja2 import BaseLoader, Environment, TemplateSyntaxError, UndefinedError

# {{ var }} pattern, must start with a non-digit and contain only letters, digits, and underscores
_SIMPLE_VAR_RE = re.compile(r'\{\{\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*\}\}')

_env = Environment(
    loader=BaseLoader(),
    keep_trailing_newline=True,
    autoescape=False,
)

def extract_variables(text: str) -> set[str]:
    """Return an ordered, list of simple {{ variable }} names.

    Only bare identifiers are returned - dot-access expressions like 
    {{ user.name }} returned as {{ user }}.

    Examples:
        >>> extract_variables("Hello {{ name }}!")
        ["name"]
        >>> extract_variables("No variables here.")
        []
    """
    seen: set[str] = set()
    variables: list[str] = []

    for match in _SIMPLE_VAR_RE.finditer(text):
        var = match.group(1)
        if var not in seen:
            seen.add(var)
            variables.append(var)
    return variables


def render_prompt(text: str, context: dict[str, str]) -> tuple[str, Optional[str]]:
    """Render *text* as a Jinja2 template with *context*.

    Returns:
        (rendered, None)        on success.
        ("", error_message)     on failure.
    
    Examples:
        >>> render_prompt("Hello {{ name }}!", {"name": "Alice"})
        ("Hello Alice!", None)
        >>> render_prompt("Hello {{ name }}!", {})
        ("", "Undefined variable: 'name'")
    """
    try:
        template = _env.from_string(text)
        rendered = template.render(context)
        return rendered, None
    
    except TemplateSyntaxError as e:
        return "", f"Syntax error in template: {e.message}"
    except UndefinedError as e:
        return "", f"Undefined variable: {e.message}"
    except Exception as e:
        return "", f"Error rendering template: {str(e)}"