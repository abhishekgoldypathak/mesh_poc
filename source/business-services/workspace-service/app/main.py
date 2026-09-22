import os
from typing import Optional
from fastapi import FastAPI, HTTPException, status
from pydantic import BaseModel
from kubernetes import client, config

app = FastAPI(
    title="Workspace Orchestrator API",
    version="v6.0.0",
    docs_url="/docs",
    openapi_url="/openapi.json"
)

# In-cluster vs local Kubeconfig loading
if os.getenv("KUBERNETES_SERVICE_HOST"):
    config.load_incluster_config()
else:
    config.load_kube_config()

api_instance = client.CustomObjectsApi()

GROUP = "platform.ebpf.io"
VERSION = "v1alpha1"
NAMESPACE = os.getenv("WORKSPACE_NAMESPACE", "business-app")
PLURAL = "workspaces"

class WorkspaceCreate(BaseModel):
    name: str
    tenant_name: str = "default-tenant"
    memgraph_version: str = "latest"

@app.post("/workspaces", status_code=status.HTTP_201_CREATED)
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

@app.get("/workspaces")
def list_workspaces():
    try:
        resp = api_instance.list_namespaced_custom_object(
            group=GROUP,
            version=VERSION,
            namespace=NAMESPACE,
            plural=PLURAL
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