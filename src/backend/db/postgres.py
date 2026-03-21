import asyncpg  # type: ignore

from src.backend.core.appointment_workflow import run_appointment_happy_path
from src.backend.core.document_workflow import write_document_sample


async def write_document(conn, document_id, title, content):
    return await write_document_sample(conn, document_id, title, content)


async def create_appointment(conn, title, start_time, end_time):
    return await run_appointment_happy_path(conn, title, start_time, end_time)


async def get_document(conn, document_id):
    return await conn.fetchrow(
        """
        SELECT id, title, content
        FROM documents
        WHERE id = $1
        """,
        document_id,
    )


async def delete_document(conn, document_id):
    await conn.execute("DELETE FROM documents WHERE id = $1", document_id)


async def connect_to_db():
    conn = await asyncpg.connect(
        database="your_database_name",
        user="your_username",
        password="your_password",
        host="localhost",
    )
    return conn
