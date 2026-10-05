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
            host = container "Composition host" "Source plugins / finite jobs / ownership." "Node 24 / Cordis / Execa"
            documents = container "Document worker" "Published contracts / writers." "Python CLI"
            evaluation = container "Evaluation worker" "Published; ROS attach-only." "Python CLI"
            native = container "Provider worker" "Candidate native APIs; qualify each profile." "Native SDK / Python or C++" {
                tags "Candidate"
            }
            media = container "Media worker" "Source GStreamer; native decode / frames." "Python GI / GStreamer"
            evidence = container "Retained evidence" "Exact files; bundles signed after release checks." "Files / object storage" {
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
        platform.host -> platform.documents "Validate / write" "argv / files / exit"
        platform.host -> platform.evaluation "Evaluate" "argv / files / exit"
        platform.host -> platform.native "Startup / ready / teardown" "Compose / finite jobs"
        platform.host -> autopilot "SDK clients / consumer policy" "MAVSDK / gRPC"
        platform.host -> platform.media "Bounded media jobs" "argv / files / exit"
        platform.media -> mediaSource "Declared input" "GStreamer / RTSP / fixture"
        platform.media -> platform.evidence "Native reports / outputs" "Exact files"
        platform.native -> simulators "Native SDK/controller" "Backend API"
        platform.native -> platform.evidence "Retain before reset / dispose" "Exact payloads"
        platform.documents -> platform.evidence "Validate / write docs" "Files"
        platform.evaluation -> platform.evidence "Read evidence / write results" "Files / JSON / JUnit"
        platform.host -> platform.evidence "Nonempty refs; observe cleanup" "Callback refs"
        deploymentEnvironment "Home" {
            deploymentNode "Home workstation" "Hosts the WSL CPU route." "Windows / WSL2" {
                deploymentNode "dev WSL" "CPU qualification by profile." "Ubuntu 24.04 / WSL2" {
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
    }
    views {
        systemContext platform "Context" "Actors and system boundary." {
            title "Platform context"
            include *?
            autoLayout lr 10 50
        }
        container platform "Container" "Owned processes and retained data; native interfaces are in ContainerDetail." {
            title "Process composition"
            include platform.host platform.documents platform.evaluation platform.native platform.media platform.evidence
            autoLayout lr 10 50
        }
        container platform "ContainerDetail" "Complete consumer, controller, simulator and media interface graph." {
            title "Native and consumer interfaces"
            include *
            autoLayout lr 50 30
        }
        deployment platform "Home" "HomeDeployment" "Implemented WSL CPU route with provider-specific qualification." {
            title "WSL CPU deployment"
            include *
            autoLayout tb 100 40
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
                width 380
                height 380
                fontSize 36
            }
            relationship "Relationship" {
                fontSize 36
                width 240
            }
            element "Person" {
                shape Person
                width 420
                fontSize 36
                metadata false
            }
            element "Software System" {
                fontSize 36
                background "#35546f"
                color "#ffffff"
            }
            element "Container" {
                background "#e6edf3"
                color "#172431"
            }
            element "Database" {
                shape Cylinder
                height 440
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
