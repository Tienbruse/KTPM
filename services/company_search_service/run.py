import os
import sys

import uvicorn
from dotenv import load_dotenv

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
SRC_DIR = os.path.join(BASE_DIR, "src")
if SRC_DIR not in sys.path:
    sys.path.insert(0, SRC_DIR)

from company_search_service.config import get_settings

load_dotenv(os.path.join(BASE_DIR, ".env"))


def main() -> None:
    settings = get_settings()
    uvicorn.run(
        "company_search_service.app:app",
        host=settings.host,
        port=settings.port,
        reload=True,
        factory=False,
    )


if __name__ == "__main__":
    main()
