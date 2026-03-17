import asyncpg  # type: ignore

from src.backend.core import run_appointment_happy_path


async def create_appointment(conn, title, start_time, end_time):
    return await run_appointment_happy_path(conn, title, start_time, end_time)


async def get_appointments(conn):
    return await conn.fetch("SELECT * FROM appointments")


async def update_appointment(
    conn, appointment_id, title=None, start_time=None, end_time=None
):
    if title:
        await conn.execute(
            "UPDATE appointments SET title = $1 WHERE id = $2", title, appointment_id
        )
    if start_time:
        await conn.execute(
            "UPDATE appointments SET start_time = $1 WHERE id = $2",
            start_time,
            appointment_id,
        )
    if end_time:
        await conn.execute(
            "UPDATE appointments SET end_time = $1 WHERE id = $2",
            end_time,
            appointment_id,
        )


async def delete_appointment(conn, appointment_id):
    await conn.execute("DELETE FROM appointments WHERE id = $1", appointment_id)


async def connect_to_db():
    conn = await asyncpg.connect(
        database="your_database_name",
        user="your_username",
        password="your_password",
        host="localhost",
    )
    return conn
