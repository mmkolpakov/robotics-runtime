workspace "Robotics execution and qualification" "Joint platform from robotics-runtime and robotics-runtime-infra; compiled host and Python packages have separate releases; provider qualification is profile-scoped." {
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
        platform = softwareSystem "Robotics runtime platform" "Published host and Python tools; providers per profile." {
            host = container "Run host" "Prerelease ESM host." "Node 24 / Cordis / Execa" {
                tags "Host"
            }
            documents = container "Document CLI" "Published contracts." "Python CLI" {
                tags "Published"
            }
            evaluation = container "Evaluation CLI" "Published evaluator." "Python CLI" {
                tags "Published"
            }
            native = container "Provider worker" "Native SDK candidate." "Native SDK / Python or C++" {
                tags "Candidate"
            }
            media = container "Media worker" "Source GStreamer." "Python GI / GStreamer" {
                tags "Media"
            }
            evidence = container "Evidence store" "Retained bytes." "Files / object storage" {
                tags "Database"
            }
            externalApi = container "Optional external Test API" "Source service; external producer metadata and opaque byte custody." "Fastify / jose / public core Jobs"
            apiMetadata = container "External Test metadata" "Tenant/project RLS; upload versions, proof checkpoints and producer claims." "PostgreSQL" {
                tags "Database"
            }
            custody = container "Custody CLI processes" "Finite public download, verification, signature and receipt operations." "AWS CLI / cosign / retained-artifact / contracts CLI"
        }
        externalSdk = softwareSystem "External SDK client" "Limited SignalFlag SDK 1.8.0 recipe; project ID and explicit token." {
            tags "External"
        }
        identity = softwareSystem "OIDC issuer" "Configured JWT issuer and JWKS; fixture uses Keycloak." {
            tags "External"
        }
        objectStorage = softwareSystem "Versioned S3 service" "Opaque objects; fixture uses S3-compatible SeaweedFS." {
            tags "External"
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
        integrator -> identity "Obtain configured token" "OIDC"
        integrator -> externalSdk "Provide project and token" "Client configuration"
        externalSdk -> platform.externalApi "Six REST operations" "JWT / HTTP"
        externalSdk -> objectStorage "Opaque upload" "Presigned PUT / required headers"
        platform.externalApi -> identity "Verify JWT with configured JWKS" "jose / RS256"
        platform.externalApi -> platform.apiMetadata "Authorized metadata and proof checkpoints" "Same-client transaction / forced RLS"
        platform.externalApi -> objectStorage "Presign and bind exact upload version" "AWS SDK / HEAD"
        platform.externalApi -> platform.custody "Fixed server-owned operations" "Public core Jobs / bounded argv"
        platform.custody -> objectStorage "Verify retained bytes at exact VersionId" "Bounded public CLI / GET"

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
            include platform.host platform.documents platform.evaluation platform.native platform.media platform.evidence platform.externalApi platform.apiMetadata platform.custody externalSdk identity objectStorage
            autoLayout lr 60 60
        }
        container platform "ContainerDetail" "Complete consumer, controller, simulator and media interface graph." {
            title "Native and consumer interfaces"
            include *
            autoLayout lr 80 100
        }
        container platform "ExternalTestAPI" "Optional source API; external producer metadata and custody are separate from native qualification." {
            title "Optional external Test API"
            include integrator externalSdk identity objectStorage platform.externalApi platform.apiMetadata platform.custody
            autoLayout lr 70 80
        }
        container platform "NativeInterfaces" "Selected simulator, media and SDK dependencies; no common frame or control bus." {
            title "Native interfaces"
            include platform.host platform.native platform.media simulators mediaSource autopilot
            autoLayout lr 60 70
        }
        container platform "ConsumerInterfaces" "Product ownership, published document/evaluation tools and retained evidence." {
            title "Consumer interfaces"
            include integrator product platform.host platform.documents platform.evaluation platform.evidence autopilot
            autoLayout lr 60 70
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
                stroke "#2563eb"
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
