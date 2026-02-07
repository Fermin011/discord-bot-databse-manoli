#!/usr/bin/env python3
"""
Script para crear una base de datos SQLite3 desde un archivo JSON
formato SNAP ORM que contiene tanto la estructura como los datos.
"""

import json
import sqlite3
import sys
import os
from pathlib import Path
from typing import Dict, List, Any


class SQLiteGenerator:
    def __init__(self, json_file: str, db_file: str):
        self.json_file = Path(json_file)
        self.db_file = Path(db_file)
        self.data = None
        
        # Verificar que el archivo JSON existe
        if not self.json_file.exists():
            raise FileNotFoundError(f"El archivo JSON no existe: {self.json_file}")
        
        # Verificar que el directorio de destino existe
        db_dir = self.db_file.parent
        if not db_dir.exists():
            db_dir.mkdir(parents=True, exist_ok=True)
            print(f"✓ Directorio creado: {db_dir}")
    
    def load_json(self) -> Dict[str, Any]:
        """Carga y valida el archivo JSON formato SNAP."""
        try:
            with open(self.json_file, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
            
            # Validar estructura básica para el formato SNAP
            required_keys = ['metadata', 'tables']
            missing_keys = []
            
            for key in required_keys:
                if key not in self.data:
                    missing_keys.append(key)
            
            if missing_keys:
                raise ValueError(f"Claves requeridas no encontradas: {', '.join(missing_keys)}")
            
            # Validar que tables no esté vacío
            if not self.data['tables']:
                raise ValueError("La sección 'tables' está vacía")
            
            # Mostrar información del JSON cargado
            tables_count = len(self.data['tables'])
            metadata = self.data['metadata']
            
            print(f"✓ JSON cargado exitosamente: {self.json_file}")
            print(f"  - Sistema: {metadata.get('backup_system', 'N/A')}")
            print(f"  - Base de datos origen: {metadata.get('database_file', 'N/A')}")
            print(f"  - Total de tablas: {tables_count}")
            print(f"  - Total de filas: {metadata.get('total_rows', 'N/A')}")
            print(f"  - Exportado: {metadata.get('exported_at', 'N/A')}")
            
            return self.data
            
        except FileNotFoundError:
            raise FileNotFoundError(f"Archivo JSON no encontrado: {self.json_file}")
        except json.JSONDecodeError as e:
            raise ValueError(f"Error al parsear JSON en línea {e.lineno}: {e.msg}")
        except Exception as e:
            raise ValueError(f"Error inesperado al cargar JSON: {e}")
    
    def validate_json_structure(self):
        """Valida la estructura del JSON antes de procesar."""
        print("\n🔍 Validando estructura del JSON...")
        
        issues = []
        warnings = []
        
        # Verificar cada tabla
        for table_name, table_info in self.data['tables'].items():
            # Verificar que tenga la estructura requerida
            if 'structure' not in table_info:
                issues.append(f"Tabla '{table_name}': falta la sección 'structure'")
                continue
            
            structure = table_info['structure']
            if not structure or len(structure) == 0:
                issues.append(f"Tabla '{table_name}': no tiene columnas definidas")
                continue
            
            # Verificar que cada columna tenga los campos requeridos
            for i, col in enumerate(structure):
                if 'column_name' not in col:
                    issues.append(f"Tabla '{table_name}', columna {i}: falta 'column_name'")
                if 'data_type' not in col:
                    issues.append(f"Tabla '{table_name}', columna {i}: falta 'data_type'")
            
            # Verificar datos
            if 'data' not in table_info:
                warnings.append(f"Tabla '{table_name}': falta la sección 'data'")
            elif not table_info['data']:
                warnings.append(f"Tabla '{table_name}': datos vacíos")
            
            # Verificar consistencia row_count
            if 'row_count' in table_info and 'data' in table_info:
                expected_count = table_info['row_count']
                actual_count = len(table_info['data']) if table_info['data'] else 0
                if expected_count != actual_count:
                    warnings.append(f"Tabla '{table_name}': row_count ({expected_count}) no coincide con datos reales ({actual_count})")
        
        # Mostrar resultados de validación
        if issues:
            print("❌ Problemas encontrados:")
            for issue in issues:
                print(f"   - {issue}")
            raise ValueError("El JSON tiene problemas estructurales que impiden continuar")
        
        if warnings:
            print("⚠️  Advertencias:")
            for warning in warnings:
                print(f"   - {warning}")
        
        tables_count = len(self.data['tables'])
        total_records = sum(len(table.get('data', [])) for table in self.data['tables'].values())
        print(f"✓ Estructura válida: {tables_count} tablas, {total_records} registros totales")
    
    def map_snap_column_type(self, snap_type: str) -> str:
        """Mapea tipos específicos del formato SNAP a SQLite."""
        if not snap_type:
            return 'TEXT'
            
        snap_type = snap_type.upper()
        
        # Mapeo específico para el formato SNAP
        type_mapping = {
            'VARCHAR': 'TEXT',
            'INTEGER': 'INTEGER', 
            'BOOLEAN': 'INTEGER',  # SQLite usa INTEGER para booleanos
            'TEXT': 'TEXT',
            'REAL': 'REAL',
            'BLOB': 'BLOB',
            'DATETIME': 'TEXT',
            'DATE': 'TEXT',
            'TIMESTAMP': 'TEXT'
        }
        
        return type_mapping.get(snap_type, 'TEXT')
    
    def create_table_sql(self, table_name: str, structure: List[Dict[str, Any]]) -> str:
        """Genera el SQL CREATE TABLE para una tabla con formato SNAP."""
        column_definitions = []
        
        for col in structure:
            # Obtener nombre de columna (formato SNAP usa 'column_name')
            col_name = col.get('column_name', '')
            if not col_name:
                continue
                
            # Obtener tipo de datos (formato SNAP usa 'data_type')
            col_type = self.map_snap_column_type(col.get('data_type', 'TEXT'))
            
            # Construir definición de columna
            definition = f"`{col_name}` {col_type}"
            
            # Agregar constraints basados en el formato SNAP
            if col.get('primary_key', False):
                definition += " PRIMARY KEY"
            
            # NOT NULL (si no es PRIMARY KEY, que ya implica NOT NULL)
            if col.get('not_null', False) and not col.get('primary_key', False):
                definition += " NOT NULL"
            
            # DEFAULT value - manejo mejorado
            if 'default' in col and col['default'] is not None:
                default_val = col['default']
                default_clause = self.process_default_value(default_val)
                if default_clause:
                    definition += f" DEFAULT {default_clause}"
            
            column_definitions.append(definition)
        
        if not column_definitions:
            raise ValueError(f"No se encontraron columnas válidas para la tabla {table_name}")
        
        columns_sql = ",\n    ".join(column_definitions)
        return f"CREATE TABLE `{table_name}` (\n    {columns_sql}\n);"
    
    def process_default_value(self, default_val: Any) -> str:
        """Procesa valores por defecto y los convierte a SQL válido."""
        if default_val is None:
            return "NULL"
        
        # Convertir a string para analizar
        default_str = str(default_val)
        
        # Detectar objetos SQLAlchemy serializados incorrectamente
        if "ScalarElementColumnDefault" in default_str:
            # Extraer el valor entre comillas simples
            import re
            match = re.search(r"ScalarElementColumnDefault\('([^']+)'\)", default_str)
            if match:
                extracted_value = match.group(1)
                return f"'{extracted_value}'"
            else:
                # Si no se puede extraer, usar NULL
                return "NULL"
        
        # Manejar otros objetos ORM serializados incorrectamente
        if any(obj_type in default_str for obj_type in ['ColumnDefault', 'DefaultClause', 'Scalar']):
            # Para otros tipos de objetos ORM, usar NULL como fallback seguro
            return "NULL"
        
        # Valores especiales de SQL
        if default_str.upper() in ['NULL', 'CURRENT_TIMESTAMP', 'CURRENT_DATE', 'CURRENT_TIME']:
            return default_str.upper()
        
        # Valores booleanos
        if isinstance(default_val, bool):
            return "1" if default_val else "0"
        
        # Valores numéricos
        if isinstance(default_val, (int, float)):
            return str(default_val)
        
        # Strings normales - escapar comillas simples
        if isinstance(default_val, str):
            # Escapar comillas simples duplicándolas
            escaped_val = default_str.replace("'", "''")
            return f"'{escaped_val}'"
        
        # Fallback para otros tipos
        return "NULL"
    
    def create_database(self):
        """Crea la base de datos SQLite con todas las tablas."""
        # Eliminar DB existente si existe
        if self.db_file.exists():
            self.db_file.unlink()
            print(f"✓ Base de datos existente eliminada: {self.db_file}")
        
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            tables = self.data['tables']
            
            print(f"\n🔧 Creando tablas...")
            
            # Crear cada tabla
            for table_name, table_info in tables.items():
                if 'structure' in table_info:
                    structure = table_info['structure']
                    
                    try:
                        create_sql = self.create_table_sql(table_name, structure)
                        
                        print(f"   Creando tabla: {table_name}")
                        cursor.execute(create_sql)
                        
                        row_count = table_info.get('row_count', 0)
                        actual_data_count = len(table_info.get('data', []))
                        print(f"   └─ {len(structure)} columnas, {actual_data_count} registros")
                        
                    except Exception as table_error:
                        print(f"\n❌ Error en tabla '{table_name}':")
                        print(f"   Mensaje: {table_error}")
                        print(f"   SQL generado:")
                        try:
                            failed_sql = self.create_table_sql(table_name, structure)
                            print(f"   {failed_sql}")
                        except:
                            print(f"   No se pudo generar el SQL")
                        
                        # Mostrar estructura de la tabla problemática
                        print(f"   Estructura de la tabla:")
                        for i, col in enumerate(structure):
                            print(f"   [{i}] {col}")
                        
                        raise table_error
            
            conn.commit()
            print("✓ Todas las tablas creadas exitosamente")
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Error creando tablas: {e}")
        
        finally:
            conn.close()
    
    def insert_data(self):
        """Inserta los datos en las tablas."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            tables = self.data['tables']
            
            print(f"\n📊 Insertando datos...")
            
            for table_name, table_info in tables.items():
                table_data = table_info.get('data', [])
                
                if not table_data:  # Tabla vacía
                    print(f"   Tabla {table_name}: sin datos")
                    continue
                
                # Procesar datos (formato SNAP: lista de objetos)
                if isinstance(table_data, list) and len(table_data) > 0:
                    first_record = table_data[0]
                    
                    if isinstance(first_record, dict):
                        columns = list(first_record.keys())
                        
                        # Preparar SQL de inserción
                        placeholders = ', '.join(['?' for _ in columns])
                        columns_sql = ', '.join([f'`{col}`' for col in columns])
                        insert_sql = f"INSERT INTO `{table_name}` ({columns_sql}) VALUES ({placeholders})"
                        
                        # Preparar datos para inserción
                        rows_to_insert = []
                        for record in table_data:
                            if isinstance(record, dict):
                                row = []
                                for col in columns:
                                    value = record.get(col)
                                    # Convertir valores especiales de SNAP
                                    if value is None or value == 'NULL' or value == '':
                                        value = None
                                    elif isinstance(value, str) and value.lower() == 'null':
                                        value = None
                                    # Convertir booleanos para SQLite
                                    elif isinstance(value, bool):
                                        value = 1 if value else 0
                                    row.append(value)
                                rows_to_insert.append(row)
                        
                        # Insertar en lotes para mejor rendimiento
                        if rows_to_insert:
                            cursor.executemany(insert_sql, rows_to_insert)
                            print(f"   Tabla {table_name}: {len(rows_to_insert)} registros insertados")
                        else:
                            print(f"   Tabla {table_name}: sin datos válidos para insertar")
                    
                    else:
                        print(f"   Tabla {table_name}: formato de datos no reconocido")
                
                else:
                    print(f"   Tabla {table_name}: formato de datos no estándar")
            
            conn.commit()
            print("✓ Todos los datos insertados exitosamente")
            
        except Exception as e:
            conn.rollback()
            raise Exception(f"Error insertando datos: {e}")
        
        finally:
            conn.close()
    
    def print_summary(self):
        """Imprime un resumen de la base de datos creada."""
        conn = sqlite3.connect(self.db_file)
        cursor = conn.cursor()
        
        try:
            print(f"\n📋 Resumen de la base de datos: {self.db_file}")
            print("-" * 50)
            
            # Obtener lista de tablas
            cursor.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = cursor.fetchall()
            
            total_records = 0
            
            for (table_name,) in tables:
                # Contar registros
                cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                count = cursor.fetchone()[0]
                total_records += count
                
                # Obtener info de columnas
                cursor.execute(f"PRAGMA table_info(`{table_name}`)")
                columns_info = cursor.fetchall()
                
                print(f"Tabla: {table_name}")
                print(f"  └─ Registros: {count}")
                print(f"  └─ Columnas: {len(columns_info)}")
                
                # Mostrar primeras columnas
                col_names = [col[1] for col in columns_info[:3]]
                if len(columns_info) > 3:
                    col_names.append(f"... (+{len(columns_info)-3} más)")
                print(f"     [{', '.join(col_names)}]")
                print()
            
            print(f"TOTAL: {len(tables)} tablas, {total_records} registros")
            
            # Información adicional del metadata si existe
            if 'metadata' in self.data:
                metadata = self.data['metadata']
                print("\nInformación del backup:")
                print(f"  Sistema: {metadata.get('backup_system', 'N/A')}")
                print(f"  Archivo origen: {metadata.get('database_file', 'N/A')}")
                print(f"  Exportado: {metadata.get('exported_at', 'N/A')}")
                print(f"  Motor ORM: {metadata.get('orm_engine', 'N/A')}")
        
        finally:
            conn.close()
    
    def generate(self):
        """Ejecuta todo el proceso de generación."""
        print("🚀 Iniciando generación de base de datos SQLite")
        print(f"Archivo JSON: {self.json_file}")
        print(f"Base de datos: {self.db_file}")
        
        # Cargar y validar JSON
        self.load_json()
        
        # Validar estructura del JSON
        self.validate_json_structure()
        
        # Crear estructura de tablas
        self.create_database()
        
        # Insertar datos
        self.insert_data()
        
        # Mostrar resumen
        self.print_summary()
        
        print(f"\n🎉 Base de datos creada exitosamente: {self.db_file}")
        print(f"📊 Tamaño del archivo: {self.db_file.stat().st_size / 1024:.1f} KB")
        
        # Mostrar comandos útiles
        print(f"\n💡 Comandos útiles:")
        print(f"   sqlite3 {self.db_file}")
        print(f"   .tables")
        print(f"   .schema nombre_tabla")
        print(f"   SELECT * FROM nombre_tabla LIMIT 5;")


def main():
    """Función principal del script."""
    # Si no se proporcionan argumentos, usar archivos por defecto
    if len(sys.argv) == 1:
        # Buscar data.json en el directorio actual
        current_dir = Path.cwd()
        json_file = current_dir / "data.json"
        db_file = current_dir / "database.db"
        
        if not json_file.exists():
            print("❌ No se encontró 'data.json' en el directorio actual")
            print("Uso: python main.py [archivo_json] [archivo_db]")
            print("O coloca el archivo 'data.json' en la misma carpeta que el script")
            sys.exit(1)
        
        print(f"📁 Usando archivos por defecto:")
        print(f"   JSON: {json_file}")
        print(f"   DB:   {db_file}")
        
    elif len(sys.argv) == 3:
        json_file = sys.argv[1]
        db_file = sys.argv[2]
        
    else:
        print("Uso del script:")
        print("  python main.py                    # Busca data.json en carpeta actual")
        print("  python main.py <json> <db>        # Especifica archivos manualmente")
        print()
        print("Ejemplos:")
        print("  python main.py")
        print("  python main.py backup.json database.db")
        sys.exit(1)
    
    try:
        generator = SQLiteGenerator(json_file, db_file)
        generator.generate()
        
    except Exception as e:
        print(f"❌ Error: {e}")
        print(f"\n🔧 Consejos para solucionar problemas:")
        print(f"   - Verifica que el archivo JSON existe y es válido")
        print(f"   - Revisa que el JSON tenga las secciones 'metadata' y 'tables'")
        print(f"   - Asegúrate de tener permisos de escritura en el directorio")
        sys.exit(1)


if __name__ == "__main__":
    main()