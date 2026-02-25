"""
Pydantic v2 models for the domain schema system.

Supports parsing from the custom DSL format (.schema files) and YAML format,
with validation, conversion to extraction schema dicts, and convenient properties.
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, model_validator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Atomic schema building blocks
# ---------------------------------------------------------------------------


class PropertyDef(BaseModel):
    """A single property on an entity."""

    name: str
    type: str
    index: Optional[str] = None
    constraint: Optional[str] = None


class EdgePropertyDef(BaseModel):
    """A single property on a relationship edge."""

    name: str
    type: str


class RelationDef(BaseModel):
    """A relationship definition inside an entity."""

    name: str
    target_entity: str
    edge_properties: List[EdgePropertyDef] = []
    constraint: Optional[str] = None


class EntityDef(BaseModel):
    """An entity (EntityType or ConceptType) definition."""

    name: str
    entity_type: Literal["EntityType", "ConceptType"]
    properties: List[PropertyDef] = []
    relations: List[RelationDef] = []
    hypernym_predicate: Optional[str] = None


# ---------------------------------------------------------------------------
# Top-level schema
# ---------------------------------------------------------------------------


class DomainSchema(BaseModel):
    """
    Complete domain schema containing all entity definitions.

    Can be loaded from the custom ``.schema`` DSL or from YAML.
    """

    namespace: str
    entities: Dict[str, EntityDef]

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    @model_validator(mode="after")
    def _validate_relation_targets(self) -> "DomainSchema":
        """Warn about relation target_entity values that are not defined entities.

        This is a warning rather than a hard error because some schemas
        intentionally reference external or primitive types (e.g. ``Text``)
        as relation targets.
        """
        entity_names = set(self.entities.keys())
        for entity_name, entity_def in self.entities.items():
            for rel in entity_def.relations:
                if rel.target_entity not in entity_names:
                    logger.warning(
                        "Entity '%s', relation '%s': target_entity '%s' "
                        "is not defined in the schema",
                        entity_name,
                        rel.name,
                        rel.target_entity,
                    )
        return self

    # ------------------------------------------------------------------
    # Convenience properties
    # ------------------------------------------------------------------

    @property
    def entity_type_names(self) -> List[str]:
        """Return a sorted list of all entity names (both EntityType and ConceptType)."""
        return sorted(self.entities.keys())

    @property
    def relation_type_names(self) -> List[str]:
        """Return a sorted, deduplicated list of all relation names across all entities."""
        names: set[str] = set()
        for entity_def in self.entities.values():
            for rel in entity_def.relations:
                names.add(rel.name)
        return sorted(names)

    @property
    def concept_types(self) -> List[str]:
        """Return entity names that are ConceptType."""
        return sorted(
            name
            for name, edef in self.entities.items()
            if edef.entity_type == "ConceptType"
        )

    @property
    def entity_types_only(self) -> List[str]:
        """Return entity names that are EntityType (excluding ConceptType)."""
        return sorted(
            name
            for name, edef in self.entities.items()
            if edef.entity_type == "EntityType"
        )

    # ------------------------------------------------------------------
    # Conversion to extraction schema dict (backward compatible)
    # ------------------------------------------------------------------

    def to_extraction_schema(self) -> Dict[str, Any]:
        """
        Produce the dict format consumed by extractor prompt templates.

        The output matches the structure previously created by
        ``_parse_domain_schema_content`` in the extractor module::

            {
                "namespace": "Finance",
                "entities": {
                    "Company": {
                        "type": "EntityType",
                        "properties": {"desc": {"type": "Text", "index": "Text"}, ...},
                        "relations": {
                            "OWNS": {
                                "target_entity": "Company",
                                "constraint": None,
                                "properties": {},
                                "rule": None
                            },
                            ...
                        }
                    },
                    ...
                },
                "entity_types": ["Chunk", "Industry", ...],
                "relation_types": ["OWNS", "COMPETES_WITH", ...]
            }
        """
        entities_dict: Dict[str, Any] = {}
        all_relation_types: List[str] = []

        for entity_name, entity_def in self.entities.items():
            # Build properties dict
            props: Dict[str, Any] = {}
            for prop in entity_def.properties:
                entry: Dict[str, Any] = {"type": prop.type}
                if prop.index is not None:
                    entry["index"] = prop.index
                else:
                    entry["index"] = None
                if prop.constraint is not None:
                    entry["constraint"] = prop.constraint
                props[prop.name] = entry

            # Build relations dict
            rels: Dict[str, Any] = {}
            for rel in entity_def.relations:
                edge_props: Dict[str, Any] = {}
                for ep in rel.edge_properties:
                    edge_props[ep.name] = {"type": ep.type}

                rels[rel.name] = {
                    "target_entity": rel.target_entity,
                    "constraint": rel.constraint,
                    "properties": edge_props,
                    "rule": None,
                }

                if rel.name not in all_relation_types:
                    all_relation_types.append(rel.name)

            entities_dict[entity_name] = {
                "type": entity_def.entity_type,
                "properties": props,
                "relations": rels,
            }

        return {
            "namespace": self.namespace,
            "entities": entities_dict,
            "entity_types": list(self.entities.keys()),
            "relation_types": all_relation_types,
        }

    # ------------------------------------------------------------------
    # Factory: from DSL (.schema) content
    # ------------------------------------------------------------------

    @classmethod
    def from_dsl(cls, content: str) -> "DomainSchema":
        """Parse the indentation-based ``.schema`` DSL format.

        Raises ``ValueError`` with line-number information on parse errors.
        """
        namespace: Optional[str] = None
        entities: Dict[str, EntityDef] = {}

        # Parsing state
        current_entity_name: Optional[str] = None
        current_section: Optional[str] = None  # "properties" | "relations"
        current_relation_name: Optional[str] = None
        in_edge_properties: bool = False

        # Accumulators
        current_properties: List[PropertyDef] = []
        current_relations: List[RelationDef] = []
        current_entity_type: Optional[str] = None
        current_hypernym: Optional[str] = None

        # For the relation currently being built
        current_rel_edge_props: List[EdgePropertyDef] = []
        current_rel_target: Optional[str] = None
        current_rel_constraint: Optional[str] = None

        # For the property currently being built (to attach index/constraint)
        last_property: Optional[PropertyDef] = None

        def _flush_relation() -> None:
            nonlocal current_relation_name, current_rel_edge_props
            nonlocal current_rel_target, current_rel_constraint, in_edge_properties
            if current_relation_name is not None and current_rel_target is not None:
                current_relations.append(
                    RelationDef(
                        name=current_relation_name,
                        target_entity=current_rel_target,
                        edge_properties=list(current_rel_edge_props),
                        constraint=current_rel_constraint,
                    )
                )
            current_relation_name = None
            current_rel_target = None
            current_rel_edge_props = []
            current_rel_constraint = None
            in_edge_properties = False

        def _flush_entity() -> None:
            nonlocal current_entity_name, current_section, last_property
            _flush_relation()
            if current_entity_name is not None and current_entity_type is not None:
                entities[current_entity_name] = EntityDef(
                    name=current_entity_name,
                    entity_type=current_entity_type,  # type: ignore[arg-type]
                    properties=list(current_properties),
                    relations=list(current_relations),
                    hypernym_predicate=current_hypernym,
                )
            current_entity_name = None
            current_section = None
            last_property = None

        lines = content.split("\n")
        for line_no, raw_line in enumerate(lines, start=1):
            # Determine indentation level (in units of 4 spaces)
            stripped = raw_line.rstrip()
            if not stripped:
                continue

            # Skip comments
            lstripped = stripped.lstrip()
            if lstripped.startswith("#") or lstripped.startswith("==="):
                continue

            # Count leading whitespace (normalise tabs to 4 spaces)
            expanded = raw_line.expandtabs(4)
            content_start = len(expanded) - len(expanded.lstrip())
            indent_level = content_start // 4  # 0, 1, 2, 3 ...
            line = lstripped

            try:
                # --- Level 0: namespace or entity declaration ---
                if indent_level == 0:
                    if line.startswith("namespace "):
                        namespace = line[len("namespace "):].strip()
                        continue

                    # Entity declaration: "Company: EntityType"
                    match = re.match(
                        r"^(\w+)\s*:\s*(EntityType|ConceptType)\s*$", line
                    )
                    if match:
                        _flush_entity()
                        current_entity_name = match.group(1)
                        current_entity_type = match.group(2)
                        current_properties = []
                        current_relations = []
                        current_hypernym = None
                        current_section = None
                        continue

                # --- Level 1: sections or hypernymPredicate ---
                if indent_level == 1 and current_entity_name:
                    if line == "properties:":
                        _flush_relation()
                        current_section = "properties"
                        last_property = None
                        continue
                    if line == "relations:":
                        _flush_relation()
                        current_section = "relations"
                        continue
                    if line.startswith("hypernymPredicate:"):
                        current_hypernym = line.split(":", 1)[1].strip()
                        continue

                # --- Level 2: property lines or relation lines ---
                if indent_level == 2 and current_entity_name:
                    if current_section == "properties":
                        if ":" in line:
                            parts = line.split(":", 1)
                            prop_name = parts[0].strip()
                            prop_type = parts[1].strip()
                            prop = PropertyDef(name=prop_name, type=prop_type)
                            current_properties.append(prop)
                            last_property = prop
                        continue

                    if current_section == "relations":
                        # A new relation line: "OWNS: Company"
                        if ":" in line and not line.startswith("edgeProperties"):
                            _flush_relation()
                            parts = line.split(":", 1)
                            current_relation_name = parts[0].strip()
                            # Handle inline comments
                            target_raw = parts[1].strip()
                            current_rel_target = target_raw.split("#")[0].strip()
                            in_edge_properties = False
                        continue

                # --- Level 3: sub-properties (index, constraint, edgeProperties header) ---
                if indent_level == 3 and current_entity_name:
                    if current_section == "properties" and last_property is not None:
                        if line.startswith("index:"):
                            last_property.index = line.split(":", 1)[1].strip()
                        elif line.startswith("constraint:"):
                            last_property.constraint = line.split(":", 1)[1].strip()
                        continue

                    if current_section == "relations":
                        if line.startswith("edgeProperties:"):
                            in_edge_properties = True
                            continue
                        if line.startswith("constraint:"):
                            current_rel_constraint = line.split(":", 1)[1].strip()
                            continue

                # --- Level 4: edge property items ---
                if indent_level >= 4 and current_entity_name:
                    if current_section == "relations" and in_edge_properties:
                        if ":" in line:
                            parts = line.split(":", 1)
                            ep_name = parts[0].strip()
                            ep_type = parts[1].strip().split("#")[0].strip()
                            current_rel_edge_props.append(
                                EdgePropertyDef(name=ep_name, type=ep_type)
                            )
                        continue

            except Exception as exc:
                raise ValueError(
                    f"Error parsing schema at line {line_no}: {raw_line!r} — {exc}"
                ) from exc

        # Flush last entity
        _flush_entity()

        if namespace is None:
            raise ValueError("Schema is missing a 'namespace' declaration")

        return cls(namespace=namespace, entities=entities)

    # ------------------------------------------------------------------
    # Factory: from YAML content
    # ------------------------------------------------------------------

    @classmethod
    def from_yaml(cls, content: str) -> "DomainSchema":
        """Parse a YAML schema representation."""
        data = yaml.safe_load(content)
        if not isinstance(data, dict):
            raise ValueError("YAML schema must be a mapping at the top level")

        namespace = data.get("namespace")
        if not namespace:
            raise ValueError("YAML schema is missing 'namespace'")

        entities: Dict[str, EntityDef] = {}
        for entity_name, entity_data in data.get("entities", {}).items():
            properties = [
                PropertyDef(**p) for p in entity_data.get("properties", [])
            ]
            relations = []
            for rel_data in entity_data.get("relations", []):
                edge_props = [
                    EdgePropertyDef(**ep)
                    for ep in rel_data.get("edge_properties", [])
                ]
                relations.append(
                    RelationDef(
                        name=rel_data["name"],
                        target_entity=rel_data["target_entity"],
                        edge_properties=edge_props,
                        constraint=rel_data.get("constraint"),
                    )
                )
            entities[entity_name] = EntityDef(
                name=entity_name,
                entity_type=entity_data["entity_type"],
                properties=properties,
                relations=relations,
                hypernym_predicate=entity_data.get("hypernym_predicate"),
            )

        return cls(namespace=namespace, entities=entities)

    # ------------------------------------------------------------------
    # Factory: auto-detect from file extension
    # ------------------------------------------------------------------

    @classmethod
    def from_file(cls, path: str) -> "DomainSchema":
        """Load a schema from a file, auto-detecting format from extension.

        Supported extensions: ``.schema`` (DSL), ``.yaml`` / ``.yml`` (YAML).
        """
        p = Path(path)
        if not p.exists():
            raise FileNotFoundError(f"Schema file not found: {path}")

        content = p.read_text(encoding="utf-8")

        if p.suffix == ".schema":
            return cls.from_dsl(content)
        elif p.suffix in (".yaml", ".yml"):
            return cls.from_yaml(content)
        else:
            raise ValueError(
                f"Unsupported schema file extension '{p.suffix}'. "
                "Use .schema, .yaml, or .yml"
            )
