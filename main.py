from fastapi import FastAPI
from fastapi.responses import JSONResponse, HTMLResponse
from server import fetch_download_server
from fastapi import Query
import os

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/fetch")
def fetch_url(url: str = Query(..., description="The vcloud.lol URL to fetch")):
    result = fetch_download_server(url)
    return JSONResponse(content=result)

@app.get("/view-response1")
def view_response1():
    filename = "response1.html"
    if not os.path.exists(filename):
        return JSONResponse(content={"error": f"File {filename} not found"}, status_code=404)
    with open(filename, 'r', encoding='utf-8') as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)

@app.get("/view-response2")
def view_response2():
    filename = "response2.html"
    if not os.path.exists(filename):
        return JSONResponse(content={"error": f"File {filename} not found"}, status_code=404)
    with open(filename, 'r', encoding='utf-8') as f:
        html_content = f.read()
    return HTMLResponse(content=html_content)