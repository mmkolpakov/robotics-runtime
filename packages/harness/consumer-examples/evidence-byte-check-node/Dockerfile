FROM node:24.21.0-trixie-slim@sha256:c83040f7e24bacea68e58a0b96a484ba430bf24abb2973eab7ba4701144b7b63
COPY evaluate.mjs /opt/evaluator/evaluate.mjs
USER 65532:65532
ENTRYPOINT ["node", "/opt/evaluator/evaluate.mjs"]
