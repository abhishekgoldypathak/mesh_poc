import asyncio
import logging
import uuid
from typing import List
from fastapi import FastAPI, HTTPException, Depends, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import engine, Base, get_db
from app.models import Workspace
from app.schema import WorkspaceCreate, WorkspaceResponse

app = FastAPI(title="Business Workspace API", version="1.0.0")

@app.on_event("startup")
async def startup():
    retries = 10
    while retries > 0:
        try:
            async with engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            logging.info("Successfully connected to PostgreSQL database.")
            break
        except Exception as e:
            retries -= 1
            logging.warning(f"Database connection failed. Retrying in 3s... ({retries} attempts left): {e}")
            await asyncio.sleep(3)

@app.get("/healthz")
async def healthz():
    return {"status": "ok"}

@app.post("/api/v1/workspaces", response_model=WorkspaceResponse, status_code=status.HTTP_201_CREATED)
async def create_workspace(payload: WorkspaceCreate, db: AsyncSession = Depends(get_db)):
    stmt = select(Workspace).where(Workspace.name == payload.name)
    existing = (await db.execute(stmt)).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=400, detail="Workspace name already exists")

    ws_id = f"ws-{uuid.uuid4().hex[:8]}"
    tenant_ns = f"memgraph-{ws_id}"

    workspace = Workspace(
        id=ws_id,
        name=payload.name,
        status="PROVISIONING",
        namespace=tenant_ns
    )
    db.add(workspace)
    await db.commit()
    await db.refresh(workspace)
    return workspace

@app.get("/api/v1/workspaces", response_model=List[WorkspaceResponse])
async def list_workspaces(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Workspace))
    return result.scalars().all()