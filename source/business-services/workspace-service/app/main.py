import asyncio
import logging
import uuid
from typing import List
from fastapi import FastAPI, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from kubernetes_asyncio import client, config
from kubernetes_asyncio.client.rest import ApiException

from app.database import engine, Base, get_db
from app.models import Workspace
from app.schema import WorkspaceCreate, WorkspaceResponse

app = FastAPI(title="Business Workspace API", version="1.0.0")

# Initialize K8s client on startup
@app.on_event("startup")
async def startup():
    # Load in-cluster config (or fallback to kubeconfig for local dev)
    try:
        config.load_incluster_config()
    except Exception:
        await config.load_kube_config()

    # DB readiness check
    retries = 10
    while retries > 0:
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            break
        except Exception as e:
            retries -= 1
            await asyncio.sleep(2)

@app.post("/api/v1/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(payload: WorkspaceCreate, db: AsyncSession = Depends(get_db)):
    # 1. DB Duplicate Check
    stmt = select(Workspace).where(Workspace.name == payload.name)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Workspace name already exists")

    ws_id = f"ws-{uuid.uuid4().hex[:8]}"
    tenant_ns = f"memgraph-{ws_id}"

    # 2. Persist to Postgres
    workspace = Workspace(
        id=ws_id,
        name=payload.name,
        status="PROVISIONING",
        namespace=tenant_ns
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)

    # 3. Create Custom Resource in Kubernetes
    cr_manifest = {
        "apiVersion": "platform.ebpf.io/v1alpha1",
        "kind": "Workspace",
        "metadata": {
            "name": ws_id,
            "namespace": "business-app"
        },
        "spec": {
            "workspaceId": ws_id,
            "tenantName": payload.name,
            "memgraphVersion": "2.14"
        }
    }

    try:
        async with client.ApiClient() as api_client:
            custom_api = client.CustomObjectsApi(api_client)
            await custom_api.create_namespaced_custom_object(
                group="platform.ebpf.io",
                version="v1alpha1",
                namespace="business-app",
                plural="workspaces",
                body=cr_manifest
            )
    except ApiException as e:
        logging.error(f"Failed to emit Workspace CRD: {e}")
        # Rollback or log error based on requirements
        raise HTTPException(
            status_code=500, 
            detail=f"Database record created, but K8s CRD creation failed: {e.reason}"
        )

    return workspace