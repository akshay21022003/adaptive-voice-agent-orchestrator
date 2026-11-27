# Database Query Guide (SQLAlchemy 2.0)

A generic, reusable reference for writing database code with SQLAlchemy 2.0: CRUD,
querying, filtering, joins across multiple tables, relationships, and transactions.

All examples use the modern 2.0 style (`select()` + `Session.scalars()` /
`Session.execute()`). The model names below (`User`, `Post`, `Comment`, `Tag`, …) are
illustrative placeholders — swap in whatever entities your feature needs.

---

## 1. Mental model: how the pieces fit

```
API / caller  →  Repository  →  Session  →  Database
                 stages work    unit of    (Postgres/SQLite/…)
                 (add/flush)    work +
                                commit
```

- **Engine** — the connection pool to your database. Created once at startup.
- **Session** — a workspace for one unit of work. It tracks the objects you load/create
  and the pending changes, then flushes them as SQL.
- **Repository** — a thin class that owns queries for one entity. Keeps SQL out of your
  handlers/services.

A common, clean convention (recommended):

> **Repositories only stage work** (`add`, `flush`, `delete`, run queries). **One commit
> per request/unit of work**, owned by whoever created the session — not scattered inside
> repositories. This keeps all the writes in a request atomic.

```python
# A request-scoped session that commits once at the end.
def get_db():
    db = SessionLocal()
    try:
        yield db
        db.commit()        # commit once on success
    except Exception:
        db.rollback()      # undo everything on failure
        raise
    finally:
        db.close()
```

### `flush()` vs `commit()` (the #1 thing people get stuck on)

| Operation  | What it does                                                        | Permanent? |
| ---------- | ------------------------------------------------------------------ | ---------- |
| `flush()`  | Emits pending INSERT/UPDATE/DELETE **within the current transaction**. Makes DB-generated values (autoincrement ids, defaults) available. | No — still inside the transaction |
| `commit()` | Ends the transaction and makes everything permanent. Implies a flush first. | Yes |
| `rollback()` | Discards all pending changes since the last commit.              | —          |

Rule of thumb: call `flush()` when you need the inserted row's id *before* the request
ends; let the single `commit()` finalize everything.

---

## 2. Defining models (so examples make sense)

Modern 2.0 declarative style with typed columns:

```python
from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import ForeignKey, String, Text, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())

    # Optional ORM relationship (see §6). Lets you do user.posts instead of a manual join.
    posts: Mapped[list["Post"]] = relationship(back_populates="author")


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    author_id: Mapped[UUID] = mapped_column(ForeignKey("users.id"), index=True)
    title: Mapped[str] = mapped_column(String(200))
    body: Mapped[str] = mapped_column(Text)

    author: Mapped["User"] = relationship(back_populates="posts")
```

**Column tips you'll reuse:**
- `nullable=False` is the default for a non-`Optional` type; use `Mapped[str | None]` for
  nullable columns.
- `index=True` on columns you filter/join on often (especially foreign keys).
- `unique=True` for natural keys (emails, slugs, external ids).
- `default=` runs in Python; `server_default=` runs in the database.
- `onupdate=func.now()` for an auto-updating `updated_at`.

---

## 3. CRUD — the core four

```python
from sqlalchemy import select
from sqlalchemy.orm import Session
```

### Create

Use ORM `add()` + `flush()`. This inserts **and** gives you back a live, populated object
(with its generated id). Prefer this over the Core `insert()` statement, which is meant
for bulk/batch inserts and does not return a managed ORM instance.

```python
def create_user(db: Session, name: str) -> User:
    user = User(name=name)
    db.add(user)
    db.flush()          # INSERT now; user.id is populated
    return user
```

### Read one — by primary key

`get()` is the fast path for PK lookups; it can serve the object from the session's
identity map without hitting the DB again.

```python
def get_user(db: Session, user_id: UUID) -> User | None:
    return db.get(User, user_id)
```

### Read many

```python
def list_users(db: Session) -> list[User]:
    return list(db.scalars(select(User)).all())
```

### Update

Load → mutate attributes → flush. SQLAlchemy's change tracking emits the UPDATE.

```python
def rename_user(db: Session, user_id: UUID, name: str) -> User | None:
    user = db.get(User, user_id)
    if user is None:
        return None
    user.name = name
    db.flush()
    return user
```

### Delete

```python
def delete_user(db: Session, user_id: UUID) -> bool:
    user = db.get(User, user_id)
    if user is None:
        return False
    db.delete(user)
    db.flush()
    return True
```

---

## 4. Querying patterns

```python
from sqlalchemy import select, func, or_, and_, not_, desc
```

### Objects vs scalars vs rows

```python
# Full ORM objects (most common)
users = db.scalars(select(User)).all()

# One object or None
user = db.scalars(select(User).where(User.name == "Alice")).first()

# Exactly one — raises if 0 or >1 (great for unique columns)
user = db.scalars(select(User).where(User.id == uid)).one()
# .one_or_none() → returns None instead of raising when there are 0 rows

# Specific columns → Row tuples, not model objects
rows = db.execute(select(User.id, User.name)).all()
for user_id, name in rows:
    ...
```

### Filtering (`where`)

```python
# Equality
select(Post).where(Post.title == "Hello")

# AND — comma-separate, chain .where(), or use and_()
select(Post).where(Post.author_id == uid, Post.title == "Hello")

# OR / NOT
select(Post).where(or_(Post.title == "A", Post.title == "B"))
select(Post).where(not_(Post.title == "Draft"))

# IN / NOT IN
select(Post).where(Post.title.in_(["A", "B"]))
select(Post).where(Post.title.not_in(["A", "B"]))

# NULL
select(User).where(User.name.is_(None))
select(User).where(User.name.is_not(None))

# Pattern match (ilike = case-insensitive on Postgres)
select(Post).where(Post.title.ilike("%python%"))

# Comparisons / ranges
select(Post).where(Post.created_at >= some_date)
select(Post).where(Post.score.between(1, 10))
```

### Ordering, limit, offset (pagination)

```python
select(Post).order_by(Post.created_at.desc())
select(Post).order_by(desc(Post.created_at)).limit(20).offset(40)  # page 3, size 20
```

### Aggregates & grouping

```python
# Count all
total = db.scalar(select(func.count()).select_from(User))

# Count with filter
n = db.scalar(select(func.count()).select_from(Post).where(Post.author_id == uid))

# Group by with a label
rows = db.execute(
    select(Post.author_id, func.count().label("n"))
    .group_by(Post.author_id)
    .having(func.count() > 5)        # filter groups
).all()
```

### Distinct

```python
db.scalars(select(Post.title).distinct()).all()
```

---

## 5. Working across tables (2nd, 3rd, Nth table)

This is where people get stuck. There are two situations:

### A) Query a child by its parent's id — **no join needed**

The foreign key lives on the child, so it's just a `where`:

```python
# All posts by a user
def posts_by_user(db: Session, user_id: UUID) -> list[Post]:
    return list(db.scalars(select(Post).where(Post.author_id == user_id)).all())
```

### B) Filter a parent by a child's columns — **use JOIN**

```python
# Users who have at least one post titled "Hello"
users = db.scalars(
    select(User)
    .join(Post, Post.author_id == User.id)
    .where(Post.title == "Hello")
    .distinct()
).all()
```

`join(TargetTable, ON condition)`. If there's exactly one FK between the tables you can
drop the condition (`select(User).join(Post)`), but being explicit is safer as schemas
grow.

### C) Three (or more) tables — chain `.join()`

Imagine `User → Post → Comment` (a comment belongs to a post, a post belongs to a user):

```python
# Every comment on any post written by a given user
comments = db.scalars(
    select(Comment)
    .join(Post, Comment.post_id == Post.id)
    .join(User, Post.author_id == User.id)
    .where(User.id == user_id)
    .order_by(Comment.created_at.asc())
).all()
```

### D) Pull columns from several tables at once

Use `execute()` and read Row tuples when you select a mix of columns/aggregates:

```python
rows = db.execute(
    select(User.name, func.count(Post.id).label("post_count"))
    .join(Post, Post.author_id == User.id)
    .group_by(User.name)
).all()
for name, post_count in rows:
    ...
```

### Join types

| Type        | How                                               | Keeps rows with no match? |
| ----------- | ------------------------------------------------- | ------------------------- |
| Inner (default) | `.join(Post, ...)`                            | No                        |
| Left outer  | `.outerjoin(Post, ...)` or `.join(Post, ..., isouter=True)` | Yes (NULLs for missing side) |

### Creating related rows (order matters)

The parent must exist before a child's FK can reference it:

```python
user = create_user(db, name="Alice")          # flush → user.id exists
post = Post(author_id=user.id, title="Hi", body="…")
db.add(post)
db.flush()                                     # post.id exists
comment = Comment(post_id=post.id, body="nice")
db.add(comment)
# one commit at request end makes all three atomic
```

---

## 6. Relationships (optional but powerful)

If you declare `relationship()` on your models (as in §2), you can navigate objects
instead of writing joins by hand:

```python
user = db.get(User, user_id)
for post in user.posts:        # lazy-loads posts for this user
    print(post.title)

post = db.get(Post, post_id)
print(post.author.name)        # navigate the other way
```

### The N+1 problem (and the fix)

Lazy loading inside a loop fires one query per row — slow. Eager-load instead:

```python
from sqlalchemy.orm import selectinload, joinedload

# One extra query loads ALL posts for the matched users (good for collections)
users = db.scalars(
    select(User).options(selectinload(User.posts))
).all()

# Single JOINed query (good for many-to-one, e.g. post.author)
posts = db.scalars(
    select(Post).options(joinedload(Post.author))
).all()
```

Rule of thumb: `selectinload` for one-to-many collections, `joinedload` for many-to-one
single references.

### Cascades

To delete children automatically when a parent is deleted, configure the relationship:

```python
posts: Mapped[list["Post"]] = relationship(
    back_populates="author",
    cascade="all, delete-orphan",
)
```

Without a cascade (or a DB-level `ON DELETE`), deleting a parent that still has children
raises a foreign-key error.

---

## 7. Bulk operations (when you're updating/deleting many rows)

For loading-then-mutating one object, use the ORM pattern in §3. For changing *many* rows
without loading them, use statement-level update/delete:

```python
from sqlalchemy import update, delete

# UPDATE posts SET title='Archived' WHERE author_id = :uid
db.execute(
    update(Post).where(Post.author_id == uid).values(title="Archived")
)

# DELETE FROM posts WHERE author_id = :uid
db.execute(delete(Post).where(Post.author_id == uid))
```

And `insert()` for true bulk inserts (fast, but returns no ORM objects):

```python
from sqlalchemy import insert
db.execute(insert(Post), [
    {"author_id": uid, "title": "A", "body": "…"},
    {"author_id": uid, "title": "B", "body": "…"},
])
```

Caveat: bulk statements bypass ORM in-memory change tracking. If you've already loaded
objects in the same session, prefer the ORM pattern or re-fetch afterward.

---

## 8. Transactions beyond a single request

Most of the time the single commit in `get_db()` is all you need. For explicit control:

```python
# Explicit transaction block (commits on success, rolls back on exception)
with db.begin():
    db.add(a)
    db.add(b)

# Nested savepoint — partial rollback without losing the outer transaction
with db.begin_nested():
    db.add(risky)
```

---

## 9. The repository + interface pattern

Keep queries behind a small class per entity, and depend on an interface so you can swap
implementations (e.g. a fake in tests):

```python
from abc import ABC, abstractmethod


class IUserRepository(ABC):
    @abstractmethod
    def create(self, name: str) -> User: ...
    @abstractmethod
    def get_by_id(self, user_id: UUID) -> User | None: ...
    @abstractmethod
    def list_all(self) -> list[User]: ...
    @abstractmethod
    def delete(self, user_id: UUID) -> bool: ...


class UserRepository(IUserRepository):
    def __init__(self, db: Session):
        self.db = db

    def create(self, name: str) -> User:
        user = User(name=name)
        self.db.add(user)
        self.db.flush()
        return user

    def get_by_id(self, user_id: UUID) -> User | None:
        return self.db.get(User, user_id)

    def list_all(self) -> list[User]:
        return list(self.db.scalars(select(User)).all())

    def delete(self, user_id: UUID) -> bool:
        obj = self.db.get(User, user_id)
        if obj is None:
            return False
        self.db.delete(obj)
        self.db.flush()
        return True
```

To add a repository for any new table, copy this shape: constructor takes `db: Session`,
methods use `add`/`flush`/`get`/`select`/`delete`, and **no `commit()` inside**.

---

## 10. Quick reference

| Task                     | Modern 2.0 code                                              |
| ------------------------ | ------------------------------------------------------------ |
| Insert + get object back | `db.add(obj); db.flush()`                                    |
| Get by primary key       | `db.get(Model, pk)`                                          |
| List all                 | `db.scalars(select(Model)).all()`                            |
| First match or None      | `db.scalars(select(Model).where(...)).first()`               |
| Exactly one              | `db.scalars(select(Model).where(...)).one()`                 |
| Specific columns         | `db.execute(select(Model.a, Model.b)).all()`                 |
| Count                    | `db.scalar(select(func.count()).select_from(Model))`         |
| Update one               | load → set attr → `db.flush()`                               |
| Update many              | `db.execute(update(Model).where(...).values(...))`           |
| Delete one               | `db.delete(obj); db.flush()`                                 |
| Delete many              | `db.execute(delete(Model).where(...))`                       |
| Child rows by parent id  | `select(Child).where(Child.parent_id == pid)`                |
| Join 2 tables            | `select(A).join(B, B.a_id == A.id)`                          |
| Join 3 tables            | `select(A).join(B, B.a_id == A.id).join(C, C.b_id == B.id)`  |
| Left/outer join          | `select(A).outerjoin(B, B.a_id == A.id)`                     |
| Eager-load collection    | `select(A).options(selectinload(A.children))`                |
| Eager-load parent        | `select(Child).options(joinedload(Child.parent))`            |
| Commit                   | once, by the session owner — not in repositories             |

### Legacy → modern cheat sheet

| Legacy (avoid)                       | Modern (use)                                        |
| ------------------------------------ | --------------------------------------------------- |
| `db.query(User).all()`               | `db.scalars(select(User)).all()`                    |
| `db.query(User).get(pk)`             | `db.get(User, pk)`                                  |
| `db.query(User).filter_by(name="A")` | `select(User).where(User.name == "A")`              |
| `db.query(User).filter(...)`         | `select(User).where(...)`                           |
| `db.query(User).count()`             | `db.scalar(select(func.count()).select_from(User))` |
| `query.first()` / `.one()`           | `db.scalars(select(...)).first()` / `.one()`        |
