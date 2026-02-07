"""
Servicio IMAP: buscar email, descargar adjunto, descomprimir.
"""

import email
import gzip
import imaplib
import json
import tarfile
import tempfile
from email.header import decode_header
from pathlib import Path
from typing import Optional

from loguru import logger

from app.config import settings

_last_processed_uid: Optional[str] = None


def _connect() -> imaplib.IMAP4_SSL:
    """Conecta a Gmail via IMAP SSL."""
    mail = imaplib.IMAP4_SSL("imap.gmail.com")
    mail.login(settings.gmail_email, settings.gmail_app_password)
    return mail


def _decode_header_value(value: str) -> str:
    """Decodifica un header de email."""
    decoded_parts = decode_header(value)
    result = []
    for part, charset in decoded_parts:
        if isinstance(part, bytes):
            result.append(part.decode(charset or "utf-8", errors="replace"))
        else:
            result.append(part)
    return "".join(result)


def fetch_latest_backup() -> Optional[Path]:
    """
    Busca el email mas reciente con el subject configurado,
    descarga el adjunto y lo descomprime a JSON.
    Retorna el Path al JSON o None si no hay email nuevo.
    """
    global _last_processed_uid

    if not settings.gmail_email or not settings.gmail_app_password:
        logger.warning("Credenciales Gmail no configuradas")
        return None

    mail = None
    try:
        mail = _connect()
        mail.select("INBOX")

        subject = settings.gmail_search_subject
        status, data = mail.uid("search", None, f'(SUBJECT "{subject}")')

        if status != "OK" or not data[0]:
            logger.info("No se encontraron emails con subject: {}", subject)
            return None

        uids = data[0].split()
        latest_uid = uids[-1].decode()

        if latest_uid == _last_processed_uid:
            logger.debug("Email ya procesado (UID: {}), saltando", latest_uid)
            return None

        logger.info("Nuevo email encontrado (UID: {})", latest_uid)

        status, msg_data = mail.uid("fetch", latest_uid, "(RFC822)")
        if status != "OK":
            logger.error("Error descargando email UID: {}", latest_uid)
            return None

        msg = email.message_from_bytes(msg_data[0][1])

        # Buscar adjunto
        attachment_data = None
        attachment_name = None

        for part in msg.walk():
            if part.get_content_maintype() == "multipart":
                continue

            filename = part.get_filename()
            if filename:
                filename = _decode_header_value(filename)
                if filename.endswith((".gz", ".tar.gz", ".json")):
                    attachment_data = part.get_payload(decode=True)
                    attachment_name = filename
                    break

        if not attachment_data:
            logger.warning("Email sin adjunto valido (.gz/.tar.gz/.json)")
            return None

        logger.info("Adjunto descargado: {} ({:.1f} KB)", attachment_name, len(attachment_data) / 1024)

        # Descomprimir
        json_data = _decompress(attachment_data, attachment_name)
        if json_data is None:
            return None

        # Guardar JSON formateado
        output_path = settings.json_file_path
        output_path.parent.mkdir(parents=True, exist_ok=True)

        parsed = json.loads(json_data)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(parsed, f, indent=3, ensure_ascii=False)

        logger.info("JSON guardado: {} ({:.1f} KB)", output_path.name, output_path.stat().st_size / 1024)

        _last_processed_uid = latest_uid
        return output_path

    except imaplib.IMAP4.error as e:
        logger.error("Error IMAP: {}", e)
        return None
    except Exception as e:
        logger.error("Error en fetch_latest_backup: {}", e)
        return None
    finally:
        if mail:
            try:
                mail.close()
                mail.logout()
            except Exception:
                pass


def _decompress(data: bytes, filename: str) -> Optional[bytes]:
    """Descomprime .gz o .tar.gz y retorna el contenido JSON como bytes."""
    try:
        if filename.endswith(".tar.gz"):
            import io

            with tarfile.open(fileobj=io.BytesIO(data), mode="r:gz") as tar:
                for member in tar.getmembers():
                    if member.name.endswith(".json"):
                        f = tar.extractfile(member)
                        if f:
                            return f.read()
                # Si no hay .json, extraer el primer archivo
                members = tar.getmembers()
                if members:
                    f = tar.extractfile(members[0])
                    if f:
                        return f.read()
            logger.error("No se encontro contenido en tar.gz")
            return None

        elif filename.endswith(".gz"):
            return gzip.decompress(data)

        elif filename.endswith(".json"):
            return data

        else:
            logger.error("Formato no soportado: {}", filename)
            return None

    except Exception as e:
        logger.error("Error descomprimiendo {}: {}", filename, e)
        return None
