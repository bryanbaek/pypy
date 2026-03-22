"""FastAPI application entrypoint for local and containerized runs."""

from fastapi import FastAPI


def create_app() -> FastAPI:
    """Create the FastAPI application used by local workflows."""
    application = FastAPI(
        title="FastAPI Template",
        description="Local entrypoint for the reusable FastAPI template.",
    )

    @application.get("/")
    async def read_root() -> dict[str, str]:
        """Return a minimal landing payload for the template app."""
        return {"message": "Welcome to the FastAPI template"}

    @application.get("/health")
    async def read_health() -> dict[str, str]:
        """Return the process health status."""
        return {"status": "ok"}

    return application


app = create_app()


__all__ = ["app", "create_app"]
