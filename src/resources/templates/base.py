from typing import Any, Callable, Dict, Optional
from pydantic import BaseModel, Field, field_validator, ConfigDict
import re
from dataclasses import dataclass
from enum import Enum

class ResourceError(Exception):
    """Base class for resource-related errors."""
    pass

class URIValidationError(ResourceError):
    """Raised when URI validation fails."""
    pass

class ParameterExtractionError(ResourceError):
    """Raised when parameter extraction fails."""
    pass

class ResourceState(Enum):
    """Possible states of a resource template."""
    CREATED = "created"
    ACTIVE = "active"
    INVALID = "invalid"
    CLEANUP = "cleanup"

@dataclass
class URIComponents:
    """Parsed components of a URI template."""
    protocol: str
    path: str
    parameters: Dict[str, str]

class ResourceTemplate(BaseModel):
    """Base class for resource templates with URI handling.
    
    Attributes:
        uri_template: The URI template string
        state: Current state of the resource template
        parameter_types: Type definitions for parameters
    """
    model_config = ConfigDict(arbitrary_types_allowed=True)

    uri_template: str = Field(..., description="URI template string")
    state: ResourceState = Field(default=ResourceState.CREATED)
    parameter_types: Dict[str, type] = Field(default_factory=dict)

    @field_validator('uri_template')
    @classmethod
    def validate_uri_template(cls, v: str) -> str:
        """Validate URI template format."""
        if not v.startswith('docs://'):
            raise URIValidationError("URI must start with docs:// protocol")
        if len(v) <= 7:  # len('docs://')
            raise URIValidationError("URI must have a non-empty path")
        return v

    def parse_uri(self, uri: str) -> URIComponents:
        """Parse a URI into its components."""
        if not uri.startswith('docs://'):
            raise URIValidationError("Invalid protocol")
        
        path = uri[7:]  # Remove 'docs://'
        template_path = self.uri_template[7:]  # Remove 'docs://' from template
        
        # Split paths into segments, filtering out empty segments
        template_segments = [s for s in template_path.split('/') if s]
        uri_segments = [s for s in path.split('/') if s]
        
        if len(template_segments) != len(uri_segments):
            raise URIValidationError(
                f"URI segments do not match template. Expected {len(template_segments)} segments, got {len(uri_segments)}"
            )
        
        parameters: Dict[str, str] = {}
        param_pattern = r'\{([^}]+)\}'
        
        # Match segments and extract parameters
        for template_seg, uri_seg in zip(template_segments, uri_segments):
            match = re.match(param_pattern, template_seg)
            if match:
                param_name = match.group(1)
                if not param_name.isalnum():
                    raise URIValidationError(f"Invalid parameter name: {param_name}")
                parameters[param_name] = uri_seg
                
        return URIComponents(
            protocol="docs",
            path=path,
            parameters=parameters
        )

    def extract_parameters(self, uri: str) -> Dict[str, Any]:
        """Extract and validate parameters from a URI."""
        components = self.parse_uri(uri)
        parameters = components.parameters
        
        # Validate all required parameters are present
        template_params = set(self.parameter_types.keys())
        uri_params = set(parameters.keys())
        
        if template_params != uri_params:
            missing = template_params - uri_params
            extra = uri_params - template_params
            error_msg = []
            if missing:
                error_msg.append(f"Missing parameters: {missing}")
            if extra:
                error_msg.append(f"Extra parameters: {extra}")
            raise ParameterExtractionError(", ".join(error_msg))
            
        return parameters

    def validate_parameters(self, parameters: Dict[str, Any]) -> None:
        """Validate parameter types against defined parameter_types."""
        for name, value in parameters.items():
            expected_type = self.parameter_types.get(name)
            if expected_type and not isinstance(value, expected_type):
                raise ParameterExtractionError(
                    f"Parameter '{name}' must be of type {expected_type.__name__}"
                )