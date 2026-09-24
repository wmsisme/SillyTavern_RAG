from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    from backend.config import CHROMA_DIR, COLLECTION_NAME, DOCS_REPO_DIR
    import chromadb
    import subprocess

    try:
        client = chromadb.PersistentClient(path=str(CHROMA_DIR))
        collection = client.get_collection(COLLECTION_NAME)
        chroma_count = collection.count()
    except Exception:
        chroma_count = 0

    commit_hash = ""
    try:
        r = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            capture_output=True, text=True, timeout=10,
            cwd=str(DOCS_REPO_DIR),
        )
        if r.returncode == 0:
            commit_hash = r.stdout.strip()[:8]
    except Exception:
        pass

    return {
        "status": "ok",
        "chroma_count": chroma_count,
        "commit_hash": commit_hash,
    }
