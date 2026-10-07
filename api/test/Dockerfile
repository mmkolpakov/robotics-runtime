ARG CONTRACTS_BASE
ARG EVIDENCE_TOOLS_BASE
FROM ${EVIDENCE_TOOLS_BASE} AS evidence-tools
FROM docker.io/library/node@sha256:b64fccfbcd1ae10d11b969a868b50e1c2530a7054813d5cdea04ac3bce551697 AS node
FROM ${CONTRACTS_BASE}
USER root
COPY --from=node /usr/local/bin/node /usr/local/bin/node
COPY --from=evidence-tools /usr/local/aws-cli /usr/local/aws-cli
RUN ln -s /usr/local/aws-cli/v2/current/bin/aws /usr/local/bin/aws \
    && test -x /opt/contracts/bin/robotics-contracts \
    && mkdir -p /opt/api /work/api-custody \
    && chown -R 1000:1000 /work/api-custody
COPY --chmod=0555 artifacts/worker-assets/retained-artifact.py /usr/local/libexec/retained-artifact
COPY --chmod=0555 api/test/retention-witness.py /usr/local/bin/retained-artifact
COPY --chmod=0555 artifacts/worker-assets/receipt-inputs.py /usr/local/bin/receipt-inputs
COPY --chmod=0555 artifacts/worker-assets/catatonit /usr/local/bin/catatonit
COPY api/node_modules /opt/api/node_modules
COPY api/dist /opt/api/dist
COPY api/package.json /opt/api/package.json
USER 1000:1000
ENV AWS_SHARED_CREDENTIALS_FILE=/run/secrets/s3-credentials \
    AWS_CONFIG_FILE=/run/secrets/s3-config \
    AWS_EC2_METADATA_DISABLED=true \
    PYTHONDONTWRITEBYTECODE=1 \
    PATH=/opt/venv/bin:/usr/local/bin:/usr/bin:/bin
WORKDIR /opt/api
ENTRYPOINT ["/usr/local/bin/catatonit","--","/usr/local/bin/node","/opt/api/dist/src/main.js"]
