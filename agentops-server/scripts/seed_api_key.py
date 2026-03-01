from __future__ import annotations

import argparse

from sqlalchemy import select

from app.core.auth import hash_api_key
from app.core.db import SessionLocal, init_db
from app.models.tables import ApiKey, Project


def main() -> None:
    parser = argparse.ArgumentParser(description="Create or update a project and API key for local testing.")
    parser.add_argument("--project-id", default="proj_demo")
    parser.add_argument("--project-name", default="Demo Project")
    parser.add_argument("--api-key", default="dev-agentops-key")
    parser.add_argument("--key-name", default="local-dev")
    args = parser.parse_args()

    init_db()

    db = SessionLocal()
    try:
        project = db.get(Project, args.project_id)
        if project is None:
            project = Project(id=args.project_id, name=args.project_name)
            db.add(project)

        key_hash = hash_api_key(args.api_key)
        api_key = db.scalar(select(ApiKey).where(ApiKey.key_hash == key_hash))
        if api_key is None:
            api_key = ApiKey(project_id=project.id, key_hash=key_hash, name=args.key_name)
            db.add(api_key)

        db.commit()

        print(f"project_id={project.id}")
        print(f"api_key={args.api_key}")
        print("status=ready")
    finally:
        db.close()


if __name__ == "__main__":
    main()
