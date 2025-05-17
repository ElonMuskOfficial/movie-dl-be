from fastapi import FastAPI
from fastapi.responses import JSONResponse
from server import fetch_download_server
from fastapi import Query

app = FastAPI()

@app.get("/")
def read_root():
    return {"Hello": "World"}

@app.get("/fetch")
def fetch_url(url: str = Query(..., description="The vcloud.lol URL to fetch")):
    result = fetch_download_server(url)
    return JSONResponse(content=result)