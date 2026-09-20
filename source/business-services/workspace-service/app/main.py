import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from kubernetes import client, config

app = FastAPI(title="Workspace Orchestrator API", version="v6.0")

if os.getenv("KUBERNETES_SERVICE_HOST"):
    config.load_incluster_config()
else:
    config.load_kube_config()

api_instance = client.CustomObjectsApi()

GROUP = "platform.ebpf.io"
VERSION = "v1alpha1"
NAMESPACE = "business-app"
PLURAL = "workspaces"

class WorkspaceCreate(BaseModel):
    name: str
    tenant_name: str = "default-tenant"
    memgraph_version: str = "latest"

@app.post("/workspaces")
def create_workspace(body: WorkspaceCreate):
    tenant = body.tenant_name if body.tenant_name and body.tenant_name != "string" else body.name
    cr = {
        "apiVersion": f"{GROUP}/{VERSION}",
        "kind": "Workspace",
        "metadata": {
            "name": body.name,
            "namespace": NAMESPACE
        },
        "spec": {
            "tenantName": tenant,
            "storageSize": "100Mi",
            "memgraphVersion": body.memgraph_version
        }
    }
    try:
        resp = api_instance.create_namespaced_custom_object(
            group=GROUP,
            version=VERSION,
            namespace=NAMESPACE,
            plural=PLURAL,
            body=cr
        )
        return {"status": "success", "data": resp}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/workspaces/{name}")
def delete_workspace(name: str):
    try:
        resp = api_instance.delete_namespaced_custom_object(
            group=GROUP,
            version=VERSION,
            namespace=NAMESPACE,
            plural=PLURAL,
            name=name
        )
        return {"status": "deleted", "data": resp}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
def health():
    return {"status": "healthy"}