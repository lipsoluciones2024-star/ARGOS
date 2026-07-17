# DOCUMENTO DE SEGURIDAD Y VALIDACIÓN: ARGOS Enterprise

**Versión:** 1.0  
**Fecha:** 2026-07-16  
**Objetivo:** Establecer estándares de seguridad enterprise y procesos de validación para ARGOS nivel XAI

---

## 1. VISIÓN GENERAL

### 1.1 Principios de Seguridad
- **Zero Trust:** Nunca confiar, siempre verificar
- **Defense in Depth:** Múltiples capas de seguridad
- **Least Privilege:** Mínimo acceso necesario
- **Audit Everything:** Todo debe ser auditable
- **Secure by Design:** Seguridad desde el diseño

### 1.2 Objetivos de Seguridad
- **Confidencialidad:** Proteger datos sensibles
- **Integridad:** Prevenir modificaciones no autorizadas
- **Disponibilidad:** Garantizar acceso continuo
- **Auditabilidad:** Rastro completo de acciones
- **Compliance:** Cumplir estándares (NIST, CIS, MITRE)

### 1.3 Alcance
Este documento cubre:
- Autenticación y autorización
- Validación de inputs
- Seguridad de datos
- Audit logging
- Testing de seguridad
- Validación de componentes
- Compliance

---

## 2. AUTENTICACIÓN Y AUTORIZACIÓN

### 2.1 RBAC Avanzado

```python
# argos/security/rbac.py
from enum import Enum
from typing import Set, Dict, List, Optional
from dataclasses import dataclass

class Permission(Enum):
    """Permisos del sistema."""
    # Event operations
    READ_EVENTS = "read:events"
    WRITE_EVENTS = "write:events"
    DELETE_EVENTS = "delete:events"
    
    # Alert operations
    READ_ALERTS = "read:alerts"
    WRITE_ALERTS = "write:alerts"
    ACKNOWLEDGE_ALERTS = "acknowledge:alerts"
    
    # Detection operations
    READ_RULES = "read:rules"
    WRITE_RULES = "write:rules"
    ENABLE_RULES = "enable:rules"
    DISABLE_RULES = "disable:rules"
    
    # Response operations
    READ_RESPONSES = "read:responses"
    WRITE_RESPONSES = "write:responses"
    EXECUTE_RESPONSES = "execute:responses"
    
    # System operations
    READ_CONFIG = "read:config"
    WRITE_CONFIG = "write:config"
    MANAGE_USERS = "manage:users"
    MANAGE_PLUGINS = "manage:plugins"
    VIEW_AUDIT = "view:audit"
    SYSTEM_ADMIN = "system:admin"

class Role(Enum):
    """Roles del sistema."""
    OPERATOR = "operator"
    ANALYST = "analyst"
    INVESTIGATOR = "investigator"
    RESPONDER = "responder"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"

@dataclass
class User:
    """Usuario del sistema."""
    id: str
    username: str
    email: str
    role: Role
    permissions: Set[Permission]
    enabled: bool = True
    mfa_enabled: bool = False

# Mapping de roles a permisos
ROLE_PERMISSIONS: Dict[Role, Set[Permission]] = {
    Role.OPERATOR: {
        Permission.READ_EVENTS,
        Permission.READ_ALERTS,
        Permission.READ_RULES,
        Permission.READ_RESPONSES,
        Permission.READ_CONFIG,
        Permission.VIEW_AUDIT,
    },
    Role.ANALYST: {
        *ROLE_PERMISSIONS[Role.OPERATOR],
        Permission.WRITE_ALERTS,
        Permission.ACKNOWLEDGE_ALERTS,
    },
    Role.INVESTIGATOR: {
        *ROLE_PERMISSIONS[Role.ANALYST],
        Permission.WRITE_EVENTS,
        Permission.WRITE_RULES,
    },
    Role.RESPONDER: {
        *ROLE_PERMISSIONS[Role.INVESTIGATOR],
        Permission.WRITE_RESPONSES,
        Permission.EXECUTE_RESPONSES,
    },
    Role.ADMIN: {
        *ROLE_PERMISSIONS[Role.RESPONDER],
        Permission.WRITE_CONFIG,
        Permission.MANAGE_USERS,
        Permission.MANAGE_PLUGINS,
    },
    Role.SUPERADMIN: {
        *ROLE_PERMISSIONS[Role.ADMIN],
        Permission.DELETE_EVENTS,
        Permission.SYSTEM_ADMIN,
    },
}

class RBACManager:
    """Gestor de RBAC."""
    
    def __init__(self):
        self.users: Dict[str, User] = {}
        self.sessions: Dict[str, Dict] = {}
    
    def create_user(self, username: str, email: str, role: Role) -> User:
        """Crea un nuevo usuario."""
        user_id = self._generate_user_id()
        permissions = ROLE_PERMISSIONS.get(role, set())
        
        user = User(
            id=user_id,
            username=username,
            email=email,
            role=role,
            permissions=permissions
        )
        
        self.users[user_id] = user
        return user
    
    def has_permission(self, user_id: str, permission: Permission) -> bool:
        """Verifica si un usuario tiene un permiso."""
        user = self.users.get(user_id)
        if not user or not user.enabled:
            return False
        
        return permission in user.permissions
    
    def has_any_permission(self, user_id: str, permissions: Set[Permission]) -> bool:
        """Verifica si un usuario tiene alguno de los permisos."""
        user = self.users.get(user_id)
        if not user or not user.enabled:
            return False
        
        return bool(user.permissions & permissions)
    
    def has_all_permissions(self, user_id: str, permissions: Set[Permission]) -> bool:
        """Verifica si un usuario tiene todos los permisos."""
        user = self.users.get(user_id)
        if not user or not user.enabled:
            return False
        
        return permissions.issubset(user.permissions)
    
    def grant_permission(self, user_id: str, permission: Permission) -> bool:
        """Otorga un permiso a un usuario."""
        user = self.users.get(user_id)
        if not user:
            return False
        
        user.permissions.add(permission)
        return True
    
    def revoke_permission(self, user_id: str, permission: Permission) -> bool:
        """Revoca un permiso de un usuario."""
        user = self.users.get(user_id)
        if not user:
            return False
        
        user.permissions.discard(permission)
        return True
    
    def create_session(self, user_id: str, metadata: Optional[Dict] = None) -> str:
        """Crea una sesión de usuario."""
        session_id = self._generate_session_id()
        
        self.sessions[session_id] = {
            "user_id": user_id,
            "created_at": time.time(),
            "last_activity": time.time(),
            "metadata": metadata or {},
            "ip_address": metadata.get("ip_address") if metadata else None,
            "user_agent": metadata.get("user_agent") if metadata else None,
        }
        
        return session_id
    
    def validate_session(self, session_id: str) -> Optional[User]:
        """Valida una sesión y retorna el usuario."""
        session = self.sessions.get(session_id)
        if not session:
            return None
        
        # Check session timeout (24 hours)
        if time.time() - session["last_activity"] > 86400:
            del self.sessions[session_id]
            return None
        
        # Update last activity
        session["last_activity"] = time.time()
        
        return self.users.get(session["user_id"])
    
    def revoke_session(self, session_id: str) -> bool:
        """Revoca una sesión."""
        if session_id in self.sessions:
            del self.sessions[session_id]
            return True
        return False
    
    def revoke_all_user_sessions(self, user_id: str) -> int:
        """Revoca todas las sesiones de un usuario."""
        count = 0
        for session_id, session in list(self.sessions.items()):
            if session["user_id"] == user_id:
                del self.sessions[session_id]
                count += 1
        return count
    
    def _generate_user_id(self) -> str:
        """Genera un ID de usuario único."""
        return f"user_{uuid.uuid4().hex}"
    
    def _generate_session_id(self) -> str:
        """Genera un ID de sesión único."""
        return f"session_{uuid.uuid4().hex}"
```

### 2.2 Autenticación Multi-Factor

```python
# argos/security/mfa.py
import pyotp
import qrcode
from io import BytesIO
import base64

class MFAManager:
    """Gestor de autenticación multi-factor."""
    
    def __init__(self):
        self.secrets: Dict[str, str] = {}
    
    def generate_secret(self, user_id: str) -> str:
        """Genera un secreto TOTP para un usuario."""
        secret = pyotp.random_base32()
        self.secrets[user_id] = secret
        return secret
    
    def generate_qr_code(self, user_id: str, username: str, issuer: str = "ARGOS") -> str:
        """Genera un código QR para configuración TOTP."""
        secret = self.secrets.get(user_id)
        if not secret:
            raise ValueError("No secret found for user")
        
        totp = pyotp.TOTP(secret)
        provisioning_uri = totp.provisioning_uri(
            name=username,
            issuer_name=issuer
        )
        
        qr = qrcode.QRCode(version=1, box_size=10, border=5)
        qr.add_data(provisioning_uri)
        qr.make(fit=True)
        
        img = qr.make_image(fill_color="black", back_color="white")
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        img_str = base64.b64encode(buffer.getvalue()).decode()
        
        return f"data:image/png;base64,{img_str}"
    
    def verify_token(self, user_id: str, token: str) -> bool:
        """Verifica un token TOTP."""
        secret = self.secrets.get(user_id)
        if not secret:
            return False
        
        totp = pyotp.TOTP(secret)
        return totp.verify(token, valid_window=1)  # Allow 1 step drift
    
    def enable_mfa(self, user_id: str) -> str:
        """Habilita MFA para un usuario."""
        secret = self.generate_secret(user_id)
        return secret
    
    def disable_mfa(self, user_id: str) -> bool:
        """Deshabilita MFA para un usuario."""
        if user_id in self.secrets:
            del self.secrets[user_id]
            return True
        return False
```

---

## 3. VALIDACIÓN DE INPUTS

### 3.1 Validación de API Inputs

```python
# argos/security/validation.py
from pydantic import BaseModel, validator, Field
from typing import Optional, List, Dict, Any
from datetime import datetime
import re

class EventQueryValidator(BaseModel):
    """Validador para queries de eventos."""
    
    filters: Optional[Dict[str, Any]] = None
    limit: int = Field(default=100, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)
    
    @validator('filters')
    def validate_filters(cls, v):
        if v is None:
            return v
        
        # Validar que los filtros sean seguros
        dangerous_keys = ['__proto__', 'constructor', 'prototype']
        for key in dangerous_keys:
            if key in str(v):
                raise ValueError("Potentially dangerous filter detected")
        
        # Validar regex patterns
        if 'pattern' in v:
            try:
                re.compile(v['pattern'])
            except re.error:
                raise ValueError("Invalid regex pattern")
        
        return v

class ToolExecutionValidator(BaseModel):
    """Validador para ejecución de tools."""
    
    tool_name: str = Field(..., min_length=1, max_length=100)
    arguments: Dict[str, Any] = Field(default_factory=dict)
    
    @validator('tool_name')
    def validate_tool_name(cls, v):
        # Solo permitir caracteres alfanuméricos y guiones
        if not re.match(r'^[a-zA-Z0-9_-]+$', v):
            raise ValueError("Invalid tool name")
        return v
    
    @validator('arguments')
    def validate_arguments(cls, v):
        # Validar que no haya código ejecutable
        dangerous_patterns = [
            r'__import__',
            r'eval\(',
            r'exec\(',
            r'open\(',
            r'subprocess',
            r'os\.system',
        ]
        
        args_str = str(v)
        for pattern in dangerous_patterns:
            if re.search(pattern, args_str):
                raise ValueError("Potentially dangerous argument detected")
        
        return v

class AlertValidator(BaseModel):
    """Validador para alertas."""
    
    title: str = Field(..., min_length=1, max_length=200)
    severity: str = Field(..., regex='^(low|medium|high|critical)$')
    description: Optional[str] = Field(None, max_length=1000)
    host: str = Field(..., min_length=1, max_length=100)
    attack_id: Optional[str] = Field(None, regex='^T[0-9]{4}(\.[0-9]{3})?$')
    
    @validator('title')
    def sanitize_title(cls, v):
        # Sanitizar HTML
        import html
        return html.escape(v)
    
    @validator('description')
    def sanitize_description(cls, v):
        if v is None:
            return v
        import html
        return html.escape(v)

class ConfigValidator(BaseModel):
    """Validador para configuración."""
    
    key: str = Field(..., min_length=1, max_length=100)
    value: Any
    
    @validator('key')
    def validate_key(cls, v):
        # Prevenir keys peligrosas
        forbidden_keys = [
            'password',
            'api_key',
            'secret',
            'token',
            'private_key',
        ]
        
        if any(forbidden in v.lower() for forbidden in forbidden_keys):
            raise ValueError("Sensitive configuration keys are not allowed")
        
        return v

def validate_request_data(data: Dict[str, Any], validator_class: type) -> Dict[str, Any]:
    """Valida datos de request usando Pydantic."""
    try:
        validated = validator_class(**data)
        return validated.dict()
    except Exception as e:
        raise ValueError(f"Validation error: {str(e)}")
```

### 3.2 Sanitización de Outputs

```python
# argos/security/sanitization.py
import html
import json
from typing import Dict, Any

class OutputSanitizer:
    """Sanitizador de outputs para prevenir XSS."""
    
    @staticmethod
    def sanitize_string(value: str) -> str:
        """Sanitiza un string."""
        return html.escape(value)
    
    @staticmethod
    def sanitize_dict(data: Dict[str, Any]) -> Dict[str, Any]:
        """Sanitiza un diccionario recursivamente."""
        sanitized = {}
        
        for key, value in data.items():
            if isinstance(value, str):
                sanitized[key] = html.escape(value)
            elif isinstance(value, dict):
                sanitized[key] = OutputSanitizer.sanitize_dict(value)
            elif isinstance(value, list):
                sanitized[key] = OutputSanitizer.sanitize_list(value)
            else:
                sanitized[key] = value
        
        return sanitized
    
    @staticmethod
    def sanitize_list(data: List[Any]) -> List[Any]:
        """Sanitiza una lista recursivamente."""
        sanitized = []
        
        for item in data:
            if isinstance(item, str):
                sanitized.append(html.escape(item))
            elif isinstance(item, dict):
                sanitized.append(OutputSanitizer.sanitize_dict(item))
            elif isinstance(item, list):
                sanitized.append(OutputSanitizer.sanitize_list(item))
            else:
                sanitized.append(item)
        
        return sanitized
    
    @staticmethod
    def sanitize_json(data: Any) -> str:
        """Sanitiza datos antes de serializar a JSON."""
        if isinstance(data, (dict, list)):
            data = OutputSanitizer.sanitize_dict(data) if isinstance(data, dict) else OutputSanitizer.sanitize_list(data)
        
        return json.dumps(data)
```

---

## 4. SEGURIDAD DE DATOS

### 4.1 Encriptación

```python
# argos/security/encryption.py
from cryptography.fernet import Fernet
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC
import base64
import os

class EncryptionManager:
    """Gestor de encriptación."""
    
    def __init__(self, master_key: Optional[bytes] = None):
        if master_key is None:
            master_key = os.urandom(32)
        
        self.key = self._derive_key(master_key)
        self.cipher = Fernet(self.key)
    
    def _derive_key(self, master_key: bytes) -> bytes:
        """Deriva una clave desde la master key."""
        kdf = PBKDF2HMAC(
            algorithm=hashes.SHA256(),
            length=32,
            salt=b'argos_salt',  # En producción, usar salt único
            iterations=100000,
        )
        return base64.urlsafe_b64encode(kdf.derive(master_key))
    
    def encrypt(self, data: bytes) -> bytes:
        """Encripta datos."""
        return self.cipher.encrypt(data)
    
    def decrypt(self, encrypted_data: bytes) -> bytes:
        """Desencripta datos."""
        return self.cipher.decrypt(encrypted_data)
    
    def encrypt_string(self, data: str) -> str:
        """Encripta un string."""
        encrypted = self.encrypt(data.encode())
        return base64.urlsafe_b64encode(encrypted).decode()
    
    def decrypt_string(self, encrypted_data: str) -> str:
        """Desencripta un string."""
        encrypted = base64.urlsafe_b64decode(encrypted_data.encode())
        decrypted = self.decrypt(encrypted)
        return decrypted.decode()

class PasswordHasher:
    """Hasher de passwords usando Argon2."""
    
    @staticmethod
    def hash_password(password: str) -> str:
        """Hashea un password."""
        import argon2
        hasher = argon2.PasswordHasher(
            time_cost=3,  # Number of iterations
            memory_cost=65536,  # Memory in KiB
            parallelism=4,  # Number of parallel threads
            hash_len=32,  # Hash length
            salt_len=16,  # Salt length
        )
        return hasher.hash(password)
    
    @staticmethod
    def verify_password(hash: str, password: str) -> bool:
        """Verifica un password contra su hash."""
        import argon2
        try:
            hasher = argon2.PasswordHasher()
            hasher.verify(hash, password)
            return True
        except argon2.exceptions.VerifyMismatchError:
            return False
```

### 4.2 Data Masking

```python
# argos/security/masking.py
from typing import Dict, Any
import re

class DataMasker:
    """Masker de datos sensibles."""
    
    PATTERNS = {
        'email': r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}',
        'ip': r'\b(?:\d{1,3}\.){3}\d{1,3}\b',
        'credit_card': r'\b(?:\d[ -]*?){13,16}\b',
        'ssn': r'\b\d{3}-\d{2}-\d{4}\b',
        'api_key': r'[A-Za-z0-9]{32,}',
    }
    
    @classmethod
    def mask_email(cls, email: str) -> str:
        """Mask un email."""
        if '@' not in email:
            return email
        
        local, domain = email.split('@', 1)
        masked_local = local[:2] + '*' * (len(local) - 2)
        return f"{masked_local}@{domain}"
    
    @classmethod
    def mask_ip(cls, ip: str) -> str:
        """Mask una IP."""
        parts = ip.split('.')
        if len(parts) != 4:
            return ip
        
        return f"{parts[0]}.{parts[1]}.***.***"
    
    @classmethod
    def mask_credit_card(cls, card: str) -> str:
        """Mask un número de tarjeta de crédito."""
        card = re.sub(r'[^0-9]', '', card)
        if len(card) < 13:
            return card
        
        return '*' * (len(card) - 4) + card[-4:]
    
    @classmethod
    def mask_data(cls, data: Dict[str, Any], fields_to_mask: List[str]) -> Dict[str, Any]:
        """Mask campos específicos en un diccionario."""
        masked = data.copy()
        
        for field in fields_to_mask:
            if field in masked:
                value = masked[field]
                
                if isinstance(value, str):
                    if 'email' in field.lower():
                        masked[field] = cls.mask_email(value)
                    elif 'ip' in field.lower():
                        masked[field] = cls.mask_ip(value)
                    elif 'card' in field.lower() or 'credit' in field.lower():
                        masked[field] = cls.mask_credit_card(value)
                    else:
                        masked[field] = '*' * len(value)
        
        return masked
```

---

## 5. AUDIT LOGGING

### 5.1 Audit Logging Inmutable

```python
# argos/security/audit.py
import hashlib
import json
from datetime import datetime
from typing import Dict, Any, Optional
from pathlib import Path

class ImmutableAuditLog:
    """Log de auditoría inmutable con hash chaining."""
    
    def __init__(self, log_path: str = "logs/audit.log"):
        self.log_path = Path(log_path)
        self.log_path.parent.mkdir(parents=True, exist_ok=True)
        self.chain = []
        self.load_chain()
    
    def load_chain(self):
        """Carga la cadena de hashes existente."""
        if not self.log_path.exists():
            return
        
        with open(self.log_path, 'r') as f:
            for line in f:
                if line.strip():
                    entry = json.loads(line)
                    self.chain.append(entry)
    
    def add_entry(self, entry: Dict[str, Any]) -> str:
        """Agrega una entrada al log con hash chaining."""
        if self.chain:
            prev_hash = self.chain[-1]['hash']
        else:
            prev_hash = '0' * 64
        
        entry_with_metadata = {
            'timestamp': datetime.utcnow().isoformat(),
            'entry': entry,
            'prev_hash': prev_hash,
        }
        
        entry_str = json.dumps(entry_with_metadata, sort_keys=True)
        current_hash = hashlib.sha256(entry_str.encode()).hexdigest()
        
        audit_entry = {
            **entry_with_metadata,
            'hash': current_hash,
        }
        
        self.chain.append(audit_entry)
        self._append_to_file(audit_entry)
        
        return current_hash
    
    def _append_to_file(self, entry: Dict[str, Any]):
        """Agrega una entrada al archivo."""
        with open(self.log_path, 'a') as f:
            f.write(json.dumps(entry) + '\n')
    
    def verify_chain(self) -> bool:
        """Verifica la integridad de la cadena de hashes."""
        for i in range(1, len(self.chain)):
            current = self.chain[i]
            prev = self.chain[i - 1]
            
            # Verificar que el prev_hash coincida
            if current['prev_hash'] != prev['hash']:
                return False
            
            # Recalcular hash para verificar
            entry_copy = current.copy()
            stored_hash = entry_copy.pop('hash')
            entry_str = json.dumps(entry_copy, sort_keys=True)
            calculated_hash = hashlib.sha256(entry_str.encode()).hexdigest()
            
            if calculated_hash != stored_hash:
                return False
        
        return True
    
    def query_entries(self, filters: Optional[Dict[str, Any]] = None) -> list:
        """Query entries con filtros."""
        if filters is None:
            return self.chain
        
        results = []
        for entry in self.chain:
            match = True
            
            for key, value in filters.items():
                if key not in entry['entry']:
                    match = False
                    break
                
                if entry['entry'][key] != value:
                    match = False
                    break
            
            if match:
                results.append(entry)
        
        return results
    
    def get_entries_by_user(self, user_id: str) -> list:
        """Obtiene entries por usuario."""
        return self.query_entries({'user_id': user_id})
    
    def get_entries_by_action(self, action: str) -> list:
        """Obtiene entries por acción."""
        return self.query_entries({'action': action})
    
    def get_entries_by_time_range(self, start: str, end: str) -> list:
        """Obtiene entries por rango de tiempo."""
        results = []
        
        for entry in self.chain:
            timestamp = entry['timestamp']
            
            if start <= timestamp <= end:
                results.append(entry)
        
        return results

class AuditLogger:
    """Logger de auditoría de alto nivel."""
    
    def __init__(self, audit_log: ImmutableAuditLog):
        self.audit_log = audit_log
    
    def log_login(self, user_id: str, ip_address: str, success: bool):
        """Log un intento de login."""
        self.audit_log.add_entry({
            'action': 'login',
            'user_id': user_id,
            'ip_address': ip_address,
            'success': success,
            'timestamp': datetime.utcnow().isoformat(),
        })
    
    def log_logout(self, user_id: str, session_id: str):
        """Log un logout."""
        self.audit_log.add_entry({
            'action': 'logout',
            'user_id': user_id,
            'session_id': session_id,
            'timestamp': datetime.utcnow().isoformat(),
        })
    
    def log_permission_check(self, user_id: str, permission: str, granted: bool):
        """Log un check de permiso."""
        self.audit_log.add_entry({
            'action': 'permission_check',
            'user_id': user_id,
            'permission': permission,
            'granted': granted,
            'timestamp': datetime.utcnow().isoformat(),
        })
    
    def log_tool_execution(self, user_id: str, tool_name: str, arguments: Dict[str, Any]):
        """Log una ejecución de tool."""
        self.audit_log.add_entry({
            'action': 'tool_execution',
            'user_id': user_id,
            'tool_name': tool_name,
            'arguments': arguments,
            'timestamp': datetime.utcnow().isoformat(),
        })
    
    def log_config_change(self, user_id: str, key: str, old_value: Any, new_value: Any):
        """Log un cambio de configuración."""
        self.audit_log.add_entry({
            'action': 'config_change',
            'user_id': user_id,
            'key': key,
            'old_value': old_value,
            'new_value': new_value,
            'timestamp': datetime.utcnow().isoformat(),
        })
    
    def log_alert_action(self, user_id: str, alert_id: str, action: str):
        """Log una acción sobre una alerta."""
        self.audit_log.add_entry({
            'action': 'alert_action',
            'user_id': user_id,
            'alert_id': alert_id,
            'alert_action': action,
            'timestamp': datetime.utcnow().isoformat(),
        })
```

---

## 6. RATE LIMITING

### 6.1 Rate Limiting Implementation

```python
# argos/security/rate_limit.py
from collections import defaultdict
from typing import Dict, Optional
import time
from functools import wraps

class RateLimiter:
    """Limitador de rate simple en memoria."""
    
    def __init__(self):
        self.requests: Dict[str, list] = defaultdict(list)
    
    def is_allowed(self, key: str, limit: int, window: int) -> bool:
        """
        Verifica si una request está permitida.
        
        Args:
            key: Identificador único (e.g., user_id, ip_address)
            limit: Máximo número de requests
            window: Ventana de tiempo en segundos
        """
        now = time.time()
        
        # Remover requests viejas fuera de la ventana
        self.requests[key] = [
            timestamp for timestamp in self.requests[key]
            if now - timestamp < window
        ]
        
        # Verificar si excede el límite
        if len(self.requests[key]) >= limit:
            return False
        
        # Agregar request actual
        self.requests[key].append(now)
        return True
    
    def get_remaining(self, key: str, limit: int, window: int) -> int:
        """Obtiene requests restantes para un key."""
        now = time.time()
        
        # Remover requests viejas
        self.requests[key] = [
            timestamp for timestamp in self.requests[key]
            if now - timestamp < window
        ]
        
        return max(0, limit - len(self.requests[key]))
    
    def reset(self, key: str):
        """Resetea el contador para un key."""
        if key in self.requests:
            del self.requests[key]

# Rate limits por endpoint
RATE_LIMITS = {
    'api_events': {'limit': 100, 'window': 60},  # 100 requests/min
    'api_alerts': {'limit': 50, 'window': 60},   # 50 requests/min
    'api_tools': {'limit': 30, 'window': 60},    # 30 requests/min
    'api_config': {'limit': 10, 'window': 60},   # 10 requests/min
    'api_auth': {'limit': 5, 'window': 60},     # 5 requests/min
}

def rate_limit(endpoint: str):
    """Decorator para rate limiting."""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Obtener key (user_id o ip_address)
            # Esto depende de tu framework específico
            key = kwargs.get('user_id') or kwargs.get('ip_address', 'anonymous')
            
            limiter = RateLimiter()
            limits = RATE_LIMITS.get(endpoint, {'limit': 100, 'window': 60})
            
            if not limiter.is_allowed(key, limits['limit'], limits['window']):
                raise Exception(f"Rate limit exceeded for {endpoint}")
            
            return func(*args, **kwargs)
        return wrapper
    return decorator
```

---

## 7. SECURITY HEADERS

### 7.1 Middleware de Security Headers

```python
# argos/security/headers.py
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Middleware para agregar security headers."""
    
    async def dispatch(self, request: Request, call_next):
        response: Response = await call_next(request)
        
        # Security headers
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        response.headers["Content-Security-Policy"] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline';"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        
        return response
```

---

## 8. TESTING DE SEGURIDAD

### 8.1 Security Tests

```python
# tests/security/test_rbac.py
import pytest
from argos.security.rbac import RBACManager, Role, Permission

def test_role_permissions():
    """Test permisos por rol."""
    rbac = RBACManager()
    
    user = rbac.create_user("test_user", "test@example.com", Role.ANALYST)
    
    assert rbac.has_permission(user.id, Permission.READ_EVENTS)
    assert rbac.has_permission(user.id, Permission.READ_ALERTS)
    assert not rbac.has_permission(user.id, Permission.WRITE_CONFIG)
    assert not rbac.has_permission(user.id, Permission.SYSTEM_ADMIN)

def test_permission_grant():
    """Test otorgar permisos."""
    rbac = RBACManager()
    
    user = rbac.create_user("test_user", "test@example.com", Role.OPERATOR)
    
    assert not rbac.has_permission(user.id, Permission.WRITE_ALERTS)
    
    rbac.grant_permission(user.id, Permission.WRITE_ALERTS)
    
    assert rbac.has_permission(user.id, Permission.WRITE_ALERTS)

def test_permission_revoke():
    """Test revocar permisos."""
    rbac = RBACManager()
    
    user = rbac.create_user("test_user", "test@example.com", Role.ADMIN)
    
    assert rbac.has_permission(user.id, Permission.SYSTEM_ADMIN)
    
    rbac.revoke_permission(user.id, Permission.SYSTEM_ADMIN)
    
    assert not rbac.has_permission(user.id, Permission.SYSTEM_ADMIN)

# tests/security/test_validation.py
import pytest
from argos.security.validation import EventQueryValidator, ToolExecutionValidator

def test_event_query_validation():
    """Test validación de query de eventos."""
    # Valid
    validator = EventQueryValidator(limit=100, offset=0)
    assert validator.limit == 100
    
    # Invalid
    with pytest.raises(ValueError):
        EventQueryValidator(limit=2000)  # Exceeds max
    
    with pytest.raises(ValueError):
        EventQueryValidator(limit=-1)  # Negative

def test_tool_execution_validation():
    """Test validación de ejecución de tools."""
    # Valid
    validator = ToolExecutionValidator(
        tool_name="query_events",
        arguments={"filters": {"severity": "high"}}
    )
    assert validator.tool_name == "query_events"
    
    # Invalid tool name
    with pytest.raises(ValueError):
        ToolExecutionValidator(tool_name="invalid;tool")
    
    # Dangerous arguments
    with pytest.raises(ValueError):
        ToolExecutionValidator(
            tool_name="query_events",
            arguments={"command": "__import__('os').system('ls')"}
        )

# tests/security/test_audit.py
import pytest
from argos.security.audit import ImmutableAuditLog, AuditLogger

def test_audit_chain_integrity():
    """Test integridad de cadena de auditoría."""
    audit_log = ImmutableAuditLog(":memory:")
    
    # Agregar entries
    audit_log.add_entry({"action": "test", "user_id": "user1"})
    audit_log.add_entry({"action": "test", "user_id": "user2"})
    
    # Verificar integridad
    assert audit_log.verify_chain() == True
    
    # Modificar una entry (simulado)
    audit_log.chain[1]['entry']['user_id'] = 'hacker'
    
    # Verificar que ahora falla
    assert audit_log.verify_chain() == False

def test_audit_query():
    """Test query de auditoría."""
    audit_log = ImmutableAuditLog(":memory:")
    
    audit_log.add_entry({"action": "login", "user_id": "user1"})
    audit_log.add_entry({"action": "logout", "user_id": "user1"})
    audit_log.add_entry({"action": "login", "user_id": "user2"})
    
    # Query por usuario
    user1_entries = audit_log.get_entries_by_user("user1")
    assert len(user1_entries) == 2
    
    # Query por acción
    login_entries = audit_log.get_entries_by_action("login")
    assert len(login_entries) == 2
```

### 8.2 Penetration Testing Checklist

```markdown
# Penetration Testing Checklist

## Authentication
- [ ] Test weak passwords
- [ ] Test password reset flows
- [ ] Test session hijacking
- [ ] Test MFA bypass
- [ ] Test account enumeration

## Authorization
- [ ] Test horizontal privilege escalation
- [ ] Test vertical privilege escalation
- [ ] Test IDOR (Insecure Direct Object References)
- [ ] Test parameter tampering
- [ ] Test mass assignment

## Input Validation
- [ ] Test SQL injection
- [ ] Test XSS (Cross-Site Scripting)
- [ ] Test command injection
- [ ] Test path traversal
- [ ] Test XXE (XML External Entity)

## API Security
- [ ] Test rate limiting
- [ ] Test mass assignment
- [ ] Test improper assets management
- [ ] Test security misconfiguration
- [ ] Test sensitive data exposure

## Session Management
- [ ] Test session fixation
- [ ] Test session timeout
- [ ] Test session revocation
- [ ] Test concurrent sessions
- [ ] Test session storage

## Data Protection
- [ ] Test data encryption at rest
- [ ] Test data encryption in transit
- [ ] Test sensitive data exposure
- [ ] Test data masking
- [ ] Test data retention

## Audit & Logging
- [ ] Test audit log tampering
- [ ] Test log injection
- [ ] Test log availability
- [ ] Test log completeness
- [ ] Test log retention
```

---

## 9. COMPLIANCE

### 9.1 NIST CSF Mapping

```python
# argos/security/compliance.py
from enum import Enum

class NISTFunction(Enum):
    """Funciones del NIST Cybersecurity Framework."""
    IDENTIFY = "ID"
    PROTECT = "PR"
    DETECT = "DE"
    RESPOND = "RS"
    RECOVER = "RC"

class NISTCategory(Enum):
    """Categorías del NIST CSF."""
    # Identify
    ASSET_MANAGEMENT = "ID.AM"
    GOVERNANCE = "ID.GV"
    RISK_ASSESSMENT = "ID.RA"
    SUPPLY_CHAIN = "ID.SC"
    
    # Protect
    ACCESS_CONTROL = "PR.AC"
    AWARENESS_TRAINING = "PR.AT"
    DATA_SECURITY = "PR.DS"
    INFO_PROTECTION = "PR.IP"
    MAINTENANCE = "PR.MA"
    PROTECTIVE_TECHNOLOGY = "PR.PS"
    
    # Detect
    ANOMALIES_EVENTS = "DE.AE"
    SECURITY_CONTINUOUS = "DE.CM"
    AWARENESS_EVENTS = "DE.DP"
    
    # Respond
    RESPONSE_PLANNING = "RS.RP"
    COMMUNICATIONS = "RS.CO"
    ANALYSIS = "RS.AN"
    MITIGATION = "RS.MI"
    IMPROVEMENTS = "RS.IM"
    
    # Recover
    RECOVERY_PLANNING = "RC.RP"
    IMPROVEMENTS = "RC.IM"
    COMMUNICATIONS = "RC.CO"

NIST_MAPPING = {
    "rbac": [NISTCategory.ACCESS_CONTROL],
    "mfa": [NISTCategory.ACCESS_CONTROL, NISTCategory.AWARENESS_TRAINING],
    "encryption": [NISTCategory.DATA_SECURITY],
    "audit_logging": [NISTCategory.ANOMALIES_EVENTS, NISTCategory.SECURITY_CONTINUOUS],
    "incident_response": [NISTCategory.RESPONSE_PLANNING, NISTCategory.ANALYSIS],
    "vulnerability_management": [NISTCategory.MAINTENANCE],
    "security_training": [NISTCategory.AWARENESS_TRAINING],
}

def get_nist_coverage(feature: str) -> list[NISTCategory]:
    """Obtiene categorías NIST cubiertas por una feature."""
    return NIST_MAPPING.get(feature, [])
```

### 9.2 CIS Controls Mapping

```python
CIS_CONTROLS = {
    "inventory": "CIS Control 1: Inventory and Control of Enterprise Assets",
    "software": "CIS Control 2: Inventory and Control of Software Assets",
    "config": "CIS Control 3: Secure Configuration of Enterprise Assets and Software",
    "vulnerability": "CIS Control 4: Vulnerability Management",
    "access": "CIS Control 5: Account Management",
    "auth": "CIS Control 6: Access Control Management",
    "logging": "CIS Control 7: Continuous Vulnerability Management",
    "email": "CIS Control 8: Email and Web Browser Protections",
    "malware": "CIS Control 9: Malware Defenses",
    "data": "CIS Control 10: Data Recovery",
    "network": "CIS Control 11: Secure Network Infrastructure",
    "network_device": "CIS Control 12: Network Device Management",
    "network_monitoring": "CIS Control 13: Network Monitoring and Defense",
    "info_protection": "CIS Control 14: Security Awareness and Skills Training",
    "service": "CIS Control 15: Service Provider Management",
    "app": "CIS Control 16: Application Software Security",
    "incident": "CIS Control 17: Incident Response Management",
    "penetration": "CIS Control 18: Penetration Testing",
}

def get_cis_controls(feature: str) -> list[str]:
    """Obtiene controles CIS cubiertos por una feature."""
    mapping = {
        "rbac": [CIS_CONTROLS["access"], CIS_CONTROLS["auth"]],
        "mfa": [CIS_CONTROLS["auth"]],
        "encryption": [CIS_CONTROLS["data"]],
        "audit_logging": [CIS_CONTROLS["logging"], CIS_CONTROLS["network_monitoring"]],
        "incident_response": [CIS_CONTROLS["incident"]],
    }
    return mapping.get(feature, [])
```

---

## 10. VALIDACIÓN DE COMPONENTES

### 10.1 Plugin Validation

```python
# argos/security/plugin_validation.py
import hashlib
import json
from pathlib import Path
from typing import Dict, Any, Optional

class PluginValidator:
    """Validador de plugins."""
    
    def __init__(self):
        self.trusted_sources: set = set()
    
    def add_trusted_source(self, source: str):
        """Agrega una fuente confiable."""
        self.trusted_sources.add(source)
    
    def validate_plugin(self, plugin_path: Path) -> tuple[bool, Optional[str]]:
        """
        Valida un plugin.
        
        Returns:
            (is_valid, error_message)
        """
        # Verificar que plugin.json existe
        manifest_path = plugin_path / "plugin.json"
        if not manifest_path.exists():
            return False, "plugin.json not found"
        
        # Cargar y validar manifest
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
        except json.JSONDecodeError as e:
            return False, f"Invalid JSON in plugin.json: {e}"
        
        # Validar campos requeridos
        required_fields = ["name", "version", "description", "entry_point"]
        for field in required_fields:
            if field not in manifest:
                return False, f"Missing required field: {field}"
        
        # Validar versión
        if not self._validate_version(manifest["version"]):
            return False, "Invalid version format"
        
        # Verificar source si es remoto
        if manifest.get("source", {}).get("type") == "remote":
            if not self._validate_remote_source(manifest["source"]):
                return False, "Untrusted remote source"
        
        # Validar entry_point
        if not self._validate_entry_point(manifest["entry_point"]):
            return False, "Invalid entry_point format"
        
        # Calcular hash del plugin
        plugin_hash = self._calculate_plugin_hash(plugin_path)
        
        return True, None
    
    def _validate_version(self, version: str) -> bool:
        """Valida formato de versión."""
        import re
        return bool(re.match(r'^\d+\.\d+\.\d+$', version))
    
    def _validate_remote_source(self, source: Dict[str, Any]) -> bool:
        """Valida source remoto."""
        url = source.get("url", "")
        sha = source.get("sha", "")
        
        # Verificar que URL sea de fuente confiable
        if not any(trusted in url for trusted in self.trusted_sources):
            return False
        
        # Verificar que SHA esté presente
        if not sha or len(sha) != 40:
            return False
        
        return True
    
    def _validate_entry_point(self, entry_point: str) -> bool:
        """Valida formato de entry_point."""
        # Debe ser formato: module.path:ClassName
        if ":" not in entry_point:
            return False
        
        module, class_name = entry_point.rsplit(":", 1)
        
        # Validar module path
        if not module or not class_name:
            return False
        
        # Validar que no tenga paths relativos peligrosos
        if ".." in module:
            return False
        
        return True
    
    def _calculate_plugin_hash(self, plugin_path: Path) -> str:
        """Calcula hash SHA256 del plugin."""
        import hashlib
        
        hash_obj = hashlib.sha256()
        
        for file in plugin_path.rglob("*"):
            if file.is_file():
                with open(file, "rb") as f:
                    hash_obj.update(f.read())
        
        return hash_obj.hexdigest()
```

### 10.2 Prompt Validation

```python
# argos/security/prompt_validation.py
from typing import List, Optional

class PromptValidator:
    """Validador de prompts de IA."""
    
    DANGEROUS_PATTERNS = [
        r'ignore\s+(all\s+)?(previous\s+)?instructions',
        r'disregard\s+(all\s+)?(previous\s+)?instructions',
        r'forget\s+(all\s+)?(previous\s+)?instructions',
        r'override\s+(all\s+)?(previous\s+)?instructions',
        r'bypass\s+(all\s+)?(previous\s+)?instructions',
        r'jailbreak',
        r'roleplay\s+as',
        r'pretend\s+to\s+be',
        r'act\s+as',
        r'simulate\s+being',
    ]
    
    @classmethod
    def validate_prompt(cls, prompt: str) -> tuple[bool, Optional[str]]:
        """
        Valida un prompt.
        
        Returns:
            (is_valid, error_message)
        """
        import re
        
        # Verificar patrones peligrosos
        for pattern in cls.DANGEROUS_PATTERNS:
            if re.search(pattern, prompt, re.IGNORECASE):
                return False, f"Potentially dangerous pattern detected: {pattern}"
        
        # Verificar longitud razonable
        if len(prompt) > 10000:
            return False, "Prompt too long"
        
        # Verificar caracteres sospechosos
        suspicious_chars = ['\x00', '\x01', '\x02', '\x03', '\x04', '\x05']
        if any(char in prompt for char in suspicious_chars):
            return False, "Suspicious characters detected"
        
        return True, None
    
    @classmethod
    def sanitize_prompt(cls, prompt: str) -> str:
        """Sanitiza un prompt removiendo patrones peligrosos."""
        import re
        
        sanitized = prompt
        
        for pattern in cls.DANGEROUS_PATTERNS:
            sanitized = re.sub(pattern, '[REDACTED]', sanitized, flags=re.IGNORECASE)
        
        return sanitized
```

---

## 11. MONITOREO DE SEGURIDAD

### 11.1 Security Metrics

```python
# argos/security/metrics.py
from prometheus_client import Counter, Histogram, Gauge

# Security metrics
AUTH_ATTEMPTS_TOTAL = Counter(
    'auth_attempts_total',
    'Total authentication attempts',
    ['method', 'status']
)

AUTH_FAILURES_TOTAL = Counter(
    'auth_failures_total',
    'Total authentication failures',
    ['reason']
)

PERMISSION_DENIALS_TOTAL = Counter(
    'permission_denials_total',
    'Total permission denials',
    ['permission', 'user_role']
)

RATE_LIMIT_VIOLATIONS_TOTAL = Counter(
    'rate_limit_violations_total',
    'Total rate limit violations',
    ['endpoint']
)

SECURITY_EVENTS_TOTAL = Counter(
    'security_events_total',
    'Total security events',
    ['type', 'severity']
)

VULNERABILITY_SCANS_TOTAL = Counter(
    'vulnerability_scans_total',
    'Total vulnerability scans',
    ['status']
)

ACTIVE_SESSIONS = Gauge(
    'active_sessions',
    'Number of active sessions'
)

FAILED_LOGIN_ATTEMPTS = Gauge(
    'failed_login_attempts',
    'Number of failed login attempts in last hour'
)
```

---

## 12. INCIDENT RESPONSE

### 12.1 Incident Response Plan

```markdown
# Incident Response Plan

## Phases

### 1. Preparation
- Establish incident response team
- Define roles and responsibilities
- Create communication channels
- Prepare response tools and procedures
- Conduct regular drills

### 2. Identification
- Monitor security alerts
- Analyze potential incidents
- Classify incident severity
- Document initial findings

### 3. Containment
- Isolate affected systems
- Block malicious IPs/domains
- Disable compromised accounts
- Implement temporary controls

### 4. Eradication
- Remove malware
- Patch vulnerabilities
- Close attack vectors
- Verify system integrity

### 5. Recovery
- Restore from clean backups
- Rebuild compromised systems
- Monitor for recurrence
- Validate functionality

### 6. Lessons Learned
- Conduct post-incident review
- Document timeline and actions
- Identify root causes
- Update procedures and controls

## Severity Levels

### Critical (P0)
- Immediate response required
- Full incident response team activated
- Executive notification required
- 24/7 monitoring until resolved

### High (P1)
- Response within 1 hour
- Core incident response team activated
- Management notification required
- Business hours monitoring

### Medium (P2)
- Response within 4 hours
- Relevant team members activated
- Team lead notification
- Business hours monitoring

### Low (P3)
- Response within 24 hours
- Assigned team member responds
- Team lead notification
- Normal monitoring
```

---

## 13. PRÓXIMOS PASOS

1. **Inmediato:**
   - Implementar RBAC avanzado
   - Agregar MFA
   - Implementar audit logging inmutable

2. **Corto plazo (1 semana):**
   - Implementar validación de inputs
   - Agregar security headers
   - Implementar rate limiting

3. **Mediano plazo (2 semanas):**
   - Implementar encriptación de datos
   - Agregar data masking
   - Implementar plugin validation

4. **Largo plazo (1 mes):**
   - Completar compliance mapping
   - Ejecutar penetration testing
   - Implementar incident response plan

---

## CONCLUSIÓN

Este documento establece un framework completo de seguridad y validación para ARGOS nivel enterprise, cubriendo autenticación, autorización, validación de inputs, seguridad de datos, audit logging, y compliance con estándares de la industria.
