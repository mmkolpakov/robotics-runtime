workspace "Robotics execution and qualification" "Joint platform from robotics-runtime and robotics-runtime-infra; source host and candidate providers are separate from the published Python pair." {
    !identifiers hierarchical
    model {
        integrator = person "Integrator" "Selects profiles and verifies evidence."
        product = softwareSystem "Product application" "Robot, NSU, control and vision behavior." {
            tags "External"
        }
        simulators = softwareSystem "Simulation engines" "Gazebo / Webots / Isaac; profile-scoped." {
            tags "External"
        }
        autopilot = softwareSystem "MAVSDK endpoint" "MAVSDK: separate transport, peer and effect facts." {
            tags "External"
        }
        mediaSource = softwareSystem "Media source" "Camera, RTSP or fixture; native frame semantics." {
            tags "External"
        }
        registries = softwareSystem "Artifact registries" "Immutable packages, images and attestations." {
            tags "External"
        }
        platform = softwareSystem "Robotics runtime platform" "Source host, published Python tools; providers per profile." {
            host = container "Composition host" "Source: lifecycle and ownership." "Node 24 / Cordis / Execa" {
                tags "Host"
            }
            documents = container "Document worker" "Published contracts / writers." "Python CLI" {
                tags "Published"
            }
            evaluation = container "Evaluation worker" "Published evidence evaluator." "Python CLI" {
                tags "Published"
            }
            native = container "Provider worker" "Candidate native SDK." "Native SDK / Python or C++" {
                tags "Candidate"
            }
            media = container "Media worker" "Source: GStreamer frames." "Python GI / GStreamer" {
                tags "Media"
            }
            evidence = container "Retained evidence" "Retained files; separate trust." "Files / object storage" {
                tags "Database"
            }
        }
        integrator -> platform "Run and verify workloads"
        product -> platform "Supply config; read verdicts"
        product -> autopilot "Control / telemetry"
        platform -> simulators "Selected native runtimes"
        platform -> autopilot "Selected SDK"
        platform -> mediaSource "Selected media"
        platform -> registries "Install / verify"
        integrator -> platform.host "Trusted profile" "Consumer CLI/API"
        product -> platform.host "Trusted coordinator" "Host API / files"
        platform.host -> platform.documents "Validate documents" "argv / files"
        platform.host -> platform.evaluation "Evaluate evidence" "argv / files"
        platform.host -> platform.native "Lifecycle jobs" "Compose / argv"
        platform.host -> autopilot "SDK clients / consumer policy" "MAVSDK / gRPC"
        platform.host -> platform.media "Media jobs" "argv / files"
        platform.media -> mediaSource "Declared input" "GStreamer / RTSP / fixture"
        platform.media -> platform.evidence "Frames / reports" "Exact files"
        platform.native -> simulators "Native SDK/controller" "Backend API"
        platform.native -> platform.evidence "Before reset / dispose" "Exact payloads"
        platform.documents -> platform.evidence "Write documents" "Files"
        platform.evaluation -> platform.evidence "Read bytes / write verdicts" "JSON / JUnit"
        platform.host -> platform.evidence "Export / cleanup proof" "Callback refs"
        deploymentEnvironment "Home" {
            deploymentNode "Home workstation" "Source WSL CPU topology; qualification is profile-scoped." "Windows / WSL2" {
                deploymentNode "dev WSL" "Source components; native and media coverage is profile-scoped." "Ubuntu 24.04 / WSL2" {
                    infrastructureNode "Rootless engine" "Owned socket; namespace mapping." "Podman 4.9.3 / Compose 5.3.1"
                    containerInstance platform.host
                    containerInstance platform.documents
                    containerInstance platform.evaluation
                    containerInstance platform.native
                    containerInstance platform.media
                    containerInstance platform.evidence
                }
            }
        }
        deploymentEnvironment "Local" {
            deploymentNode "Local execution profile" "Source topology, not a universal qualification." "Linux / Docker or rootless Podman" {
                inputs = infrastructureNode "Read-only inputs" "Admitted profile and native assets." "Mounted files" {
                    tags "Inputs"
                }
                engine = infrastructureNode "Engine and Compose" "One owned project per attempt." "Native container API" {
                    tags "Host"
                }
                coordinator = containerInstance platform.host
                worker = containerInstance platform.native
                retained = containerInstance platform.evidence
                inputs -> coordinator "Admit closure" "Files / hashes"
                inputs -> worker "Native scene / config" "Read-only"
                coordinator -> engine "Owned execution" "Local API"
            }
        }
    }
    views {
        systemContext platform "Context" "Actors and system boundary." {
            title "Platform context"
            include *?
            autoLayout lr 60 60
        }
        container platform "Container" "Owned processes and retained data; native interfaces are in ContainerDetail." {
            title "Process composition"
            include platform.host platform.documents platform.evaluation platform.native platform.media platform.evidence
            autoLayout lr 60 60
        }
        container platform "ContainerDetail" "Complete consumer, controller, simulator and media interface graph." {
            title "Native and consumer interfaces"
            include *
            autoLayout tb 60 70
        }
        deployment platform "Home" "HomeDeployment" "Source WSL CPU topology; this view is not a complete consumer qualification." {
            title "Source WSL CPU topology"
            include *
            autoLayout tb 100 40
        }
        deployment platform "Local" "ExecutionDeployment" "Selected native-worker path; document and media jobs use their own profiles." {
            title "Local execution / source topology"
            include *
            autoLayout lr 60 60
        }
        properties {
            "structurizr.metadata" "false"
            "structurizr.description" "false"
            "structurizr.boundaryPadding" "20"
            "structurizr.deploymentNodePadding" "20"
            "structurizr.groupPadding" "20"
        }
        styles {
            element "Element" {
                shape RoundedBox
                width 320
                height 150
                fontSize 26
                strokeWidth 2
                background "#f8fafc"
                color "#0f172a"
                stroke "#cbd5e1"
                metadata false
            }
            relationship "Relationship" {
                fontSize 22
                width 190
                color "#475569"
                style solid
                routing Orthogonal
                thickness 2
            }
            element "Person" {
                shape Person
                width 280
                height 230
            }
            element "Software System" {
                background "#dbeafe"
                stroke "#60a5fa"
            }
            element "Container" {
                background "#f1f5f9"
            }
            element "Host" {
                background "#dbeafe"
                stroke "#2563eb"
            }
            element "Published" {
                background "#ecfdf5"
                stroke "#047857"
            }
            element "Media" {
                background "#ecfeff"
                stroke "#0e7490"
            }
            element "Database" {
                shape Cylinder
                height 175
                background "#eef2ff"
                stroke "#6d28d9"
            }
            element "External" {
                background "#f8fafc"
                stroke "#94a3b8"
            }
            element "Candidate" {
                background "#fffbeb"
                stroke "#b45309"
                border Dashed
            }
            element "Inputs" {
                shape Folder
                background "#f8fafc"
                stroke "#94a3b8"
            }
            element "Deployment Node" {
                stroke "#94a3b8"
                background "#f8fafc"
            }
        }
    }
    configuration {
        scope softwaresystem
    }
}
