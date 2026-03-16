"""CLI entry point for the OpenMedicine HTTP service."""
import uvicorn

from open_medicine.server.config import ServiceConfig


def main() -> None:
    config = ServiceConfig()
    uvicorn.run(
        "open_medicine.server.app:create_app",
        factory=True,
        host=config.host,
        port=config.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
