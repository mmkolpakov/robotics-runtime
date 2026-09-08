# Standard-library helpers

Adjacent observations use `itertools.pairwise`, timestamp parsing uses native
`datetime.fromisoformat` support for `Z`, and OTLP flags/temporality use the
generated protobuf enum constants.

File URI paths are decoded with `urllib.request.url2pathname`, available across
the supported Python 3.12–3.14 range. A contract `local_path` retains its literal
characters: quote it before converting the legacy POSIX path spelling on Windows,
so percent signs in filenames are preserved. The URI must still have a local authority and
identify the same contained evidence file. The static boundary permits only this
conversion helper; networking imports and calls remain prohibited.

The percentile replacement is deferred under the equivalence requirement.
`statistics.quantiles([0.0, 3.0], n=100, method="inclusive")[94]` returns `2.85`,
while the current interpolation returns `2.8499999999999996`. A threshold equal
to the latter changes an existing `le` verdict. Adopting different rounding needs
an explicit comparison policy rather than an apparently neutral helper change.
Histogram interval estimates are unrelated to raw-sample percentiles.
