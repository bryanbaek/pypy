from datetime import datetime


def _row_to_appointment(row) -> dict | None:
    if row is None:
        return None
    return {
        "id": row["id"],
        "title": row["title"],
        "start_time": row["start_time"],
        "end_time": row["end_time"],
    }


async def has_conflict(
    conn,
    start_time: datetime,
    end_time: datetime,
    exclude_appointment_id: int | None = None,
) -> bool:
    if exclude_appointment_id is None:
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
    else:
        conflicting = await conn.fetch(
            """
            SELECT 1
            FROM appointments
            WHERE start_time < $2
              AND end_time > $1
              AND id != $3
            LIMIT 1
            """,
            start_time,
            end_time,
            exclude_appointment_id,
        )
    return bool(conflicting)


async def create_appointment(
    conn, title: str, start_time: datetime, end_time: datetime
) -> dict:
    row = await conn.fetchrow(
        """
        INSERT INTO appointments (title, start_time, end_time)
        VALUES ($1, $2, $3)
        RETURNING id, title, start_time, end_time
        """,
        title,
        start_time,
        end_time,
    )
    appointment = _row_to_appointment(row)
    if appointment is None:
        return {"title": title, "start_time": start_time, "end_time": end_time}
    return appointment


async def get_appointment(conn, appointment_id: int) -> dict | None:
    row = await conn.fetchrow(
        """
        SELECT id, title, start_time, end_time
        FROM appointments
        WHERE id = $1
        """,
        appointment_id,
    )
    return _row_to_appointment(row)


async def get_appointments(conn) -> list[dict]:
    rows = await conn.fetch(
        """
        SELECT id, title, start_time, end_time
        FROM appointments
        ORDER BY start_time
        """
    )
    return [appointment for row in rows if (appointment := _row_to_appointment(row))]


async def update_appointment(
    conn,
    appointment_id: int,
    title: str,
    start_time: datetime,
    end_time: datetime,
) -> dict | None:
    row = await conn.fetchrow(
        """
        UPDATE appointments
        SET title = $1, start_time = $2, end_time = $3
        WHERE id = $4
        RETURNING id, title, start_time, end_time
        """,
        title,
        start_time,
        end_time,
        appointment_id,
    )
    return _row_to_appointment(row)


async def delete_appointment(conn, appointment_id: int) -> None:
    await conn.execute("DELETE FROM appointments WHERE id = $1", appointment_id)
