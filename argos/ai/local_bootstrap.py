from __future__ import annotations

import hashlib
import urllib.request
from pathlib import Path
from typing import Optional

from argos.config import Config


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def model_path(cfg: Config) -> Path:
    p = Path(cfg.local_model_path)
    return p if p.is_absolute() else cfg.model_dir() / p


def verify_model(cfg: Config) -> bool:
    p = model_path(cfg)
    if not p.exists():
        return False
    if cfg.local_model_sha256:
        return _sha256(p) == cfg.local_model_sha256
    return True


def ensure_model(cfg: Config, url: Optional[str] = None, sha256: Optional[str] = None) -> Path:
    """Asegura que el GGUF local exista y verifique su checksum.

    Si ya existe y el checksum coincide, lo devuelve. Si no, descarga desde
    `url` (o cfg.local_model_url), verifica y guarda en models/.
    Lanza RuntimeError si no hay URL o el checksum no coincide.
    """
    url = url or cfg.local_model_url
    sha256 = sha256 or cfg.local_model_sha256
    p = model_path(cfg)
    cfg.model_dir().mkdir(parents=True, exist_ok=True)
    if p.exists() and (not sha256 or _sha256(p) == sha256):
        return p
    if not url:
        raise RuntimeError(
            f"Modelo local no encontrado en {p} y no se definió ARGOS_LOCAL_MODEL_URL. "
            "Coloca el GGUF en esa ruta o ejecuta 'argos bootstrap --url <url>'."
        )
    tmp = p.with_suffix(p.suffix + ".downloading")
    print(f"Descargando modelo local desde {url} …")
    urllib.request.urlretrieve(url, str(tmp))
    digest = _sha256(tmp)
    if sha256 and digest != sha256:
        tmp.unlink(missing_ok=True)
        raise RuntimeError(f"Checksum del modelo no coincide: esperado {sha256}, obtenido {digest}")
    tmp.replace(p)
    return p
