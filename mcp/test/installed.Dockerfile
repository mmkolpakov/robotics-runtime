FROM docker.io/library/node:24.21.0-trixie-slim@sha256:c83040f7e24bacea68e58a0b96a484ba430bf24abb2973eab7ba4701144b7b63 AS node
FROM docker.io/library/python@sha256:8a7e7cc04fd3e2bd787f7f24e22d5d119aa590d429b50c95dfe12b3abe52f48b
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY mcp/public-cli.lock /opt/worker-inputs/public-cli.lock
RUN python -m venv /opt/public-workers \
    && /opt/public-workers/bin/python -m pip install --no-cache-dir --require-hashes --no-deps \
       --only-binary :all: --requirement /opt/worker-inputs/public-cli.lock \
    && /opt/public-workers/bin/python -m pip check \
    && python -c 'import sys; assert sys.version_info[:3] == (3, 12, 13)' \
    && node -e 'if (process.version !== "v24.21.0") process.exit(1)' \
    && /opt/public-workers/bin/python -c 'from importlib.metadata import version; assert version("robotics-runtime-contracts") == "0.21.1"; assert version("robotics-acceptance-harness") == "0.22.3"'
ENV HOME=/tmp PYTHONDONTWRITEBYTECODE=1
WORKDIR /consumer
ENTRYPOINT ["node", "--test", "/consumer/test/native-documents.integration.mjs"]
