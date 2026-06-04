"""Background sync worker that manages all active Telegram accounts."""

import asyncio
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from telethon.errors import FloodWaitError

from app.config import settings
from app.database import SessionLocal
from app.models import (
    TelegramAccount,
    TelegramAccountStatus,
    TelegramCommand,
    TelegramCommandStatus,
)
from workers.telegram_manager import (
    handle_send_code,
    handle_submit_code,
    join_channel,
    leave_channel,
    load_session_string,
    make_client,
    save_session_string,
    send_message,
    sync_chats,
    sync_messages,
)

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
)
logger = logging.getLogger("sync-worker")


class AccountWorker:
    """Manages a single Telethon client for one account."""

    def __init__(self, account_id: int):
        self.account_id = account_id
        self.client = None
        self.last_sync = 0.0

    async def ensure_connected(self) -> bool:
        """Connect the client if not connected, return True if authorized."""
        with SessionLocal() as db:
            account = db.get(TelegramAccount, self.account_id)
            if not account or not account.is_active:
                return False
            session_string = load_session_string(db, account)

        if self.client is None or not self.client.is_connected():
            self.client = make_client(session_string)
            await self.client.connect()

        return await self.client.is_user_authorized()

    async def disconnect(self):
        if self.client and self.client.is_connected():
            await self.client.disconnect()
        self.client = None


async def process_commands(workers: dict[int, AccountWorker]) -> None:
    """Process pending commands from the database queue."""
    with SessionLocal() as db:
        commands = list(db.scalars(
            select(TelegramCommand)
            .where(TelegramCommand.status == TelegramCommandStatus.pending)
            .order_by(TelegramCommand.created_at.asc())
            .limit(10)
        ))
        if not commands:
            return

        for command in commands:
            command.status = TelegramCommandStatus.running
        db.commit()

        command_ids = [(c.id, c.telegram_account_id, c.command, c.payload or {}) for c in commands]

    for cmd_id, account_id, cmd_name, payload in command_ids:
        try:
            # Ensure worker exists
            if account_id not in workers:
                workers[account_id] = AccountWorker(account_id)
            worker = workers[account_id]

            await worker.ensure_connected()

            with SessionLocal() as db:
                account = db.get(TelegramAccount, account_id)
                if not account:
                    raise RuntimeError(f"Account {account_id} not found")

                result = await _execute_command(
                    worker.client, db, account, cmd_name, payload
                )

                cmd = db.get(TelegramCommand, cmd_id)
                cmd.status = TelegramCommandStatus.succeeded
                cmd.result = result
                cmd.error = None
                
                # Clear transient errors on success
                if cmd_name in ("send_code", "submit_code"):
                    account.last_error = None
                
                db.commit()

        except Exception as exc:
            logger.exception("Command %s failed for account %s", cmd_name, account_id)
            with SessionLocal() as db:
                cmd = db.get(TelegramCommand, cmd_id)
                if cmd:
                    cmd.status = TelegramCommandStatus.failed
                    cmd.error = str(exc)
                    db.commit()

                # Update account status on error
                account = db.get(TelegramAccount, account_id)
                if account and cmd_name in ("send_code", "submit_code"):
                    account.status = TelegramAccountStatus.error
                    account.last_error = str(exc)
                    db.commit()


async def _execute_command(
    client, db, account: TelegramAccount, cmd_name: str, payload: dict
) -> dict:
    """Dispatch a command to the appropriate handler."""
    if cmd_name == "send_code":
        return await handle_send_code(client, db, account, payload.get("phone", account.phone))

    if cmd_name == "submit_code":
        return await handle_submit_code(
            client, db, account,
            phone=payload.get("phone", account.phone),
            code=payload["code"],
            password=payload.get("password"),
        )

    if cmd_name == "sync_chats":
        await sync_chats(client, db, account)
        return {"status": "synced"}

    if cmd_name == "sync_messages":
        await sync_messages(client, db, account)
        return {"status": "synced"}

    if cmd_name == "send_message":
        return await send_message(
            client, payload["telegram_chat_id"], payload["text"]
        )

    if cmd_name == "join_channel":
        return await join_channel(client, db, account, payload["channel_url"])

    if cmd_name == "leave_channel":
        return await leave_channel(client, payload["telegram_chat_id"])

    raise RuntimeError(f"Unknown command: {cmd_name}")


async def periodic_sync(workers: dict[int, AccountWorker]) -> None:
    """Run periodic sync for all authorized accounts."""
    with SessionLocal() as db:
        accounts = list(db.scalars(
            select(TelegramAccount).where(
                TelegramAccount.status == TelegramAccountStatus.authorized,
                TelegramAccount.is_active.is_(True),
            )
        ))
        account_ids = [a.id for a in accounts]

    for account_id in account_ids:
        if account_id not in workers:
            workers[account_id] = AccountWorker(account_id)
        worker = workers[account_id]

        now = asyncio.get_running_loop().time()
        if now - worker.last_sync < settings.sync_interval_seconds:
            continue

        try:
            authorized = await worker.ensure_connected()
            if not authorized:
                continue

            with SessionLocal() as db:
                account = db.get(TelegramAccount, account_id)
                if not account:
                    continue
                await sync_chats(worker.client, db, account)
                await sync_messages(worker.client, db, account)
                account.last_error = None
                db.commit()

            worker.last_sync = now
            logger.info("Synced account %s", account_id)

        except FloodWaitError as exc:
            logger.warning("Flood wait for account %s: %ss", account_id, exc.seconds)
            await asyncio.sleep(min(exc.seconds, 60))
        except Exception as exc:
            logger.exception("Sync failed for account %s", account_id)
            with SessionLocal() as db:
                account = db.get(TelegramAccount, account_id)
                if account:
                    account.last_error = str(exc)
                    db.commit()


async def main_loop() -> None:
    """Main event loop: process commands + periodic sync."""
    workers: dict[int, AccountWorker] = {}
    logger.info("Telegram sync worker started")

    try:
        while True:
            try:
                await process_commands(workers)
                await periodic_sync(workers)
            except Exception as exc:
                logger.exception("Worker loop error: %s", exc)
            await asyncio.sleep(2)
    finally:
        # Disconnect all clients
        for worker in workers.values():
            try:
                await worker.disconnect()
            except Exception:
                pass
        logger.info("Telegram sync worker stopped")


if __name__ == "__main__":
    asyncio.run(main_loop())
