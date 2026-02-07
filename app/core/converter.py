"""
SQLiteGenerator refactorizado desde main.py.
Convierte JSON formato SNAP ORM a SQLite.
"""

import json
import re
import sqlite3
import threading
from pathlib import Path
from typing import Any, Dict, List

from loguru import logger

_rebuild_lock = threading.Lock()


class SQLiteGenerator:
    def __init__(self, json_file: str | Path, db_file: str | Path):
        self.json_file = Path(json_file)
        self.db_file = Path(db_file)
        self.data = None

    def load_json(self) -> Dict[str, Any]:
        """Carga y valida el archivo JSON formato SNAP."""
        if not self.json_file.exists():
            raise FileNotFoundError(f"El archivo JSON no existe: {self.json_file}")

        with open(self.json_file, "r", encoding="utf-8") as f:
            self.data = json.load(f)

        required_keys = ["metadata", "tables"]
        missing = [k for k in required_keys if k not in self.data]
        if missing:
            raise ValueError(f"Claves requeridas no encontradas: {', '.join(missing)}")

        if not self.data["tables"]:
            raise ValueError("La seccion 'tables' esta vacia")

        metadata = self.data["metadata"]
        logger.info(
            "JSON cargado: {} | {} tablas | {} filas | exportado: {}",
            self.json_file.name,
            len(self.data["tables"]),
            metadata.get("total_rows", "N/A"),
            metadata.get("exported_at", "N/A"),
        )
        return self.data

    def validate_json_structure(self):
        """Valida la estructura del JSON antes de procesar."""
        issues = []
        warnings = []

        for table_name, table_info in self.data["tables"].items():
            if "structure" not in table_info:
                issues.append(f"Tabla '{table_name}': falta 'structure'")
                continue

            structure = table_info["structure"]
            if not structure:
                issues.append(f"Tabla '{table_name}': sin columnas definidas")
                continue

            for i, col in enumerate(structure):
                if "column_name" not in col:
                    issues.append(f"Tabla '{table_name}', col {i}: falta 'column_name'")
                if "data_type" not in col:
                    issues.append(f"Tabla '{table_name}', col {i}: falta 'data_type'")

            if "data" not in table_info:
                warnings.append(f"Tabla '{table_name}': falta 'data'")
            elif not table_info["data"]:
                warnings.append(f"Tabla '{table_name}': datos vacios")

            if "row_count" in table_info and "data" in table_info:
                expected = table_info["row_count"]
                actual = len(table_info["data"]) if table_info["data"] else 0
                if expected != actual:
                    warnings.append(
                        f"Tabla '{table_name}': row_count ({expected}) != datos ({actual})"
                    )

        if issues:
            for issue in issues:
                logger.error(issue)
            raise ValueError("JSON tiene problemas estructurales")

        for w in warnings:
            logger.warning(w)

        total = sum(len(t.get("data", [])) for t in self.data["tables"].values())
        logger.info("Estructura valida: {} tablas, {} registros", len(self.data["tables"]), total)

    def map_snap_column_type(self, snap_type: str) -> str:
        """Mapea tipos del formato SNAP a SQLite."""
        if not snap_type:
            return "TEXT"

        snap_type = snap_type.upper()

        type_mapping = {
            "VARCHAR": "TEXT",
            "INTEGER": "INTEGER",
            "BOOLEAN": "INTEGER",
            "TEXT": "TEXT",
            "REAL": "REAL",
            "BLOB": "BLOB",
            "DATETIME": "TEXT",
            "DATE": "TEXT",
            "TIMESTAMP": "TEXT",
        }

        return type_mapping.get(snap_type, "TEXT")

    def process_default_value(self, default_val: Any) -> str:
        """Procesa valores por defecto y los convierte a SQL valido."""
        if default_val is None:
            return "NULL"

        default_str = str(default_val)

        if "ScalarElementColumnDefault" in default_str:
            match = re.search(r"ScalarElementColumnDefault\('([^']+)'\)", default_str)
            if match:
                return f"'{match.group(1)}'"
            return "NULL"

        if any(
            obj_type in default_str
            for obj_type in ["ColumnDefault", "DefaultClause", "Scalar"]
        ):
            return "NULL"

        if default_str.upper() in [
            "NULL",
            "CURRENT_TIMESTAMP",
            "CURRENT_DATE",
            "CURRENT_TIME",
        ]:
            return default_str.upper()

        if isinstance(default_val, bool):
            return "1" if default_val else "0"

        if isinstance(default_val, (int, float)):
            return str(default_val)

        if isinstance(default_val, str):
            escaped_val = default_str.replace("'", "''")
            return f"'{escaped_val}'"

        return "NULL"

    def create_table_sql(self, table_name: str, structure: List[Dict[str, Any]]) -> str:
        """Genera el SQL CREATE TABLE para una tabla formato SNAP."""
        column_definitions = []

        for col in structure:
            col_name = col.get("column_name", "")
            if not col_name:
                continue

            col_type = self.map_snap_column_type(col.get("data_type", "TEXT"))
            definition = f"`{col_name}` {col_type}"

            if col.get("primary_key", False):
                definition += " PRIMARY KEY"

            if col.get("not_null", False) and not col.get("primary_key", False):
                definition += " NOT NULL"

            if "default" in col and col["default"] is not None:
                default_clause = self.process_default_value(col["default"])
                if default_clause:
                    definition += f" DEFAULT {default_clause}"

            column_definitions.append(definition)

        if not column_definitions:
            raise ValueError(f"No hay columnas validas para tabla {table_name}")

        columns_sql = ",\n    ".join(column_definitions)
        return f"CREATE TABLE `{table_name}` (\n    {columns_sql}\n);"

    def create_database(self, db_path: Path | None = None):
        """Crea la base de datos SQLite con todas las tablas."""
        target = db_path or self.db_file

        if target.exists():
            target.unlink()

        conn = sqlite3.connect(str(target))
        cursor = conn.cursor()

        try:
            for table_name, table_info in self.data["tables"].items():
                if "structure" not in table_info:
                    continue

                structure = table_info["structure"]
                create_sql = self.create_table_sql(table_name, structure)
                cursor.execute(create_sql)

                actual_count = len(table_info.get("data", []))
                logger.debug(
                    "Tabla {}: {} columnas, {} registros",
                    table_name,
                    len(structure),
                    actual_count,
                )

            conn.commit()
            logger.info("Todas las tablas creadas exitosamente")
        except Exception as e:
            conn.rollback()
            raise Exception(f"Error creando tablas: {e}")
        finally:
            conn.close()

    def insert_data(self, db_path: Path | None = None):
        """Inserta los datos en las tablas."""
        target = db_path or self.db_file

        conn = sqlite3.connect(str(target))
        cursor = conn.cursor()

        try:
            total_inserted = 0

            for table_name, table_info in self.data["tables"].items():
                table_data = table_info.get("data", [])
                if not table_data:
                    continue

                if not isinstance(table_data, list) or not table_data:
                    continue

                first_record = table_data[0]
                if not isinstance(first_record, dict):
                    continue

                columns = list(first_record.keys())
                placeholders = ", ".join(["?" for _ in columns])
                columns_sql = ", ".join([f"`{col}`" for col in columns])
                insert_sql = f"INSERT INTO `{table_name}` ({columns_sql}) VALUES ({placeholders})"

                rows_to_insert = []
                for record in table_data:
                    if not isinstance(record, dict):
                        continue
                    row = []
                    for col in columns:
                        value = record.get(col)
                        if value is None or value == "NULL" or value == "":
                            value = None
                        elif isinstance(value, str) and value.lower() == "null":
                            value = None
                        elif isinstance(value, bool):
                            value = 1 if value else 0
                        row.append(value)
                    rows_to_insert.append(row)

                if rows_to_insert:
                    cursor.executemany(insert_sql, rows_to_insert)
                    total_inserted += len(rows_to_insert)
                    logger.debug("Tabla {}: {} registros insertados", table_name, len(rows_to_insert))

            conn.commit()
            logger.info("Datos insertados: {} registros totales", total_inserted)
        except Exception as e:
            conn.rollback()
            raise Exception(f"Error insertando datos: {e}")
        finally:
            conn.close()

    def generate(self):
        """Ejecuta el proceso completo de generacion."""
        logger.info("Iniciando generacion de DB: {} -> {}", self.json_file.name, self.db_file.name)

        self.load_json()
        self.validate_json_structure()
        self.create_database()
        self.insert_data()

        size_kb = self.db_file.stat().st_size / 1024
        logger.info("DB creada exitosamente: {:.1f} KB", size_kb)

    def rebuild(self) -> bool:
        """
        Rebuild atomico: genera en archivo temporal y renombra.
        Usa lock para evitar rebuilds simultaneos.
        Retorna True si fue exitoso.
        """
        if not _rebuild_lock.acquire(blocking=False):
            logger.warning("Rebuild ya en progreso, saltando")
            return False

        try:
            tmp_db = self.db_file.parent / "database_tmp.db"
            logger.info("Rebuild iniciado -> {}", tmp_db.name)

            self.load_json()
            self.validate_json_structure()
            self.create_database(db_path=tmp_db)
            self.insert_data(db_path=tmp_db)

            # Swap atomico
            if self.db_file.exists():
                self.db_file.unlink()
            tmp_db.rename(self.db_file)

            size_kb = self.db_file.stat().st_size / 1024
            logger.info("Rebuild completado: {:.1f} KB", size_kb)
            return True

        except Exception as e:
            logger.error("Error en rebuild: {}", e)
            # Limpiar temporal si existe
            tmp_db = self.db_file.parent / "database_tmp.db"
            if tmp_db.exists():
                tmp_db.unlink()
            raise
        finally:
            _rebuild_lock.release()
