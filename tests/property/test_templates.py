from hypothesis import given, strategies as st, assume
import pytest
from typing import Optional, Dict, Any
from src.resources.templates.base import (
    ResourceTemplate,
    URIValidationError,
    ParameterExtractionError,
    ResourceState
)

@given(st.text(min_size=1).map(lambda s: f'docs://{s}'))
def test_template_creation(uri: str):
    """Test basic URI template creation and validation.
    
    Properties tested:
    - URI must start with docs:// protocol
    - Path component must be non-empty
    - Template parsing should extract parameters
    """
    template = ResourceTemplate(uri_template=uri)
    assert template.uri_template == uri
    assert template.state == ResourceState.CREATED
    
    components = template.parse_uri(uri)
    assert components.protocol == "docs"
    assert components.path == uri[7:]  # Remove 'docs://'

@given(
    st.text(min_size=1).filter(lambda s: '/' not in s),
    st.dictionaries(
        # Generate valid parameter names (alphanumeric only)
        st.text(min_size=1, alphabet=st.characters(whitelist_categories=('Lu', 'Ll', 'Nd'))),
        # Generate valid parameter values (no slashes)
        st.text(min_size=1).filter(lambda s: '/' not in s),
        max_size=5
    )
)
def test_template_parameter_extraction(base_path: str, params: Dict[str, str]):
    """Test parameter extraction from URI templates.
    
    Properties tested:
    - All parameters in URI should be extracted
    - Parameter values should be properly typed
    - Invalid parameters should raise appropriate errors
    """
    # Create template URI with parameters
    param_parts = [f"{{{k}}}" for k in params.keys()]
    template_uri = f"docs://{base_path}"
    if param_parts:
        template_uri += "/" + "/".join(param_parts)
    
    # Create actual URI with parameter values
    actual_uri = f"docs://{base_path}"
    if params:
        actual_uri += "/" + "/".join(str(v) for v in params.values())
    
    template = ResourceTemplate(
        uri_template=template_uri,
        parameter_types={name: str for name in params}
    )
    
    extracted = template.extract_parameters(actual_uri)
    assert set(extracted.keys()) == set(params.keys())
    for k, v in params.items():
        assert extracted[k] == str(v)
    
    template.validate_parameters(params)

@given(st.text(min_size=1))
def test_invalid_uri_handling(invalid_uri: str):
    """Test handling of invalid URIs.
    
    Properties tested:
    - URIs without docs:// protocol should be rejected
    - Malformed URIs should raise appropriate errors
    """
    assume(not invalid_uri.startswith('docs://'))
    
    with pytest.raises(URIValidationError):
        ResourceTemplate(uri_template=invalid_uri)

def test_parameter_type_validation():
    """Test parameter type validation."""
    template = ResourceTemplate(
        uri_template='docs://test/{param}',
        parameter_types={'param': int}
    )
    
    with pytest.raises(ParameterExtractionError):
        template.validate_parameters({'param': 'not_an_int'})