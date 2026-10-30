"""Bookshelf: a small HTTP API used as the system under test.

An in-memory collection of invented books. Reading is open; creating, updating
and deleting need the ``X-API-Key`` header to match the ``BOOKSHELF_API_KEY``
environment variable. Every record is invented, and ISBNs used by the tests are
synthetic (prefix 979-9) with valid check digits.

Run locally (the key is yours to choose, it protects nothing real)::

    BOOKSHELF_API_KEY=<any-local-value> uvicorn app:app --host 127.0.0.1 --port 8000
"""
from __future__ import annotations

import os
import secrets
import threading
from typing import Annotated, Any, Dict, List, Optional

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from isbn import is_valid_isbn13

YEAR_MIN, YEAR_MAX = 1450, 2100
LIMIT_MAX = 100
Tag = Annotated[str, Field(min_length=1, max_length=30)]


class ErrorMessage(BaseModel):
    detail: str


class BookFields(BaseModel):
    """Fields shared by create and update; unknown fields are rejected."""

    model_config = ConfigDict(extra="forbid")

    @field_validator("isbn", check_fields=False)
    @classmethod
    def _isbn_check_digit(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not is_valid_isbn13(value):
            raise ValueError("isbn must be 13 digits with a valid ISBN-13 check digit")
        return value

    @field_validator("title", "author", check_fields=False)
    @classmethod
    def _not_blank(cls, value: Optional[str]) -> Optional[str]:
        if value is not None and not value.strip():
            raise ValueError("must not be blank")
        return value


class BookCreate(BookFields):
    title: str = Field(min_length=1, max_length=200)
    author: str = Field(min_length=1, max_length=100)
    year: int = Field(ge=YEAR_MIN, le=YEAR_MAX)
    isbn: str = Field(pattern=r"^\d{13}$")
    tags: List[Tag] = Field(default_factory=list, max_length=10)


class BookUpdate(BookFields):
    title: Optional[str] = Field(default=None, min_length=1, max_length=200)
    author: Optional[str] = Field(default=None, min_length=1, max_length=100)
    year: Optional[int] = Field(default=None, ge=YEAR_MIN, le=YEAR_MAX)
    isbn: Optional[str] = Field(default=None, pattern=r"^\d{13}$")
    tags: Optional[List[Tag]] = Field(default=None, max_length=10)

    @model_validator(mode="before")
    @classmethod
    def _no_nulls(cls, values: Any) -> Any:
        # A field may be left out of an update, but not set to null.
        if isinstance(values, dict):
            nulls = sorted(k for k, v in values.items() if v is None)
            if nulls:
                raise ValueError(f"fields cannot be null: {', '.join(nulls)}")
        return values


class Book(BaseModel):
    id: int
    title: str
    author: str
    year: int
    isbn: str
    tags: List[str]


class BookPage(BaseModel):
    items: List[Book]
    total: int
    limit: int
    offset: int


class Health(BaseModel):
    status: str


class Store:
    """Thread-safe in-memory storage. Ids start at 1 and are never reused."""

    def __init__(self) -> None:
        self._books: Dict[int, Book] = {}
        self._next_id = 1
        self._lock = threading.Lock()

    def list(self) -> List[Book]:
        with self._lock:
            return list(self._books.values())

    def get(self, book_id: int) -> Optional[Book]:
        with self._lock:
            return self._books.get(book_id)

    def _isbn_taken(self, isbn: str, except_id: Optional[int] = None) -> bool:
        return any(b.isbn == isbn and b.id != except_id for b in self._books.values())

    def create(self, data: BookCreate) -> Optional[Book]:
        with self._lock:
            if self._isbn_taken(data.isbn):
                return None
            book = Book(id=self._next_id, **data.model_dump())
            self._books[book.id] = book
            self._next_id += 1
            return book

    def update(self, book_id: int, data: BookUpdate) -> Optional[Book]:
        """Returns the updated book; raises KeyError (unknown id) or ValueError (ISBN taken)."""
        with self._lock:
            current = self._books[book_id]
            changes = data.model_dump(exclude_unset=True)
            if "isbn" in changes and self._isbn_taken(changes["isbn"], except_id=book_id):
                raise ValueError("isbn taken")
            book = current.model_copy(update=changes)
            self._books[book_id] = book
            return book

    def delete(self, book_id: int) -> bool:
        with self._lock:
            return self._books.pop(book_id, None) is not None


store = Store()
api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False,
                              description="Must match the BOOKSHELF_API_KEY environment variable of the service")


def require_api_key(key: Optional[str] = Depends(api_key_header)) -> None:
    expected = os.environ.get("BOOKSHELF_API_KEY", "")
    if not expected or not key or not secrets.compare_digest(key.encode(), expected.encode()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, detail="missing or wrong API key")


app = FastAPI(
    title="Bookshelf",
    version="1.0.0",
    description="A small in-memory book collection used as the system under test. All records are invented.",
)

NOT_FOUND = {404: {"model": ErrorMessage, "description": "No book with this id"}}
UNAUTHORIZED = {401: {"model": ErrorMessage, "description": "Missing or wrong API key"}}
CONFLICT = {409: {"model": ErrorMessage, "description": "Another book already has this ISBN"}}


@app.get("/health", response_model=Health, tags=["service"])
def health() -> Health:
    return Health(status="ok")


@app.get("/books", response_model=BookPage, tags=["books"])
def list_books(
    limit: int = Query(20, ge=1, le=LIMIT_MAX, description="Page size"),
    offset: int = Query(0, ge=0, description="Number of books to skip"),
    author: Optional[str] = Query(None, description="Exact author match"),
    tag: Optional[str] = Query(None, description="Books carrying this tag"),
) -> BookPage:
    books = sorted(store.list(), key=lambda b: b.id)
    if author is not None:
        books = [b for b in books if b.author == author]
    if tag is not None:
        books = [b for b in books if tag in b.tags]
    return BookPage(items=books[offset:offset + limit], total=len(books), limit=limit, offset=offset)


@app.get("/books/{book_id}", response_model=Book, responses=NOT_FOUND, tags=["books"])
def get_book(book_id: int) -> Book:
    book = store.get(book_id)
    if book is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"no book with id {book_id}")
    return book


@app.post("/books", response_model=Book, status_code=status.HTTP_201_CREATED,
          responses={**UNAUTHORIZED, **CONFLICT}, dependencies=[Depends(require_api_key)], tags=["books"])
def create_book(data: BookCreate, response: Response) -> Book:
    book = store.create(data)
    if book is None:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"isbn {data.isbn} already exists")
    response.headers["Location"] = f"/books/{book.id}"
    return book


@app.patch("/books/{book_id}", response_model=Book, responses={**UNAUTHORIZED, **NOT_FOUND, **CONFLICT},
           dependencies=[Depends(require_api_key)], tags=["books"])
def update_book(book_id: int, data: BookUpdate) -> Book:
    try:
        return store.update(book_id, data)
    except KeyError:
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"no book with id {book_id}") from None
    except ValueError:
        raise HTTPException(status.HTTP_409_CONFLICT, detail=f"isbn {data.isbn} already exists") from None


@app.delete("/books/{book_id}", status_code=status.HTTP_204_NO_CONTENT, responses={**UNAUTHORIZED, **NOT_FOUND},
            dependencies=[Depends(require_api_key)], tags=["books"])
def delete_book(book_id: int) -> Response:
    if not store.delete(book_id):
        raise HTTPException(status.HTTP_404_NOT_FOUND, detail=f"no book with id {book_id}")
    return Response(status_code=status.HTTP_204_NO_CONTENT)
