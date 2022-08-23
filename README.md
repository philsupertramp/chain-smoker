# chain-smoker
An easy-to-use testing framework for web interfaces.

## Usage:
```yaml
type: 'api-test'
config:
  client:
    base_url: 'https://example.com'
tests:
  test_something:
    endpoint: ''
    method: 'get'
    status_code: 200
    contains: 'This domain is for use in illustrative examples in documents. You may use this domain in literature without prior coordination or asking for permission.'
```