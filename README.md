# Risk-Based Service Mesh

Data sources
* SBOM - CycloneDX, SPDX
* Cybersecurity Risk Quantification (CRQ) - CVE, CVSS v3/v4
* Risk Score -
  * EPSS First.org
  * Kenna aka Cisco Vulnerability management
  * CISA KEV

Policy Control Point
* Centralized interface e.g. web UI to
  * create policy objects
  * view policies
  * policy drift analysis - policy failed to apply etc.
  * policy playground - VNF lab simulating live network before applying
  * ML/AI engines to recommend policy etc 

Policy Decision Point
* Mesh
* Cilium policies
* Tetragon policies

Policy Enforcement Point
* CNI - overlay network within k8s plane
* Leaf switches
* VNF/NFV form factors - primarily in underlay network
  * vSwitches
  * vHost - VNF
  * VM (could also be running on k8s in exceptional cases - hyperconvergence HCI infra)

Use cases
1. Connectivity (that can't break)
   * batch workloads
     * Calico with iptables
     * Would also require a data pipeline in workloads for reporting etc. e.g. Kafka, Spark etc.
   * low priority networking - 50-100ms latency
     * Calico with VXLAN/ Calico with eBPF
   * high priority live workload - 1-10ms latency
     * eBPF, XDP, Cilium
   * ultra low latency workloads - Kernel level, OS bypass
     * SPDK, DPDK
     * SR-IOV for PCIe
     * SmartNIC hardware support
     * FPGA acceleration - programming via HLS or SV

2. Cluster level traffic management and Netsec
   * API Gateway ingress throttling
   * egress - WAF, HMF, DLP
   * SNI passthrough for performance
   * Node OS level
     * ASLR
     * kTLS (performance)
     * nodes should support BTF for eBPF (especially Tegragon)

3. Microsegmentation and multitenancy
   * Risk aware app-to-app microsegmentation via mesh
   * netsec microsegmentation of underlay network via SDN
   * multitenancy via signed JWT
     * JWT invalidation via "logout" workflow for human users - keep track of issued kid from Keycloak per JWT
     * job completion triggers similar "logout" like invalidation flow invalidating the JWT

4. GenAI workloads
   * AI gateway e.g. Kong
   * Time and task based policy
   * Proxy GenAI model - canary - accept prompts
   * Prompt signing and enforcmenet 
   * To explore - system prompt in eBPF maps (performance tradeoffs)

5. Observability, Telemetry and Fault management
   * Continuous Profiling: Parca (eBPF-based, zero-code CPU/memory profiling)
   * Deep Network Visibility: Pixie.dev & Cilium Hubble (eBPF flow tracing)
   * MDT Model Driven Telemetry Yang model based for device level network telemetry
   * CNCF MELT Observability
   * pull mode request queue (pushback queue for noisy neighbor) before it hits cluster ingress -> gateway

6. Supply chain provenance
   * SLSA.dev
   * Sigstore
   * Notary
   * enforce via L7 policy Kyverno

7. Identity management
   * running outside of worker clusters (on BM or another k8s or cloud IDP)
   * IDP - Keycloak/Dex
   * SCIM/SailPoint IIQ
   * common intermediate CA for all clusters via ACME
   * SPIFFE SVID via SPIRE server

```mermaid
graph TB
    subgraph External["External Services / Registries"]
        EPSS["FIRST.org EPSS API"]
        Sigstore["Sigstore / Rekor Log"]
    end

    subgraph Fabric["Physical Network Underlay"]
        ToR["Top-of-Rack Switches (ASIC / ACLs)"]
        APIC["Cisco APIC / SDN Controller"]
    end

    subgraph Cluster["Multi-Cluster Kubernetes Runtime (KinD / Production)"]
        
        subgraph ControlPlane["Control Plane Layer"]
            Istiod["Istiod (Delta xDS / L7 Control)"]
            SpireServer["SPIRE Server (PKI & Attestation)"]
            Operator["Custom Risk / EPSS Go Operator"]
        end

        subgraph Node["Compute Node (Linux Kernel 6.x)"]
            
            subgraph Kernel["Kernel Space (eBPF / NetSec)"]
                TC["Traffic Control (tc) & XDP"]
                SockMap["Sockmap / sk_msg (Zero-Copy)"]
                WG["WireGuard (cilium_wg0 Encryption)"]
            end

            subgraph NodeDaemons["Node Daemon Layer"]
                Ztunnel["ztunnel (Rust L4 mTLS / HBONE)"]
                SpireAgent["SPIRE Agent (Unix SDS)"]
                Tetragon["Tetragon (Runtime eBPF Security)"]
                Hubble["Cilium Hubble (Flow Telemetry)"]
            end

            subgraph AppNamespace["Application Namespace (business-app)"]
                Waypoint["Waypoint Proxy (Envoy L7)"]
                AppPod["Workspace Service Pod (App Container)"]
            end
        end
    end

    %% Data & Control Flows
    EPSS --> Operator
    Operator -->|Mutation| Istiod
    Istiod -->|xDS Push| Waypoint
    SpireServer -->|Attestation| SpireAgent
    SpireAgent -->|SVIDs via SDS| Ztunnel
    
    AppPod -->|Socket sendmsg| SockMap
    SockMap -->|Bypass TCP Stack| Ztunnel
    Ztunnel -->|WireGuard Encrypt| WG
    WG -->|Underlay Packet| ToR
    
    APIC -.->|gNMI / RESTCONF Sync| ToR
    Hubble -->|Metrics & Traces| Prometheus["Prometheus / OTEL Collector"]
    Tetragon -->|Audit Events| Loki["Grafana Loki / Observability"]
