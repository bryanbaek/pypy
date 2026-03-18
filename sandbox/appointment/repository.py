from datetime import datetime


async def has_conflict(conn, start_time: datetime, end_time: datetime) -> bool:
    conflicting = await conn.fetch(
        """
        SELECT 1
        FROM appointments
        WHERE start_time < $2
          AND end_time > $1
        LIMIT 1
        """,
        start_time,
        end_time,
    )
    return bool(conflicting)


async def create_appointment(
    conn, title: str, start_time: datetime, end_time: datetime
) -> dict:
    await conn.execute(
        "INSERT INTO appointments (title, start_time, end_time) VALUES ($1, $2, $3)",
        title,
        start_time,
        end_time,
    )
    return {"title": title, "start_time": start_time, "end_time": end_time}
