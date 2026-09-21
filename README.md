# Risk-Based Multi-Cluster Microsegmentation via Service Mesh

An enterprise-grade, zero-trust reference architecture combining eBPF kernel acceleration, sidecarless service mesh topology (Istio Ambient), dynamic identity attestation (SPIFFE/SPIRE), and risk-aware microsegmentation across multi-cluster environments.

---

## 1. Data Sources & Intelligence Inputs

* **Software Bill of Materials (SBOM):** CycloneDX, SPDX
* **Cybersecurity Risk Quantification (CRQ):** CVE, CVSS v3/v4
* **Risk Intelligence & Threat Scoring:**
  * FIRST.org EPSS (Exploit Prediction Scoring System)
  * Kenna / Cisco Vulnerability Management
  * CISA KEV (Known Exploited Vulnerabilities)

---

## 2. Policy Architecture Control Planes

* **Policy Control Point (Management Plane):** Centralized UI/API for policy creation, drift analysis, dry-run simulation labs, and ML-assisted policy recommendation.
* **Policy Decision Point (Control Plane):** Istiod (xDS translation), SPIRE Server (SVID issuance), Cilium Operator, and Tetragon Operator.
* **Policy Enforcement Point (Data Plane):** 
  * **In-Cluster:** Cilium eBPF (`tc`/`sockmap`), Istio `ztunnel` (Rust L4 mTLS), and Envoy Waypoint Proxies (L7 RBAC).
  * **Underlay Network:** Physical Leaf/ToR switches and VNF/NFV form factors (vSwitches, vHosts, VMs) synchronized via gNMI/RESTCONF.

---

## 3. Core Use Cases & Architectural Matrix

### 3.1. Latency-Aware Connectivity & Datapath Tiering
* **Standard Workloads:** Baseline overlay networking managed via eBPF host-routing.
* **High-Priority Live Workloads (1–10ms Latency):** eBPF `sockmap` (`sk_msg`) zero-copy socket bypass and eXpress Data Path (XDP) driver hooks.
* **Ultra-Low Latency Workloads (OS Bypass):** SR-IOV (PCIe passthrough), SPDK/DPDK, and hardware SmartNIC/FPGA acceleration paths.

### 3.2. Cluster-Level Traffic Management & NetSec
* **Ingress Boundary:** API Gateway rate limiting, L7 throttling, and SNI Passthrough for end-to-end zero-trust encryption.
* **Egress Control:** WAF, Hostile Machine Framework (HMF) inspection, and DLP domain filtering via Cilium FQDN policies.
* **Kernel Performance:** Kernel TLS (kTLS) offload and ASLR memory protection at the node OS layer.

### 3.3. Dynamic Microsegmentation & Tenant Isolation
* **Risk-Aware Microsegmentation:** Automated Go controllers poll EPSS risk scores; if a workload's CVE score exceeds policy thresholds, Istio/Cilium CRDs dynamically restrict egress routes.
* **SDN Fabric Sync:** Kubernetes controllers watch Cilium identity endpoints and push Virtual Routing and Forwarding (VRF) and Endpoint Group (EPG) updates to physical network switches.
* **Multi-Tenancy & Identity Invalidation:** User authentication via JWTs (Keycloak/Dex mapped to OpenLDAP). Automated token invalidation flows track `kid` identifiers upon user logout or asynchronous batch job completion.

### 3.4. AI/ML Workload Governance
* Isolation and runtime security for dynamic inference pipelines and model serving endpoints.

### 3.5. Observability & Telemetry (MELT Stack)
* **Continuous Profiling:** Parca eBPF profiling (zero-code instrumentation).
* **Deep Flow Visibility:** Cilium Hubble and Pixie.dev.
* **CNCF Observability Engine:** Prometheus (Metrics), Grafana Loki (Logs), and Tempo (Traces).

### 3.6. Supply Chain Provenance & Runtime Security
* **Pre-Deployment (L7):** Sigstore (Cosign/Rekor) and Kyverno admission policies block unsigned OCI images before scheduling.
* **Runtime Defense (Kernel):** Tetragon eBPF policies enforce syscall lineage, file integrity monitoring, and container breakout prevention post-deployment.

### 3.7. Identity Management & PKI
* **Identity Providers (IdP):** Dex (lab/testing) and Keycloak (production) backed by in-cluster OpenLDAP and enterprise directory services.
* **Workload Identity:** SPIRE Server issuing cryptographically verified SPIFFE SVIDs over local Unix Domain Sockets (`spire-spiffe-csi-driver`).

---

## 4. Live Cluster System Architecture

```mermaid
graph TB
    subgraph External["External Services & Upstreams"]
        EPSS["FIRST.org EPSS API"]
        Sigstore["Sigstore / Rekor Log"]
        ExtLDAP["Production LDAP / Directory"]
    end

    subgraph Fabric["Physical Network Underlay"]
        ToR["Top-of-Rack Switches (ASIC / ACLs)"]
        APIC["Cisco APIC / SDN Controller"]
    end

    subgraph Cluster["Kubernetes Cluster (webrtc-app-cluster | v1.34.0)"]
        
        subgraph IdPSystem["Identity & Directory Layer"]
            DexKeycloak["Dex / Keycloak IdP"]
            OpenLDAP["In-Cluster OpenLDAP"]
        end

        subgraph ControlPlane["Control Plane Layer"]
            Istiod["Istiod (Istio Ambient Control)"]
            SpireServer["SPIRE Server (PKI & SVID Engine)"]
            WorkspaceController["Custom Workspace Go Controller"]
        end

        subgraph Node["Compute Nodes (Debian 12 | Kernel 6.3.13)"]
            
            subgraph KernelSpace["Linux Kernel (eBPF Datapath)"]
                TC["Traffic Control (tc) & XDP Hooks"]
                SockMap["Sockmap / sk_msg (Zero-Copy Bypass)"]
                WG["WireGuard (cilium_wg0 Encryption)"]
            end

            subgraph NodeDaemons["Node Security Daemons"]
                CiliumAgent["Cilium Agent"]
                Ztunnel["ztunnel (Rust L4 mTLS Daemon)"]
                SpireAgent["SPIRE Agent & SPIFFE CSI Driver"]
                Hubble["Cilium Hubble Relay & UI"]
            end

            subgraph WorkloadNS["Dynamic Tenant Namespace"]
                FastAPIApp["Workspace Service (FastAPI)"]
                PostgreSQL[("PostgreSQL DB")]
                WorkspaceCRD["Workspace CRD Object"]
                DynamicNSPod["Dynamically Provisioned Member Pod"]
            end
        end
    end

    %% Flow Relationships
    ExtLDAP <--> DexKeycloak
    DexKeycloak <--> OpenLDAP
    EPSS --> WorkspaceController
    
    FastAPIApp -->|1. Write State| PostgreSQL
    FastAPIApp -->|2. Create| WorkspaceCRD
    WorkspaceController -->|3. Watch CRD & Provision| DynamicNSPod
    
    SpireServer -->|Attestation| SpireAgent
    SpireAgent -->|Unix SDS / CSI| Ztunnel
    Istiod -->|xDS Push| Ztunnel
    
    FastAPIApp -->|Socket sendmsg| SockMap
    SockMap -->|Direct Buffer Copy| Ztunnel
    Ztunnel -->|WireGuard Encrypt| WG
    WG -->|Egress Packet| ToR
    
    APIC -.->|gNMI / RESTCONF| ToR
    Hubble -->|Flow Telemetry| UI["Hubble UI / Prometheus"]