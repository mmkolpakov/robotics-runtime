# Local evidence and observation timestamps

Local artifacts and recording summaries must be regular files below the directory
containing their evidence index. A matching digest alone does not authorize reading
an arbitrary local path. URI and local-path identities must agree.

The reader checks containment before reading bytes. On POSIX it walks directory
descriptors without following symbolic links and opens the final file without
blocking on a FIFO. On Windows it checks the final path of the opened file handle,
including junction resolution. An unavailable containment check is an error.
The evidence directory itself is a trusted input supplied by the caller; these
checks do not authenticate its owner or replace filesystem access controls.

Size, SHA-256 and captured recording-summary bytes come from one descriptor.
Changes to file size or metadata during a read are rejected. Recording summaries
also obey the contracts document size limit. OTLP files reopened for evaluation
repeat containment and digest checks and parse the verified bytes. A writer may
finish evidence after the measurement-complete marker: verification retries
missing, partial or invalid evidence until its configured monotonic deadline and
retains the final input error if that deadline expires.

Published first-message and lifecycle timestamps are Unix nanoseconds. Internal
graph snapshots, clock samples and timeout calculations use the monotonic clock;
they must not be subtracted from document timestamps. Topic types are selected in
lexical order when the observed graph contains several types.

Result JSON and JUnit files are atomically replaced after setting mode `0644` on
POSIX, even when the caller uses a restrictive umask. Windows files inherit the
destination directory's access controls.
