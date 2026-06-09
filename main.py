from fastapi import FastAPI
from fastapi.openapi.utils import get_openapi
from fastapi.middleware.cors import CORSMiddleware
from app.routes import authr, shipmentr, contact, vehicler, router, userr, notificationsr
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse
from fastapi import Request
from starlette.exceptions import HTTPException as StarletteHTTPException
from fastapi.responses import FileResponse
import os

app = FastAPI()

app.include_router(authr.router)
app.include_router(userr.router)
app.include_router(shipmentr.router)
app.include_router(contact.router)
app.include_router(vehicler.router)
app.include_router(router.router)
app.include_router(notificationsr.router)

app.add_middleware(
    CORSMiddleware,
    allow_origins = ["http://localhost:8000"], 
    allow_credentials = True,
    allow_methods = ["*"],
    allow_headers = ["*"],
)

@app.exception_handler(404) # runs before sending a 404 response
async def custom_404_handler(request : Request, exc) :
    api_prefixes = ("/auth", "/user", "/shipment", "/contact", "/vehicle", "/router", "/notifications", "/api")
    if request.method == "GET" and not request.url.path.startswith(api_prefixes) :
        index_path = os.path.join("static", "index.html")
        if os.path.exists(index_path) :
            return FileResponse(index_path)
    return JSONResponse(status_code = 404, content = {"detail" : "not found"})

app.mount("/", StaticFiles(directory = "static", html = True), name = "static")
