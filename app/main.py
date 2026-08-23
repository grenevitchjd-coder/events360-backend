from fastapi import FastAPI

from app.routers import organizations, auth, admin, events, roles, staff_assignments, platform_admins

app = FastAPI(
    title="Events360",
    description="Central admin/control plane for the FashioNXT suite (EventNXT, CastNXT, PlaNXT).",
    version="0.1.0",
)

app.include_router(organizations.router)
app.include_router(auth.router)
app.include_router(admin.router)
app.include_router(events.router)
app.include_router(roles.router)
app.include_router(staff_assignments.router)
app.include_router(platform_admins.router)


@app.get("/health")
def health_check():
    return {"status": "ok"}