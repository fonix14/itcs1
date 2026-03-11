from __future__ import annotations

import httpx


class MatrixClient:
    def __init__(self, base_url: str, access_token: str, timeout_sec: float = 15.0):
        self.base_url = base_url.rstrip('/')
        self.access_token = access_token
        self.timeout_sec = timeout_sec

    async def send_text(self, room_id: str, txn_id: str, body: str) -> None:
        """Send message to Matrix room.

        Idempotency:
        - Matrix endpoint uses txn_id; repeated PUT with same txn_id should not duplicate the event.

        Raises httpx.HTTPStatusError on non-2xx.
        """
        url = f"{self.base_url}/_matrix/client/v3/rooms/{room_id}/send/m.room.message/{txn_id}"
        headers = {
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        payload = {"msgtype": "m.text", "body": body}

        async with httpx.AsyncClient(timeout=self.timeout_sec) as client:
            r = await client.put(url, headers=headers, json=payload)
            r.raise_for_status()
