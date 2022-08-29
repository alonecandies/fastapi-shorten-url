from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import RedirectResponse
from starlette.datastructures import URL
from sqlalchemy.orm import Session

import validators

from schemas.url_schema import URLBase, URLInfo
from models.url_model import URL as URLModel
from configs.env import get_settings
from configs.db import SessionLocal, engine
from configs.constant import INVALID_URL_MSG
from utils.crud import create_db_url, deactivate_db_url_by_secret_key, get_db_url_by_key, get_db_url_by_secret_key, update_db_clicks


def raise_bad_request(message):
    raise HTTPException(status_code=400, detail=message)


def raise_not_found(request):
    message = f"URL '{request.url}' doesn't exist"
    raise HTTPException(status_code=404, detail=message)


def get_admin_info(db_url: URLModel) -> URLInfo:
    base_url = URL(get_settings().base_url)
    admin_endpoint = app.url_path_for(
        "administration info", secret_key=db_url.secret_key
    )
    db_url.url = str(base_url.replace(path=db_url.key))
    db_url.admin_url = str(base_url.replace(path=admin_endpoint))
    return db_url


app = FastAPI()

URLModel.metadata.create_all(bind=engine)


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.post("/url", response_model=URLInfo, name="Create URL", tags=["URL Client"])
def create_url(url: URLBase, db: Session = Depends(get_db)):
    if not validators.url(url.target_url):
        raise_bad_request(message=INVALID_URL_MSG)

    db_url = create_db_url(db=db, url=url)
    return get_admin_info(db_url)


@app.get("/{url_key}", name="Redirect to URL", tags=["URL Client"])
def forward_to_target_url(
    url_key: str,
    request: Request,
    db: Session = Depends(get_db)
):
    db_url = (
        db.query(URLModel)
        .filter(URLModel.key == url_key, URLModel.is_active)
        .first()
    )
    if db_url := get_db_url_by_key(db=db, url_key=url_key):
        update_db_clicks(db=db, db_url=db_url)
        return RedirectResponse(db_url.target_url)
    else:
        raise_not_found(request)


@app.get(
    "/admin/{secret_key}",
    name="URL Info",
    response_model=URLInfo,
    tags=["URL Admin"]
)
def get_url_info(
    secret_key: str, request: Request, db: Session = Depends(get_db)
):
    if db_url := get_db_url_by_secret_key(db, secret_key=secret_key):
        return get_admin_info(db_url)
    else:
        raise_not_found(request)


@app.delete("/admin/{secret_key}", name="Deactivate URL", tags=["URL Admin"])
def delete_url(
    secret_key: str, request: Request, db: Session = Depends(get_db)
):
    if db_url := deactivate_db_url_by_secret_key(db, secret_key=secret_key):
        message = f"Successfully deleted shortened URL for '{db_url.target_url}'"
        return {"detail": message}
    else:
        raise_not_found(request)
