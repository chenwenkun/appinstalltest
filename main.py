from fastapi import FastAPI, UploadFile, File, HTTPException, Form, Body, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
import uvicorn
import os
from device_manager import DeviceManager
from apk_manager import ApkManager
from test_runner import TestRunner

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory="static"), name="static")

# Mount uploads directory to serve APKs
os.makedirs("uploads", exist_ok=True)
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")

from fastapi.responses import RedirectResponse

# Initialize managers
device_manager = DeviceManager()
apk_manager = ApkManager("apks")
test_runner = TestRunner(device_manager)

@app.get("/")
async def root():
    return RedirectResponse(url="/static/index.html")



@app.get("/devices")
def get_devices():
    return device_manager.list_devices()

@app.get("/apks")
def get_apks():
    return apk_manager.list_apks()

@app.post("/upload")
async def upload_apk(file: UploadFile = File(...), custom_name: str = Form(None)):
    return await apk_manager.save_apk(file, custom_name)

@app.delete("/apks/{filename}")
def delete_apk(filename: str):
    return apk_manager.delete_apk(filename)

@app.post("/install_old")
async def install_old(
    request: Request,
    item: dict = Body(...)
):
    device_serial = item.get("device_serial")
    old_apk_name = item.get("old_apk_name")
    apk_url = item.get("apk_url") # Support remote URL
    
    if not device_serial:
        return {"status": "error", "message": "Missing device_serial"}
    if not old_apk_name and not apk_url:
        return {"status": "error", "message": "Missing old_apk_name or apk_url"}

    return await test_runner.install_old_apk(device_serial, old_apk_name, apk_url)

@app.post("/install_new")
async def install_new(
    request: Request,
    item: dict = Body(...)
):
    device_serial = item.get("device_serial")
    new_apk_name = item.get("new_apk_name")
    apk_url = item.get("apk_url") # Support remote URL
    package_name = item.get("package_name")

    if not device_serial:
        return {"status": "error", "message": "Missing device_serial"}
    if not new_apk_name and not apk_url:
        return {"status": "error", "message": "Missing new_apk_name or apk_url"}
    if not package_name:
         return {"status": "error", "message": "Missing package_name"}

    return await test_runner.install_new_apk(device_serial, new_apk_name, package_name, apk_url)

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8791)
