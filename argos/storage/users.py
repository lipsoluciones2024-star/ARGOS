from __future__ import annotations

import hashlib
import hmac
import logging
import secrets
import sqlite3
from datetime import datetime, timezone
from typing import Any, Optional

from argos.config import Config
from argos.security.auth import ROLES

# Usamos scrypt de la stdlib (sin dependencias externas) para el hash de contraseñas.
_SCRYPT_N = 1 << 14
_SCRYPT_R = 8
_SCRYPT_P = 1
_SCRYPT_MAXMEM = 64 * 1024 * 1024


def _hash_password(password: str, salt: str | None = None) -> tuple[str, str]:
    if salt is None:
        salt = secrets.token_hex(16)
    dk = hashlib.scrypt(
        password.encode("utf-8"),
        salt=salt.encode("utf-8"),
        n=_SCRYPT_N, r=_SCRYPT_R, p=_SCRYPT_P,
        maxmem=_SCRYPT_MAXMEM, dklen=32,
    )
    return dk.hex(), salt


def _verify_password(password: str, salt: str, expected_hash: str) -> bool:
    dk, _ = _hash_password(password, salt)
    return hmac.compare_digest(dk, expected_hash)


class UsersStore:
    def __init__(self, cfg: Config) -> None:
        self.cfg = cfg
        self.db_path = cfg.data_dir / "argos.db"
        self.conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self.conn.execute("PRAGMA journal_mode=WAL")
        self.conn.execute("PRAGMA foreign_keys=ON")
        self._init_schema()
        self._seed_admin()

    def _init_schema(self) -> None:
        self.conn.execute(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                username TEXT UNIQUE NOT NULL,
                role TEXT NOT NULL,
                password_hash TEXT NOT NULL,
                salt TEXT NOT NULL,
                enabled INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            )
            """
        )
        self.conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_users_username ON users(username)"
        )
        self.conn.commit()

    def _seed_admin(self) -> None:
        """Crea un admin por defecto si no existe ninguno (bootstrapping seguro)."""
        row = self.conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()
        if row and row["c"] > 0:
            return
        seed_pass = secrets.token_urlsafe(18)
        self.create("admin", seed_pass, "admin", enabled=True,
                    created_by="system:bootstrap")
        # El password inicial solo se muestra en el log de arranque.
        logging.getLogger("argos.users").warning(
            "USUARIO ADMIN CREADO (bootstrap): usuario=admin | password=%s "
            "(cámbialo con 'argos auth create-user' o desde la UI).", seed_pass
        )

    def create(self, username: str, password: str, role: str = "operator",
               enabled: bool = True, created_by: str = "system") -> dict[str, Any]:
        if role not in ROLES:
            raise ValueError(f"rol inválido: {role}. Roles válidos: {ROLES}")
        if len(password) < 8:
            raise ValueError("el password debe tener al menos 8 caracteres")
        phash, salt = _hash_password(password)
        uid = secrets.token_hex(16)
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "INSERT INTO users (id, username, role, password_hash, salt, enabled, created_at, updated_at) "
            "VALUES (?,?,?,?,?,?,?,?)",
            (uid, username, role, phash, salt, 1 if enabled else 0, now, now),
        )
        self.conn.commit()
        return self._public(uid, username, role, enabled, now, now, created_by)

    def list(self, limit: int = 200) -> list[dict[str, Any]]:
        rows = self.conn.execute(
            "SELECT id, username, role, enabled, created_at, updated_at FROM users "
            "ORDER BY username LIMIT ?", (limit,)
        ).fetchall()
        return [self._public_row(r) for r in rows]

    def get(self, user_id: str) -> Optional[dict[str, Any]]:
        r = self.conn.execute(
            "SELECT id, username, role, enabled, created_at, updated_at FROM users WHERE id=?",
            (user_id,),
        ).fetchone()
        return self._public_row(r) if r else None

    def get_by_username(self, username: str) -> Optional[dict[str, Any]]:
        r = self.conn.execute(
            "SELECT * FROM users WHERE username=?", (username,)
        ).fetchone()
        return dict(r) if r else None

    def update(self, user_id: str, role: str | None = None,
               password: str | None = None, enabled: bool | None = None) -> Optional[dict[str, Any]]:
        cur = self.conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not cur:
            return None
        new_role = role if role is not None else cur["role"]
        if role is not None and new_role not in ROLES:
            raise ValueError(f"rol inválido: {new_role}")
        new_enabled = enabled if enabled is not None else bool(cur["enabled"])
        new_hash, new_salt = cur["password_hash"], cur["salt"]
        if password is not None:
            if len(password) < 8:
                raise ValueError("el password debe tener al menos 8 caracteres")
            new_hash, new_salt = _hash_password(password)
        now = datetime.now(timezone.utc).isoformat()
        self.conn.execute(
            "UPDATE users SET role=?, password_hash=?, salt=?, enabled=?, updated_at=? WHERE id=?",
            (new_role, new_hash, new_salt, 1 if new_enabled else 0, now, user_id),
        )
        self.conn.commit()
        return self.get(user_id)

    def delete(self, user_id: str) -> bool:
        cur = self.conn.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()
        if not cur:
            return False
        if cur["username"] == "admin":
            raise ValueError("no se puede eliminar el usuario admin")
        self.conn.execute("DELETE FROM users WHERE id=?", (user_id,))
        self.conn.commit()
        return True

    def authenticate(self, username: str, password: str) -> Optional[dict[str, Any]]:
        r = self.get_by_username(username)
        if not r:
            return None
        if not r["enabled"]:
            return None
        if not _verify_password(password, r["salt"], r["password_hash"]):
            return None
        return {
            "id": r["id"], "username": r["username"], "role": r["role"],
            "enabled": bool(r["enabled"]), "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }

    @staticmethod
    def _public_row(r: sqlite3.Row) -> dict[str, Any]:
        return {
            "id": r["id"], "username": r["username"], "role": r["role"],
            "enabled": bool(r["enabled"]), "created_at": r["created_at"],
            "updated_at": r["updated_at"],
        }

    @staticmethod
    def _public(uid: str, username: str, role: str, enabled: bool,
                created_at: str, updated_at: str, created_by: str) -> dict[str, Any]:
        return {
            "id": uid, "username": username, "role": role, "enabled": enabled,
            "created_at": created_at, "updated_at": updated_at, "created_by": created_by,
        }

    def close(self) -> None:
        self.conn.close()
