from fastapi import FastAPI

from .routers import (
    automation,
    mutation,
    token)


app = FastAPI()
app.include_router(automation.router)
app.include_router(mutation.router)
app.include_router(token.router)
