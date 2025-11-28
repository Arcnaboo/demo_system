import asyncpg
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import logging
from generators import generator
import os
logging.basicConfig(level=logging.INFO)

DATABASE_URL = os.getenv("DATABASE")  

app = FastAPI()


# -----------------------------------------------------
# DATABASE INIT
# -----------------------------------------------------
async def init_db():
    conn = await asyncpg.connect(DATABASE_URL)
    await conn.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id SERIAL PRIMARY KEY,
            email TEXT NOT NULL,
            value INTEGER NOT NULL DEFAULT 128
        );
    """)
    await conn.close()
    logging.info("DB initialized.")


@app.on_event("startup")
async def startup_event():
    await init_db()
    logging.info("Startup: DB ready.")


# -----------------------------------------------------
# MODELS
# -----------------------------------------------------
class UserCreate(BaseModel):
    email: str
    value: int = 128


class UserUpdate(BaseModel):
    value: int


class AgentAction(BaseModel):
    user_id: int
    action: str


# -----------------------------------------------------
# HELPERS
# -----------------------------------------------------
async def fetch_all_users():
    conn = await asyncpg.connect(DATABASE_URL)
    rows = await conn.fetch("SELECT id, email, value FROM users ORDER BY id ASC")
    await conn.close()
    return [dict(r) for r in rows]


# -----------------------------------------------------
# ENDPOINTS
# -----------------------------------------------------

@app.get("/state")
async def get_state():
    users = await fetch_all_users()
    return {"users": users}


@app.post("/users")
async def create_user(user: UserCreate):
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow(
        "INSERT INTO users (email, value) VALUES ($1, $2) RETURNING id, email, value",
        user.email, user.value
    )
    await conn.close()
    return dict(row)


@app.put("/users/{user_id}")
async def update_user(user_id: int, upd: UserUpdate):
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow(
        "UPDATE users SET value=$1 WHERE id=$2 RETURNING id, email, value",
        upd.value, user_id
    )
    await conn.close()

    if not row:
        raise HTTPException(404, "User not found")

    return dict(row)


# -----------------------------------------------------
# FIXED: AGENT ACTION ENDPOINT (NOW ACCEPTS JSON BODY)
# -----------------------------------------------------
@app.post("/agent/action")
async def agent_action(data: AgentAction):
    user_id = data.user_id
    action = data.action

    if action not in ("increment", "decrement"):
        raise HTTPException(400, "Invalid action")

    conn = await asyncpg.connect(DATABASE_URL)

    if action == "increment":
        row = await conn.fetchrow("""
            UPDATE users SET value = value + 1
            WHERE id=$1
            RETURNING id, email, value
        """, user_id)
    else:
        row = await conn.fetchrow("""
            UPDATE users SET value = value - 1
            WHERE id=$1
            RETURNING id, email, value
        """, user_id)

    await conn.close()

    if not row:
        raise HTTPException(404, "User not found")

    return dict(row)


# -----------------------------------------------------
# RANDOM USER GENERATOR
# -----------------------------------------------------
@app.post("/random-user")
async def random_user():
    email = generator.get_email()
    conn = await asyncpg.connect(DATABASE_URL)
    row = await conn.fetchrow(
        "INSERT INTO users (email, value) VALUES ($1, 256) RETURNING id, email, value",
        email
    )
    await conn.close()
    return dict(row)
