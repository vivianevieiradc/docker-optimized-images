from fastapi import FastAPI

app = FastAPI(title="Example App")


@app.get("/health")
def health():
    return {"status": "ok"}


@app.get("/items")
def list_items():
    return [
        {"id": 1, "name": "Item A"},
        {"id": 2, "name": "Item B"},
    ]
