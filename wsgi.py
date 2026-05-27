import logging
import os

from app import create_app

app = create_app()

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    logging.info(f"Starting server, version {os.getenv('GIT_COMMIT', 'unknown')}")
    app.run(host="0.0.0.0")
