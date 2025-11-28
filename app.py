import logging
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from generators import generator

import psycopg
from psycopg.rows import dict_row
from psycopg_pool import AsyncConnectionPool

logging.basicConfig(level=logging.INFO)

DATABASE_URL = os.getenv("DATABASE")

app = FastAPI()

# -----------------------------------------------------
# DATABASE POOL (Python 3.13 SAFE)
# -----------------------------------------------------
pool = AsyncConnectionPool(conninfo=DATABASE_URL)


# -----------------------------------------------------
# DATABASE INIT
# -----------------------------------------------------
async def init_db():
    async with pool.connection() as conn:
        await conn.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                email TEXT NOT NULL,
                value INTEGER NOT NULL DEFAULT 128
            );
        """)
        await conn.commit()
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
    async with pool.connection() as conn:
        rows = await conn.execute("SELECT id, email, value FROM users ORDER BY id ASC")
        rows = await rows.fetchall()
        # Convert Row objects to dicts
        users = []
        for r in rows:
            users.append({
                "id": r[0],
                "email": r[1],
                "value": r[2]
            })
        return users





# -----------------------------------------------------
# ENDPOINTS
# -----------------------------------------------------

@app.get("/state")
async def get_state():
    users = await fetch_all_users()
    return {"users": users}


@app.post("/users")
async def create_user(user: UserCreate):
    async with pool.connection() as conn:
        row = await conn.execute(
            """
            INSERT INTO users (email, value)
            VALUES (%s, %s)
            RETURNING id, email, value
            """,
            (user.email, user.value)
        )
        row = await row.fetchone()
        await conn.commit()
        return row


@app.put("/users/{user_id}")
async def update_user(user_id: int, upd: UserUpdate):
    async with pool.connection() as conn:
        row = await conn.execute(
            """
            UPDATE users
            SET value=%s
            WHERE id=%s
            RETURNING id, email, value
            """,
            (upd.value, user_id)
        )
        row = await row.fetchone()
        await conn.commit()

        if not row:
            raise HTTPException(404, "User not found")

        return row


# -----------------------------------------------------
# AGENT ACTION ENDPOINT (JSON BODY)
# EXACTLY LIKE YOUR FILE
# -----------------------------------------------------
@app.post("/agent/action")
async def agent_action(data: AgentAction):
    user_id = data.user_id
    action = data.action

    if action not in ("increment", "decrement"):
        raise HTTPException(400, "Invalid action")

    async with pool.connection() as conn:
        if action == "increment":
            row = await conn.execute(
                """
                UPDATE users
                SET value = value + 1
                WHERE id=%s
                RETURNING id, email, value
                """,
                (user_id,)
            )
        else:
            row = await conn.execute(
                """
                UPDATE users
                SET value = value - 1
                WHERE id=%s
                RETURNING id, email, value
                """,
                (user_id,)
            )

        row = await row.fetchone()
        await conn.commit()

        if not row:
            raise HTTPException(404, "User not found")

        return row


# -----------------------------------------------------
# RANDOM USER GENERATOR
# -----------------------------------------------------
@app.post("/random-user")
async def random_user():
    email = generator.get_email()

    async with pool.connection() as conn:
        row = await conn.execute(
            """
            INSERT INTO users (email, value)
            VALUES (%s, 256)
            RETURNING id, email, value
            """,
            (email,)
        )
        row = await row.fetchone()
        await conn.commit()
        return row
