import re
from typing import Any
from jinja2 import (
    Environment,
    StrictUndefined,
    TemplateSyntaxError,
    UndefinedError,
    meta,
)

class PromptRenderError(Exception):
    pass


class PromptRenderer:
    """
    Renders Jinja2 prompt templates with strict undefined-variable handling.
 
    Features:
    - StrictUndefined: any missing variable raises immediately — no silent blanks.
    - extract_variables: statically parses a template string for declared variables.
    - supports filters, conditionals, loops — full Jinja2 feature set.
    """
 
    def __init__(self):
        self._env = Environment(
            undefined=StrictUndefined,
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )


    def render(self, template_str: str, variables: dict[str, Any]) -> str:
        """
        Render a Jinja2 template string with the provided variables.
 
        Raises:
            PromptRenderError: on syntax errors or missing variables.
        """
        try:
            template = self._env.from_string(template_str)
            return template.render(**variables)
        except TemplateSyntaxError as e:
            raise PromptRenderError(
                f"Template syntax error at line {e.lineno}: {e.message}"
            ) from e
        except UndefinedError as e:
            raise PromptRenderError(
                f"Missing template variable: {e.message}"
            ) from e


    def extract_variables(self, template_str: str) -> list[str]:
        """
        Statically extract all referenced variable names from a template string.
        Used to populate `input_variables` on Prompt creation.
        """
        try:
            ast = self._env.parse(template_str)
            variables = meta.find_undeclared_variables(ast)
            return sorted(variables)
        except TemplateSyntaxError as e:
            raise PromptRenderError(
                f"Cannot parse template for variable extraction: {e.message}"
            ) from e
        

    def validate_template(self, template_str: str) -> None:
        """
        Validate template syntax without rendering.
 
        Raises:
            PromptRenderError: if the template has syntax errors.
        """
        try:
            self._env.parse(template_str)
        except TemplateSyntaxError as e:
            raise PromptRenderError(
                f"Invalid template syntax at line {e.lineno}: {e.message}"
            ) from e


renderer = PromptRenderer()