"""
Configuration system for KAG-LangGraph pipeline.

This module provides configuration loading, validation, and management
for pipeline components and execution parameters.
"""

import os
import logging
from typing import Dict, Any, List, Optional, Union
from pathlib import Path
from pydantic import BaseModel, Field, field_validator, ConfigDict
import yaml

logger = logging.getLogger(__name__)


class ComponentConfig(BaseModel):
    """Configuration for a single pipeline component."""
    
    type: str = Field(..., description="Component type/class name")
    enabled: bool = Field(True, description="Whether component is enabled")
    config: Dict[str, Any] = Field(default_factory=dict, description="Component-specific configuration")
    
    model_config = ConfigDict(extra="allow")


class PipelineConfig(BaseModel):
    """Configuration for the entire pipeline."""
    
    # Global pipeline settings
    name: Optional[str] = Field(None, description="Pipeline name")
    description: Optional[str] = Field(None, description="Pipeline description")
    version: str = Field("1.0", description="Configuration version")
    
    # Execution settings
    max_workers: int = Field(4, description="Maximum number of worker threads")
    batch_size: int = Field(100, description="Default batch size for processing")
    timeout: Optional[int] = Field(None, description="Pipeline timeout in seconds")
    
    # Component configurations
    components: Dict[str, ComponentConfig] = Field(..., description="Component configurations")
    
    # Global configuration that can be inherited by components
    global_config: Dict[str, Any] = Field(default_factory=dict, description="Global configuration values")
    
    @field_validator('components')
    @classmethod
    def validate_components(cls, v):
        """Validate that required components are present."""
        required_components = ['scanner', 'reader', 'extractor', 'writer']

        for required in required_components:
            if required not in v:
                logger.warning(f"Required component '{required}' not found in configuration")

        return v
    
    @field_validator('max_workers')
    @classmethod
    def validate_max_workers(cls, v):
        """Validate max workers is positive."""
        if v <= 0:
            raise ValueError("max_workers must be greater than 0")
        return v
    
    def get_component_config(self, component_name: str) -> Optional[ComponentConfig]:
        """
        Get configuration for a specific component.
        
        Args:
            component_name: Name of the component
            
        Returns:
            Component configuration or None if not found
        """
        return self.components.get(component_name)
    
    def is_component_enabled(self, component_name: str) -> bool:
        """
        Check if a component is enabled.
        
        Args:
            component_name: Name of the component
            
        Returns:
            True if component is enabled
        """
        component_config = self.get_component_config(component_name)
        return component_config.enabled if component_config else False
    
    def get_enabled_components(self) -> List[str]:
        """
        Get list of enabled component names.
        
        Returns:
            List of enabled component names
        """
        return [
            name for name, config in self.components.items()
            if config.enabled
        ]


def load_config(config_path: Union[str, Path]) -> Dict[str, Any]:
    """
    Load configuration from YAML file.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Configuration dictionary
        
    Raises:
        FileNotFoundError: If configuration file doesn't exist
        yaml.YAMLError: If YAML parsing fails
    """
    config_path = Path(config_path)
    
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = yaml.safe_load(f)
        
        logger.info(f"Loaded configuration from {config_path}")
        return config_data
        
    except yaml.YAMLError as e:
        logger.error(f"Error parsing YAML configuration: {e}")
        raise
    except Exception as e:
        logger.error(f"Error loading configuration: {e}")
        raise


def validate_config(config_data: Dict[str, Any]) -> PipelineConfig:
    """
    Validate configuration data against schema.
    
    Args:
        config_data: Raw configuration data
        
    Returns:
        Validated PipelineConfig instance
        
    Raises:
        ValueError: If configuration is invalid
    """
    try:
        # Convert component configs to ComponentConfig objects
        if 'pipeline' in config_data and 'components' in config_data['pipeline']:
            components_data = config_data['pipeline']['components']
            component_configs = {}
            
            for name, comp_data in components_data.items():
                component_configs[name] = ComponentConfig(**comp_data)
            
            # Update config data
            config_data['pipeline']['components'] = component_configs
        
        # Create and validate PipelineConfig
        if 'pipeline' in config_data:
            pipeline_config = PipelineConfig(**config_data['pipeline'])
        else:
            # Assume the entire config is pipeline config
            pipeline_config = PipelineConfig(**config_data)
        
        logger.info("Configuration validation successful")
        return pipeline_config
        
    except Exception as e:
        logger.error(f"Configuration validation failed: {e}")
        raise ValueError(f"Invalid configuration: {e}")


def load_and_validate_config(config_path: Union[str, Path]) -> PipelineConfig:
    """
    Load and validate configuration in one step.
    
    Args:
        config_path: Path to configuration file
        
    Returns:
        Validated PipelineConfig instance
    """
    config_data = load_config(config_path)
    return validate_config(config_data)


def save_config(config: Union[PipelineConfig, Dict[str, Any]], output_path: Union[str, Path]) -> None:
    """
    Save configuration to YAML file.
    
    Args:
        config: Configuration to save
        output_path: Path to output file
    """
    output_path = Path(output_path)
    
    # Convert to dictionary if needed
    if isinstance(config, PipelineConfig):
        config_dict = config.dict()
    else:
        config_dict = config
    
    # Ensure output directory exists
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        yaml.safe_dump(config_dict, f, indent=2, sort_keys=False)
    
    logger.info(f"Saved configuration to {output_path}")


def create_default_config() -> Dict[str, Any]:
    """
    Create a default configuration with common settings.
    
    Returns:
        Default configuration dictionary
    """
    return {
        "pipeline": {
            "name": "KAG-LangGraph Pipeline",
            "description": "Default knowledge graph construction pipeline",
            "version": "1.0",
            "max_workers": 4,
            "batch_size": 100,
            "components": {
                "scanner": {
                    "type": "file_scanner",
                    "enabled": True,
                    "config": {
                        "verify_exists": True
                    }
                },
                "reader": {
                    "type": "mixed_reader",
                    "enabled": True,
                    "config": {
                        "supported_types": ["pdf", "txt", "docx", "md"],
                        "default_encoding": "utf-8"
                    }
                },
                "splitter": {
                    "type": "length_splitter",
                    "enabled": True,
                    "config": {
                        "chunk_size": 1000,
                        "chunk_overlap": 100,
                        "split_by": "character",
                        "separators": ["\n\n", "\n", ". ", " "]
                    }
                },
                "extractor": {
                    "type": "llm_extractor",
                    "enabled": True,
                    "config": {
                        "llm_provider": "openai",
                        "model": "gpt-3.5-turbo",
                        "temperature": 0.1,
                        "max_tokens": 2000,
                        "entity_types": ["Person", "Organization", "Location", "Concept"],
                        "relation_types": ["works_for", "located_in", "related_to", "part_of"],
                        "batch_size": 5
                    }
                },
                "vectorizer": {
                    "type": "embedding_vectorizer",
                    "enabled": True,
                    "config": {
                        "model_name": "all-MiniLM-L6-v2",
                        "batch_size": 32,
                        "normalize_embeddings": True,
                        "embed_nodes": True,
                        "embed_edges": False
                    }
                },
                "writer": {
                    "type": "json_writer",
                    "enabled": True,
                    "config": {
                        "output_path": "./output/knowledge_graph.json",
                        "pretty_print": True,
                        "include_metadata": True,
                        "separate_files": False
                    }
                }
            },
            "global_config": {
                "log_level": "INFO",
                "output_dir": "./output",
                "temp_dir": "./temp"
            }
        }
    }


def create_example_configs() -> Dict[str, Dict[str, Any]]:
    """
    Create example configurations for different use cases.
    
    Returns:
        Dictionary of example configurations
    """
    configs = {}
    
    # Basic configuration for simple document processing
    configs["basic"] = {
        "pipeline": {
            "name": "Basic Document Processing",
            "description": "Simple pipeline for extracting knowledge from documents",
            "components": {
                "scanner": {"type": "file_scanner", "enabled": True},
                "reader": {"type": "mixed_reader", "enabled": True},
                "splitter": {"type": "length_splitter", "enabled": True},
                "extractor": {"type": "llm_extractor", "enabled": True},
                "writer": {"type": "json_writer", "enabled": True}
            }
        }
    }
    
    # Advanced configuration with all features
    configs["advanced"] = create_default_config()
    
    # Configuration for semantic processing
    configs["semantic"] = {
        "pipeline": {
            "name": "Semantic Knowledge Extraction",
            "description": "Pipeline with semantic splitting and advanced vectorization",
            "components": {
                "scanner": {"type": "directory_scanner", "enabled": True},
                "reader": {"type": "mixed_reader", "enabled": True},
                "splitter": {
                    "type": "semantic_splitter",
                    "enabled": True,
                    "config": {
                        "model_name": "all-MiniLM-L6-v2",
                        "similarity_threshold": 0.8,
                        "min_chunk_length": 200,
                        "max_chunk_length": 2000
                    }
                },
                "extractor": {
                    "type": "llm_extractor",
                    "enabled": True,
                    "config": {
                        "llm_provider": "openai",
                        "model": "gpt-4",
                        "temperature": 0.1
                    }
                },
                "vectorizer": {
                    "type": "openai_vectorizer",
                    "enabled": True,
                    "config": {
                        "model": "text-embedding-ada-002"
                    }
                },
                "writer": {"type": "neo4j_writer", "enabled": True}
            }
        }
    }
    
    # Configuration for regex-based extraction
    configs["regex"] = {
        "pipeline": {
            "name": "Regex-based Entity Extraction",
            "description": "Pipeline using regex patterns for entity extraction",
            "components": {
                "scanner": {"type": "file_scanner", "enabled": True},
                "reader": {"type": "txt_reader", "enabled": True},
                "splitter": {"type": "length_splitter", "enabled": True},
                "extractor": {
                    "type": "regex_extractor",
                    "enabled": True,
                    "config": {
                        "patterns": {
                            "email": r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b',
                            "phone": r'\b(?:\+?1[-.\s]?)?\(?([0-9]{3})\)?[-.\s]?([0-9]{3})[-.\s]?([0-9]{4})\b',
                            "url": r'https?://(?:[-\w.])+(?:\:[0-9]+)?(?:/(?:[\w/_.])*(?:\?(?:[\w&=%.])*)?(?:\#(?:[\w.])*)?)?'
                        }
                    }
                },
                "vectorizer": {"type": "no_op_vectorizer", "enabled": True},
                "writer": {"type": "csv_writer", "enabled": True}
            }
        }
    }
    
    return configs


def resolve_environment_variables(config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Resolve environment variable references in configuration.
    
    Args:
        config: Configuration dictionary
        
    Returns:
        Configuration with environment variables resolved
    """
    def resolve_value(value):
        if isinstance(value, str) and value.startswith("${") and value.endswith("}"):
            env_var = value[2:-1]
            default_value = None
            
            # Handle default values: ${VAR_NAME:default_value}
            if ":" in env_var:
                env_var, default_value = env_var.split(":", 1)
            
            return os.getenv(env_var, default_value)
        elif isinstance(value, dict):
            return {k: resolve_value(v) for k, v in value.items()}
        elif isinstance(value, list):
            return [resolve_value(item) for item in value]
        else:
            return value
    
    return resolve_value(config)


def merge_configs(base_config: Dict[str, Any], override_config: Dict[str, Any]) -> Dict[str, Any]:
    """
    Merge two configurations, with override taking precedence.
    
    Args:
        base_config: Base configuration
        override_config: Override configuration
        
    Returns:
        Merged configuration
    """
    def deep_merge(base, override):
        if isinstance(base, dict) and isinstance(override, dict):
            result = base.copy()
            for key, value in override.items():
                if key in result:
                    result[key] = deep_merge(result[key], value)
                else:
                    result[key] = value
            return result
        else:
            return override
    
    return deep_merge(base_config, override_config)