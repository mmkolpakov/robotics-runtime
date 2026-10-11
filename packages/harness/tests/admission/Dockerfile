FROM docker.io/library/python@sha256:8a7e7cc04fd3e2bd787f7f24e22d5d119aa590d429b50c95dfe12b3abe52f48b
ARG ADMISSION_ARTIFACTS=artifacts/evaluator-admission
COPY ${ADMISSION_ARTIFACTS}/requirements.txt /opt/admission/requirements.txt
RUN python -m pip install --no-cache-dir --require-hashes --no-deps -r /opt/admission/requirements.txt
COPY ${ADMISSION_ARTIFACTS}/wheels /opt/admission/wheels
RUN python -m pip install --no-cache-dir --no-deps \
    /opt/admission/wheels/robotics_runtime_contracts-*.whl \
    /opt/admission/wheels/robotics_acceptance_harness-*.whl
COPY ${ADMISSION_ARTIFACTS}/verifier /opt/admission/verifier
COPY ${ADMISSION_ARTIFACTS}/auxiliary /opt/admission/auxiliary
COPY ${ADMISSION_ARTIFACTS}/trusted-root.jsonl /opt/admission/trusted-root.jsonl
COPY ${ADMISSION_ARTIFACTS}/bundle.json /opt/admission/bundle.json
COPY ${ADMISSION_ARTIFACTS}/profile.json /opt/admission/profile.json
COPY ${ADMISSION_ARTIFACTS}/receipts /opt/admission/receipts
RUN chmod 0555 /opt/admission/verifier && chmod 0444 /opt/admission/profile.json /opt/admission/trusted-root.jsonl
COPY packages/harness/tests/admission/preinstall.py /opt/admission/preinstall.py
RUN python /opt/admission/preinstall.py \
    && python -m pip install --no-cache-dir --no-deps /opt/captured/*.whl \
    && rm -r /opt/captured
COPY packages/harness/tests/admission/witness.py /opt/admission/witness.py
ENV PYTHONDONTWRITEBYTECODE=1 HOME=/tmp
WORKDIR /tmp
ENTRYPOINT ["robotics-acceptance"]
