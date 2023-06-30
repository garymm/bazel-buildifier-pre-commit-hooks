# bazel buildifier pre-commit hooks

[Pre-commit](https://pre-commit.com/) hooks for Bazel [buildifier](https://github.com/bazelbuild/buildtools/blob/master/buildifier/README.md).

Sample `.pre-commit-config.yaml`:

```yaml
-   repo: https://github.com/garymm/bazel-buildifier-pre-commit-hooks
    rev: v6.1.2
    hooks:
    -   id: bazel-buildifier
```
