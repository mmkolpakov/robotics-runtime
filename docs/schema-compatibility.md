# Published schema compatibility

`scripts/check_schema_compatibility.py` compares the current contracts with the
latest stable `contracts-v*` tag. It verifies the tag metadata, extracts the
published schemas and valid fixtures from Git objects, then checks both schema
structure and the public `validate_document` API in isolated Python processes.

The semantic corpus consists of document values. Its fixture decoder is independent
of either package version's file loader: a frozen YAML fixture may use aliases
even when the released public loader rejects aliases. The decoder resolves those
aliases using YAML 1.2 and supplies the same JSON values to both validators. It
never modifies published fixture bytes, skips a document, or replaces the latest
release with an older baseline.

Fixtures must represent JSON values without duplicate keys, cycles, non-string
object keys, non-finite numbers, or native YAML types such as timestamps and sets.
Quote timestamps in YAML fixtures. Files ending in `.json` require JSON syntax.
Decoder failures fail the compatibility check with the fixture filename.

This check covers schema and semantic compatibility. Production input syntax and
resource limits remain covered by the package's serialization tests; this fixture
decoder is used only by the development compatibility tool.
