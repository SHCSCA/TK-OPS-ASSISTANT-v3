from __future__ import annotations

import uvicorn

from app.factory import create_app

app = create_app()


def main() -> None:
    uvicorn.run(
        "main:app",
        host="127.0.0.1",
        port=8000,
        reload=True,
    )


if __name__ == "__main__":
    main()
