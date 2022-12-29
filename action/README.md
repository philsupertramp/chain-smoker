# chain-smoker-action

GitHub action for the [chain-smoker](https://github.com/philsupertramp/chain-smoker) tool.

## Configuration
The variable `directory` is available for configuration and lets you supply the directory that holds the test configuration for your repository


## Example

```yaml
jobs:
  hello_world_job:
    runs-on: ubuntu-latest
    name: A test job
    steps:
      # To use this repository's private action,
      # you must check out the repository
      - name: Checkout
        uses: actions/checkout@v3
      - name: Action step
        uses: philsupertramp/chain-smoker-action@v1.0.1
        with:
          directory: 'examples'
```
