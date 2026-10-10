workspace "Robotics verification workflows" "Consumer-owned usage examples for published Python tools, the embedded host and optional services; native coverage belongs to each selected profile." {
    !identifiers hierarchical
    model {
        integrator = person "Integrator" "Selects profiles and verifies evidence."
        product = softwareSystem "System under test" "Robot / control / vision application." {
            tags "External"
        }
        group "Native dependencies" {
        simulators = softwareSystem "Simulators" "Gazebo / Webots / Isaac; scoped." {
            tags "External"
        }
        autopilot = softwareSystem "Selected SDK peer" "MAVSDK server in the PX4 example; native peers belong to their selected profiles." {
            tags "External"
        }
        mediaSource = softwareSystem "Media source" "Native camera / RTSP / fixture." {
            tags "External"
        }
        }
        registries = softwareSystem "Registries" "Immutable packages / images / attestations." {
            tags "External"
        }
        platform = softwareSystem "Verification application" "Consumer-owned tools and native profiles." {
            runner = container "Consumer CLI / CI" "Invokes published Python tools." "Shell / Python / CI" {
                tags "Consumer"
            }
            host = container "Consumer coordinator" "Embeds the host library; callbacks own workload and payloads." "Consumer Node app / Cordis / Execa" {
                tags "Host"
            }
            group "Python tools" {
            documents = container "Document CLI" "Published contracts." "Python CLI" {
                tags "Published"
            }
            evaluation = container "Evaluation CLI" "Published evaluator." "Python CLI" {
                tags "Published"
            }
            }
            group "Native workers" {
            native = container "Provider worker" "Selected simulator SDK." "Native SDK / Python or C++" {
                tags "Provider"
            }
            media = container "Media worker" "GStreamer pipeline and reports." "Python GI / GStreamer" {
                tags "Media"
            }
            }
            evidence = container "Evidence store" "Local bytes and retained references." "Local files / retained references" {
                tags "Database"
            }
            externalApi = container "External Test API" "Producer metadata and upload custody." "Fastify / jose / public core Jobs"
            apiMetadata = container "Test metadata" "Tenant RLS, versions and proofs." "PostgreSQL" {
                tags "Database"
            }
            custody = container "Custody CLI" "Bounded verify, sign and receipt." "AWS CLI / cosign / retained-artifact / contracts CLI"
            mcp = container "Offline MCP" "Six read tools; source package." "Standard MCP SDK / public host workers"
        }
        group "SDK interfaces" {
        externalSdk = softwareSystem "External client application" "Embeds the selected SignalFlag SDK; project + JWT." {
            tags "External"
        }
        identity = softwareSystem "OIDC issuer" "JWT and JWKS." {
            tags "External"
        }
        objectStorage = softwareSystem "Versioned S3" "Opaque object versions." {
            tags "External"
        }
        }
        mcpClient = softwareSystem "MCP client" "Local trusted operator." {
            tags "External"
        }
        integrator -> platform "Run / verify"
        product -> platform "Configure / verdicts"
        product -> autopilot "Control / telemetry"
        platform -> simulators "Native runtimes"
        platform -> autopilot "Native control SDK"
        platform -> mediaSource "Selected media"
        platform -> registries "Install / verify"
        integrator -> platform.runner "Check documents" "CLI / CI"
        platform.runner -> platform.documents "Validate documents" "argv / files"
        platform.runner -> platform.evaluation "Evaluate retained evidence" "argv / files"
        platform.runner -> platform.evidence "Preserve inputs / reports" "Files"
        integrator -> platform.host "Run selected native profile" "Consumer CLI/API"
        product -> platform.host "Trusted coordinator" "Host API / files"
        platform.host -> platform.documents "Validate documents" "argv / files"
        platform.host -> platform.evaluation "Evaluate evidence" "argv / files"
        platform.host -> platform.native "Lifecycle jobs" "Compose / argv"
        platform.host -> autopilot "Selected PX4 control profile" "MAVSDK / gRPC"
        platform.host -> platform.media "Media jobs" "argv / files"
        platform.media -> mediaSource "Declared input" "GStreamer / RTSP / fixture"
        platform.media -> platform.evidence "Frames / reports" "Exact files"
        platform.native -> simulators "Native SDK/controller" "Backend API"
        platform.native -> platform.evidence "Before reset / dispose" "Exact payloads"
        platform.documents -> platform.evidence "Write documents" "Files"
        platform.evaluation -> platform.evidence "Read bytes / write verdicts" "JSON / JUnit"
        platform.host -> platform.evidence "Export / cleanup proof" "Callback refs"
        integrator -> identity "Obtain JWT" "OIDC"
        integrator -> externalSdk "Configure client" "Project / JWT"
        externalSdk -> platform.externalApi "REST ×6 + config" "JWT / HTTP"
        externalSdk -> objectStorage "Opaque upload" "Presigned PUT"
        platform.externalApi -> identity "Verify JWT / JWKS" "jose / RS256"
        platform.externalApi -> platform.apiMetadata "Metadata / proofs" "SQL / forced RLS"
        platform.externalApi -> objectStorage "Bind VersionId" "Presign / HEAD"
        platform.externalApi -> platform.custody "Custody commands" "Core Jobs / argv"
        platform.custody -> objectStorage "Exact-version bytes" "CLI / GET"
        mcpClient -> platform.mcp "Artifact IDs" "MCP / stdio"
        platform.mcp -> platform.documents "Read contracts" "Public Jobs / argv"
        platform.mcp -> platform.evaluation "Read explanations" "Public Jobs / argv"
        platform.mcp -> platform.evidence "Registered local files" "SHA-256 / size"

        deploymentEnvironment "Development" {
            deploymentNode "Development host" "Example CPU topology; qualification is profile-scoped." "Windows / WSL2" {
                deploymentNode "Linux environment" "Source components; native and media coverage is profile-scoped." "Ubuntu 24.04 / WSL2" {
                    infrastructureNode "Rootless engine" "Owned socket; namespace mapping." "Podman / Compose"
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
        systemContext platform "Context" "Consumer-owned verification workflow and external systems; this is a usage example, not a repository boundary." {
            title "Verification workflow context"
            include integrator product platform simulators autopilot mediaSource registries externalSdk mcpClient
            autoLayout lr 20 25
        }
        container platform "Container" "Published Python tools consumed from a terminal or CI; no host service, Node runtime or optional API is required for this document workflow." {
            title "Published document workflow"
            include integrator platform.runner platform.documents platform.evaluation platform.evidence
            autoLayout lr 20 25
        }
        container platform "ContainerDetail" "Complete consumer, controller, simulator and media interface graph." {
            title "Native and consumer interfaces"
            include *
            autoLayout lr 80 100
        }
        container platform "ExternalTestAPI" "Optional source API; external producer metadata and custody are separate from native qualification." {
            title "Optional external Test API"
            include externalSdk identity objectStorage platform.externalApi platform.apiMetadata platform.custody
            autoLayout tb 20 25
        }
        container platform "NativeInterfaces" "Native usage example: consumer application embeds the host library; selected SDK and media dependencies remain native." {
            title "Native consumer application"
            include platform.host platform.documents platform.evaluation platform.native platform.media platform.evidence simulators mediaSource autopilot
            autoLayout lr 60 70
        }
        container platform "ConsumerInterfaces" "Embedded coordinator, product callbacks, public Python tools and retained evidence; optional services have their own view." {
            title "Embedded host and public tools"
            include integrator product platform.host platform.documents platform.evaluation platform.evidence
            autoLayout lr 60 70
        }
        deployment platform "Development" "DevelopmentDeployment" "Example CPU development profile; qualification remains profile-scoped." {
            title "Example CPU development topology"
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
            element "Group" {
                color "#0f172a"
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
            element "Consumer" {
                background "#f1f5f9"
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
            element "Provider" {
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
