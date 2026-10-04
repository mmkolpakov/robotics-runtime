workspace "Robotics execution and qualification" "Joint platform from robotics-runtime and robotics-runtime-infra; source host and candidate providers are separate from the published Python pair." {
    !identifiers hierarchical
    model {
        integrator = person "Integrator" "Selects a profile, launches software and verifies retained evidence."
        product = softwareSystem "Product application" "Consumer-owned robot, NSU, vision and control behavior." {
            tags "External"
        }
        simulators = softwareSystem "Simulation engines" "Native Gazebo, Webots or Isaac runtime; per-profile capabilities." {
            tags "External"
        }
        autopilot = softwareSystem "Native control endpoint" "Consumer-selected MAVSDK server; transport, peer and command effect are separate facts." {
            tags "External"
        }
        mediaSource = softwareSystem "Native media source" "Selected camera/RTSP source or finite fixture; no portable frame semantics are assumed." {
            tags "External"
        }
        registries = softwareSystem "Artifact registries" "Published package/image assets and attestations." {
            tags "External"
        }
        platform = softwareSystem "Robotics runtime platform" "Joint runtime/infra platform: source composition host, published document/evaluation tools and separately qualified providers." {
            host = container "Composition host" "Source host: plugin loading, readiness, resource ownership and finite jobs." "Node 24 / Cordis / Execa"
            documents = container "Document worker" "Finite Python application using published contracts APIs; environment supplied by infra." "Python CLI"
            evaluation = container "Evaluation worker" "Finite Python application using published harness APIs; ROS observer is attach-only." "Python CLI"
            native = container "Native provider worker" "Candidate integrations: selected backend native API and observed facts; each has its own qualification." "Native simulator / Python or C++" {
                tags "Candidate"
            }
            media = container "Media consumer worker" "Source finite GStreamer worker; decoding and frame bytes stay outside the host." "Python GI / GStreamer"
            evidence = container "Retained evidence" "Exact payloads and references. Infra publishes signed qualification bundles after release verification." "Files / object storage" {
                tags "Database"
            }
        }
        integrator -> platform "Runs and verifies selected workloads"
        product -> platform "Supplies configuration and consumes qualification"
        product -> autopilot "Uses native control and telemetry"
        platform -> simulators "Integrates selected native runtimes"
        platform -> autopilot "Connects the selected native SDK"
        platform -> mediaSource "Consumes the selected media endpoint"
        platform -> registries "Installs and verifies immutable artifacts"
        integrator -> platform.host "Selects a trusted profile" "Consumer CLI/API"
        product -> platform.host "Runs its coordinator with trusted configuration" "Host API / files"
        platform.host -> platform.documents "Invokes bounded validation/writer jobs" "argv/files/exit"
        platform.host -> platform.evaluation "Invokes bounded evaluation jobs" "argv/files/exit"
        platform.host -> platform.native "Owns startup, readiness and teardown" "Compose/finite jobs"
        platform.host -> autopilot "Uses generated SDK clients; consumer owns command policy" "MAVSDK / gRPC"
        platform.host -> platform.media "Invokes bounded native pipeline work" "argv/files/exit"
        platform.media -> mediaSource "Consumes declared input" "GStreamer / RTSP or finite source"
        platform.media -> platform.evidence "Retains native reports and configured file outputs" "Exact files"
        platform.native -> simulators "Uses native SDK/controller" "Backend API"
        platform.native -> platform.evidence "Retains observations before reset/disposal" "Exact payloads"
        platform.documents -> platform.evidence "Validates and writes linked documents" "Files"
        platform.evaluation -> platform.evidence "Reads observations and writes results" "Files/JSON/JUnit"
        platform.host -> platform.evidence "Verifies export and cleanup outcomes" "File references"
        deploymentEnvironment "Home" {
            deploymentNode "Home workstation" "Existing workstation; source qualification is environment-scoped." "Windows / NVIDIA" {
                deploymentNode "dev WSL" "Existing development environment." "Ubuntu 24.04 / WSL2" {
                    infrastructureNode "Rootless container engine" "Owned project socket and namespace mapping." "Podman 4.9.3 / Compose 5.3.1"
                    containerInstance platform.host
                    containerInstance platform.documents
                    containerInstance platform.evaluation
                    containerInstance platform.native
                    containerInstance platform.media
                    containerInstance platform.evidence
                }
                deploymentNode "Native Windows target" "Isaac standalone target; Windows access confirmed, runtime qualification pending." "Windows / RTX 5070 Ti" {
                    tags "Candidate"
                    containerInstance platform.native {
                        tags "Candidate"
                    }
                }
            }
        }
    }
    views {
        systemContext platform "Context" "Actors and system boundary." {
            include *
            autoLayout lr
        }
        container platform "Container" "Executable processes and retained data; packages are not containers." {
            include *
            autoLayout lr
        }
        deployment platform "Home" "HomeDeployment" "Existing WSL plus candidate Windows GPU target." {
            include *
            autoLayout lr
        }
        styles {
            element "Person" {
                shape Person
            }
            element "Software System" {
                background "#35546f"
                color "#ffffff"
            }
            element "Container" {
                background "#e6edf3"
                color "#172431"
            }
            element "Database" {
                shape Cylinder
            }
            element "External" {
                background "#eeeeee"
                color "#333333"
            }
            element "Candidate" {
                border Dashed
            }
        }
    }
    configuration {
        scope softwaresystem
    }
}
