# Preserved run and release records

These records describe their own package versions, source identities and tested
profiles. They remain historical evidence. Updating the current guide does not
change a recorded failure, qualify a newer image or establish a native result.

## Published Python package records

[Contracts 0.20.0](https://github.com/mmkolpakov/robotics-runtime/releases/tag/contracts-v0.20.0)
and [harness 0.21.0](https://github.com/mmkolpakov/robotics-runtime/releases/tag/harness-v0.21.0)
retain their tagged sources, release archives and provenance. Their independent
consumer installation checks establish package/API/archive behavior for those
wheels. They are separate from simulator, hardware or infra image qualification.

The [host 0.1.0-rc.0 release](https://github.com/mmkolpakov/robotics-runtime/releases/tag/host-v0.1.0-rc.0)
retains its source manifest, checksums and external installation report. It has its
own release identity and scope.

## Infra profile records

The accepted B2 stock profile belongs to
[R9 v0.9.0-rc.1](https://github.com/mmkolpakov/robotics-runtime-infra/releases/tag/v0.9.0-rc.1)
and contracts 0.18.1 / harness 0.19.0. It covers one ROS domain, UInt64 and one
finalized MCAP recording.

[R10 v0.10.0-rc.1](https://github.com/mmkolpakov/robotics-runtime-infra/releases/tag/v0.10.0-rc.1)
uses contracts 0.18.2 / harness 0.19.1 and has verified release identities. Its
[released B3 run](https://github.com/mmkolpakov/robotics-runtime-infra/actions/runs/37157837270)
passed entity checks, then failed with a 107 ms exact-step overshoot and a JointState
timeout. B3 remains unaccepted. Historical v0.8.0-rc.1 remains bound to
contracts 0.15.4 / harness 0.17.1.

The [infra compatibility policy](https://github.com/mmkolpakov/robotics-runtime-infra/blob/main/docs/compatibility.md)
distinguishes caller, tooling and image-source commits. The
[v0.11.0-rc2 release](https://github.com/mmkolpakov/robotics-runtime-infra/releases/tag/v0.11.0-rc2)
has its own contracts 0.19.0 / harness 0.20.0 composition; the current Python pair
must not be substituted into that composition by implication.

Native acceptance is stated by each pinned profile's records. Source fixtures,
archive validation and live observer unit/integration checks do not establish
arbitrary consumer or hardware qualification.
