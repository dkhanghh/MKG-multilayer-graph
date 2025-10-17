"""
Template loading utilities for KAG-LangGraph.

This module provides utilities for loading and rendering Jinja2 templates
from markdown files, particularly for LLM prompts.
"""

import json
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Union, List

try:
    from jinja2 import Environment, FileSystemLoader, Template
    HAS_JINJA2 = True
except ImportError:
    HAS_JINJA2 = False
    # Create dummy Template class for type hints when Jinja2 is not available
    class Template:
        pass

logger = logging.getLogger(__name__)


class TemplateLoader:
    """
    Template loader for Jinja2 templates from markdown files.
    
    Supports loading prompt templates with variable substitution
    for LLM interactions.
    """
    
    def __init__(self, template_dir: Union[str, Path] = None):
        """
        Initialize template loader.
        
        Args:
            template_dir: Directory containing template files
        """
        if not HAS_JINJA2:
            raise ImportError("jinja2 package not installed. Install with: pip install jinja2")
        
        if template_dir is None:
            # Default to prompts directory relative to this file
            template_dir = Path(__file__).parent.parent / "prompts"
        
        self.template_dir = Path(template_dir)
        
        # Create Jinja2 environment
        self.env = Environment(
            loader=FileSystemLoader(str(self.template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
            keep_trailing_newline=True
        )
        
        logger.info(f"Initialized template loader with directory: {self.template_dir}")
    
    def load_template(self, template_name: str) -> Template:
        """
        Load a Jinja2 template from file.
        
        Args:
            template_name: Name of template file (e.g., "ner.md")
            
        Returns:
            Jinja2 Template object
            
        Raises:
            FileNotFoundError: If template file doesn't exist
            TemplateError: If template has syntax errors
        """
        try:
            template = self.env.get_template(template_name)
            logger.debug(f"Loaded template: {template_name}")
            return template
        except Exception as e:
            logger.error(f"Failed to load template {template_name}: {e}")
            raise
    
    def render_template(
        self, 
        template_name: str, 
        variables: Dict[str, Any] = None
    ) -> str:
        """
        Load and render a template with variables.
        
        Args:
            template_name: Name of template file
            variables: Dictionary of variables to substitute
            
        Returns:
            Rendered template string
        """
        if variables is None:
            variables = {}
        
        template = self.load_template(template_name)
        
        try:
            rendered = template.render(**variables)
            logger.debug(f"Rendered template {template_name} with {len(variables)} variables")
            return rendered
        except Exception as e:
            logger.error(f"Failed to render template {template_name}: {e}")
            raise
    
    def render_prompt_template(
        self,
        template_name: str,
        schema: Dict[str, Any] = None,
        input_text: str = "",
        **kwargs
    ) -> str:
        """
        Render a prompt template with common LLM variables.
        
        Args:
            template_name: Name of template file
            schema: Schema object for extraction
            input_text: Input text to process
            **kwargs: Additional template variables
            
        Returns:
            Rendered prompt string
        """
        variables = {
            "schema": schema if schema else {},
            "input_text": input_text,
            **kwargs
        }
        
        return self.render_template(template_name, variables)
    
    def list_templates(self) -> List[str]:
        """
        List available template files.
        
        Returns:
            List of template file names
        """
        if not self.template_dir.exists():
            return []
        
        templates = []
        for file_path in self.template_dir.glob("*.md"):
            templates.append(file_path.name)
        
        return sorted(templates)
    
    def template_exists(self, template_name: str) -> bool:
        """
        Check if a template file exists.
        
        Args:
            template_name: Name of template file
            
        Returns:
            True if template exists, False otherwise
        """
        template_path = self.template_dir / template_name
        return template_path.exists()


# Global template loader instance
_template_loader: Optional[TemplateLoader] = None


def get_template_loader(template_dir: Union[str, Path] = None) -> TemplateLoader:
    """
    Get global template loader instance.
    
    Args:
        template_dir: Directory containing templates (only used on first call)
        
    Returns:
        TemplateLoader instance
    """
    global _template_loader
    
    if _template_loader is None:
        _template_loader = TemplateLoader(template_dir)
    
    return _template_loader


def load_prompt_template(
    template_name: str,
    schema: Dict[str, Any] = None,
    input_text: str = "",
    **kwargs
) -> str:
    """
    Convenience function to load and render a prompt template.
    
    Args:
        template_name: Name of template file
        schema: Schema object for extraction
        input_text: Input text to process
        **kwargs: Additional template variables
        
    Returns:
        Rendered prompt string
    """
    loader = get_template_loader()
    return loader.render_prompt_template(
        template_name=template_name,
        schema=schema,
        input_text=input_text,
        **kwargs
    )
