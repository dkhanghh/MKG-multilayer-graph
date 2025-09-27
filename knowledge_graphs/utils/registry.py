"""
Component registry system for KAG-LangGraph.

This module provides a simplified component registration system
that allows dynamic component discovery and instantiation.
"""

from typing import Dict, Type, Any, List, Optional, Callable
import inspect
import logging
from functools import wraps

from ..components.base import BaseComponent, ComponentConfig

logger = logging.getLogger(__name__)


class ComponentRegistry:
    """
    Registry for pipeline components.
    
    Provides registration and lookup functionality for all component types.
    Components can be registered by type and retrieved by name.
    """
    
    def __init__(self):
        """Initialize the component registry."""
        self._components: Dict[str, Dict[str, Type[BaseComponent]]] = {
            "scanner": {},
            "reader": {},
            "splitter": {},
            "extractor": {},
            "vectorizer": {},
            "writer": {},
        }
        self._component_metadata: Dict[str, Dict[str, Dict[str, Any]]] = {
            "scanner": {},
            "reader": {},
            "splitter": {},
            "extractor": {},
            "vectorizer": {},
            "writer": {},
        }
    
    def register(
        self,
        component_type: str,
        name: str,
        component_class: Type[BaseComponent],
        description: Optional[str] = None,
        config_schema: Optional[Dict[str, Any]] = None,
        **metadata
    ) -> Type[BaseComponent]:
        """
        Register a component class.
        
        Args:
            component_type: Type of component (scanner, reader, etc.)
            name: Name to register the component under
            component_class: Component class to register
            description: Optional description of the component
            config_schema: Optional JSON schema for component configuration
            **metadata: Additional metadata about the component
            
        Returns:
            The registered component class (for use as decorator)
        """
        if component_type not in self._components:
            raise ValueError(f"Unknown component type: {component_type}")
        
        if not issubclass(component_class, BaseComponent):
            raise TypeError(f"Component class must inherit from BaseComponent")
        
        # Register the component
        self._components[component_type][name] = component_class
        
        # Store metadata
        metadata_entry = {
            "name": name,
            "class": component_class,
            "description": description or component_class.__doc__,
            "config_schema": config_schema,
            "module": component_class.__module__,
            "qualname": component_class.__qualname__,
            **metadata
        }
        self._component_metadata[component_type][name] = metadata_entry
        
        logger.info(f"Registered {component_type} component: {name} -> {component_class.__name__}")
        return component_class
    
    def get(self, component_type: str, name: str) -> Optional[Type[BaseComponent]]:
        """
        Get a registered component class.
        
        Args:
            component_type: Type of component
            name: Name of the component
            
        Returns:
            Component class if found, None otherwise
        """
        return self._components.get(component_type, {}).get(name)
    
    def create(
        self,
        component_type: str,
        name: str,
        config: Optional[Dict[str, Any]] = None
    ) -> BaseComponent:
        """
        Create an instance of a registered component.
        
        Args:
            component_type: Type of component
            name: Name of the component
            config: Configuration for the component
            
        Returns:
            Component instance
            
        Raises:
            ValueError: If component type or name is not found
        """
        component_class = self.get(component_type, name)
        if component_class is None:
            available = list(self._components.get(component_type, {}).keys())
            raise ValueError(
                f"Component '{name}' not found for type '{component_type}'. "
                f"Available: {available}"
            )
        
        # Create component configuration
        component_config = ComponentConfig(
            type=name,
            name=name,
            config=config or {}
        )
        
        try:
            # Create component instance
            return component_class(component_config)
        except Exception as e:
            logger.error(f"Failed to create component {component_type}.{name}: {e}")
            raise
    
    def list_components(self, component_type: Optional[str] = None) -> Dict[str, List[str]]:
        """
        List all registered components.
        
        Args:
            component_type: Optional type filter
            
        Returns:
            Dictionary mapping component types to lists of component names
        """
        if component_type:
            if component_type not in self._components:
                return {}
            return {component_type: list(self._components[component_type].keys())}
        
        return {
            comp_type: list(components.keys())
            for comp_type, components in self._components.items()
        }
    
    def get_component_info(self, component_type: str, name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed information about a component.
        
        Args:
            component_type: Type of component
            name: Name of the component
            
        Returns:
            Component metadata if found, None otherwise
        """
        return self._component_metadata.get(component_type, {}).get(name)
    
    def get_config_schema(self, component_type: str, name: str) -> Optional[Dict[str, Any]]:
        """
        Get configuration schema for a component.
        
        Args:
            component_type: Type of component
            name: Name of the component
            
        Returns:
            Configuration schema if available, None otherwise
        """
        info = self.get_component_info(component_type, name)
        return info.get("config_schema") if info else None
    
    def validate_config(
        self,
        component_type: str,
        name: str,
        config: Dict[str, Any]
    ) -> List[str]:
        """
        Validate configuration for a component.
        
        Args:
            component_type: Type of component
            name: Name of the component
            config: Configuration to validate
            
        Returns:
            List of validation errors (empty if valid)
        """
        errors = []
        
        # Check if component exists
        if not self.get(component_type, name):
            errors.append(f"Component '{name}' not found for type '{component_type}'")
            return errors
        
        # Get config schema if available
        schema = self.get_config_schema(component_type, name)
        if schema:
            # Basic schema validation (could be extended with jsonschema)
            required = schema.get("required", [])
            properties = schema.get("properties", {})
            
            # Check required fields
            for field in required:
                if field not in config:
                    errors.append(f"Required field '{field}' missing from config")
            
            # Check field types
            for field, value in config.items():
                if field in properties:
                    expected_type = properties[field].get("type")
                    if expected_type and not self._check_type(value, expected_type):
                        errors.append(f"Field '{field}' has wrong type, expected {expected_type}")
        
        return errors
    
    def _check_type(self, value: Any, expected_type: str) -> bool:
        """Check if value matches expected type."""
        type_map = {
            "string": str,
            "integer": int,
            "number": (int, float),
            "boolean": bool,
            "array": list,
            "object": dict,
        }
        
        expected_python_type = type_map.get(expected_type)
        if expected_python_type:
            return isinstance(value, expected_python_type)
        
        return True  # Unknown type, assume valid


# Global registry instance
_global_registry = ComponentRegistry()


def register_component(
    component_type: str,
    name: str,
    description: Optional[str] = None,
    config_schema: Optional[Dict[str, Any]] = None,
    **metadata
) -> Callable[[Type[BaseComponent]], Type[BaseComponent]]:
    """
    Decorator for registering components.
    
    Args:
        component_type: Type of component (scanner, reader, etc.)
        name: Name to register the component under
        description: Optional description of the component
        config_schema: Optional JSON schema for component configuration
        **metadata: Additional metadata about the component
        
    Returns:
        Decorator function
        
    Example:
        @register_component("reader", "pdf_reader", description="PDF document reader")
        class PDFReader(Reader):
            pass
    """
    def decorator(component_class: Type[BaseComponent]) -> Type[BaseComponent]:
        return _global_registry.register(
            component_type=component_type,
            name=name,
            component_class=component_class,
            description=description,
            config_schema=config_schema,
            **metadata
        )
    
    return decorator


def get_component_class(component_type: str, name: str) -> Optional[Type[BaseComponent]]:
    """Get a registered component class from the global registry."""
    return _global_registry.get(component_type, name)


def create_component(
    component_type: str,
    name: str,
    config: Optional[Dict[str, Any]] = None
) -> BaseComponent:
    """Create a component instance from the global registry."""
    return _global_registry.create(component_type, name, config)


def list_components(component_type: Optional[str] = None) -> Dict[str, List[str]]:
    """List all registered components in the global registry."""
    return _global_registry.list_components(component_type)


def get_component_info(component_type: str, name: str) -> Optional[Dict[str, Any]]:
    """Get component information from the global registry."""
    return _global_registry.get_component_info(component_type, name)


# Registry access
def get_registry() -> ComponentRegistry:
    """Get the global component registry."""
    return _global_registry