# Backend Configuration

Backend configurations are managed via YAML instead of environment variables for better maintainability and clarity.

## Configuration File

Customize `app/config/user/backends.yaml` for your deployment. This file contains your backend configurations.

The configuration file has the following structure:

```yaml
backends:
  backend_name:
    language: en|de|fr|...
    adapter:
      type: mock|grocy
      config:
        # Adapter-specific configuration
        key: value
    description: "Optional description"
```

## Environment Variable Substitution

The YAML loader supports environment variable substitution with two patterns:

- `${VAR_NAME}` - Required variable (raises error if not found)
- `${VAR_NAME:-default_value}` - Optional variable with default value

## Example Configuration

```yaml
backends:
  mock:
    language: en
    adapter:
      type: mock
      config: {}
    description: "Mock adapter for testing"

  production_grocy:
    language: en
    adapter:
      type: grocy
      config:
        base_url: "https://grocy.example.com"
        api_key: "${GROCY_API_KEY}"  # Required env var
        verify_ssl: true
    description: "Production Grocy instance"

  dev_grocy:
    language: en
    adapter:
      type: grocy
      config:
        base_url: "https://dev-grocy.example.com"
        api_key: "${DEV_GROCY_API_KEY:-dev_api_key}"  # Optional with default
        verify_ssl: false
    description: "Development Grocy instance"
```

## Usage

The configuration is automatically loaded by the adapter registry. Available backends are dynamically discovered from the YAML configuration.

```python
from app.adapters.registry import get_backend, get_available_backends

# Get list of configured backends
backends = get_available_backends()  # ['mock', 'production_grocy', 'dev_grocy']

# Create backend instance
backend = get_backend('production_grocy')
```

## Benefits

1. **Clearer Structure**: Nested configuration is easier to read and maintain
2. **Environment Variables**: Secure handling of sensitive data like API keys
3. **Validation**: YAML syntax validation and missing variable detection
4. **Scalability**: Easy to add new backends without code changes
5. **Documentation**: Built-in descriptions for each backend configuration
