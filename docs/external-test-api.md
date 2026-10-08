# Optional external Test API

This source service supports the limited external Test recipe below with
unmodified SignalFlag SDK 1.8.0. Projects, branches and tenant membership are
configured before the SDK runs. A completed SDK Test reports producer metadata;
it does not qualify a robot or launch a native workload.

## Run the source fixture

From a checkout, with Docker, its default Buildx builder, Git, Bash and Python 3:

~~~bash
API_FIXTURE_ENGINE=docker api/test/run-fixture.sh
~~~

The driver builds the API, unchanged installed SDK and custody inputs from
[pinned sources](../api/test/upstream-lock.json). It creates disposable local
PostgreSQL 18.6, Keycloak 26.8 and SeaweedFS 4.29 services, generates private
fixture credentials, and removes its owned resources. It is a finite test,
not a long-running service deployment. A refused check or
unverified cleanup returns a nonzero exit. Safe reports and original custody
proofs are retained under `artifacts/api-ci-safe/`.

The fixture exercises both tenants, all six REST operations, JSONL/PNG/empty
PUTs, authorization refusals, lost registration/close responses, eight concurrent
closes and two-upload recovery after a refused close and API restart. It verifies
exact VersionId payloads and preserves the first committed proof checkpoint.
SeaweedFS is a local S3-compatible protocol fixture; this is not AWS qualification.

## Use an installed SDK

Obtain a real token from the configured issuer and authorize its subject through
tenant/project membership. The client receives that token explicitly; this
recipe does not use the SDK's Auth0 helpers. Install the client in your own
Python environment with the [pinned dependency lock](../api/test/sdk-requirements.lock).

~~~python
from pathlib import Path

import httpx
from signalflag.sdk.batch import Batch
from signalflag.sdk.client import AuthenticatedClient
from signalflag.sdk.test import LogType, Test

token = Path("/run/secrets/sdk-token").read_text().strip()
client = AuthenticatedClient(
    base_url="http://api:3000",
    token=token,
    timeout=httpx.Timeout(90.0),
)

Path("empty.log").write_bytes(b"")
with Batch(
    client=client,
    project_id="YOUR_EXISTING_PROJECT_UUID",
    branch="main",
    name="External Test",
    metrics_config_path=None,
    templates_path=None,
) as batch:
    with Test(client=client, batch=batch, name="opaque external test") as run:
        run.emit("motion", {"speed": 1}, timestamp=1_791_000_000_000_000_000)
        run.attach_log("attachment.png", log_type=LogType.OTHER_LOG, wait=True)
        run.attach_log("empty.log", log_type=LogType.OTHER_LOG, wait=True)
~~~

The example uses the fixture's container-network API address. Replace the
endpoint and project UUID with configured values, and supply the PNG file.
Both the API and returned S3 upload URL must be reachable from the client.
The Test context flushes and uploads the SDK's original emissions JSONL.
Both `None` options are required: the SDK's default metrics config path invokes
GraphQL configuration synchronization before the REST journey. Do not add
`project_name`, system, test-suite or metrics-set options to this recipe.

The service implements this bounded surface:

~~~text
GET  /projects/{projectID}/branches?name=main
POST /projects/{projectID}/batches/light
POST /projects/{projectID}/batches/{batchID}/jobs
POST /projects/{projectID}/batches/{batchID}/jobs/{jobID}/logs
POST /projects/{projectID}/batches/{batchID}/jobs/{jobID}/close
POST /projects/{projectID}/batches/{batchID}/close
~~~

Log registration returns the fixed server-owned object URL and required PUT
headers. Checksum, size, media type and exact VersionId must match before custody.
An identical pending, unbound registration can renew its URL after a refused
close. A close retry must preserve the original producer claim. Registration
identity and close recovery do not provide exactly-once batch/job creation:
those POSTs have no client nonce or idempotency key.

## Service boundary

The [entry point](../api/src/main.ts) configures a separate Fastify process.
The [SQL migration](../api/sql/001-external-tests.sql) uses forced tenant/project
RLS; the application role must not own tables or reach privileged roles.
JWT verification fixes issuer, audience, RS256, subject, expiry and the
`sdk-write` role. Each SQL transaction sets the verified issuer/subject on the
same client.

Storage endpoints, bucket, object keys, byte limits, credential files, signing
policy and worker commands belong to the server. The SDK cannot select an
arbitrary URI or worker argv. Public core Jobs settle finite CLI processes;
existing custody validators remain authoritative. Original proof blobs are
committed per upload, and the job closes only when every upload is retained.

![Optional API process boundary](architecture/generated/ExternalTestAPI.svg)

This optional package is private and has no published API image release.
Released Python packages and host artifacts do not install the service.
GraphQL/BFF, default configuration sync, Auth0 helpers, Web UI and product MCP
are not supplied. Producer status is not a native verdict, opaque emissions are
not converted into native observations, and the service does not use RunOwner.
The source fixture does not establish deployment, AWS, full vendor-platform
compatibility or an SLA.
