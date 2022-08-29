from models.url_model import URL as URLModel
from schemas.url_schema import URLBase, URL as URLSchema
from .keygen import create_random_key, create_unique_random_key
from sqlalchemy.orm import Session
import sys
sys.path.append("..")


def get_db_url_by_key(db: Session, url_key: str) -> URLModel:
    return (
        db.query(URLModel)
        .filter(URLModel.key == url_key, URLModel.is_active)
        .first()
    )


def create_db_url(db: Session, url: URLBase) -> URLModel:
    key = create_unique_random_key(db)
    secret_key = f"{key}_{create_random_key(length=8)}"
    db_url = URLModel(
        target_url=url.target_url, key=key, secret_key=secret_key
    )
    db.add(db_url)
    db.commit()
    db.refresh(db_url)
    return db_url


def get_db_url_by_secret_key(db: Session, secret_key: str) -> URLModel:
    return (
        db.query(URLModel)
        .filter(URLModel.secret_key == secret_key, URLModel.is_active)
        .first()
    )


def update_db_clicks(db: Session, db_url: URLSchema) -> URLModel:
    db_url.clicks += 1
    db.commit()
    db.refresh(db_url)
    return db_url


def deactivate_db_url_by_secret_key(db: Session, secret_key: str) -> URLModel:
    db_url = get_db_url_by_secret_key(db, secret_key)
    if db_url:
        db_url.is_active = False
        db.commit()
        db.refresh(db_url)
    return db_url
