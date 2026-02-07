# Manoli Bot Database

Sistema automatizado que descarga backups de una base de datos desde Gmail, genera una SQLite y la expone via API REST y bot de Discord.

## Arquitectura

```
Gmail (IMAP) --> JSON .gz --> SQLite --> FastAPI API --> Discord Bot
                                  ^
                                  |
                            APScheduler (cada 60 min)
```

**3 componentes corriendo en paralelo:**
- **FastAPI**: API REST en puerto 8000
- **Discord Bot**: comandos para consultar datos
- **Scheduler**: revisa Gmail cada hora buscando nuevos backups

## Requisitos

- Docker y Docker Compose
- Cuenta Gmail con App Password habilitado
- Bot de Discord con Message Content Intent activado

## Instalacion (VPS o local)

```bash
# 1. Clonar
git clone https://github.com/Fermin011/discord-bot-databse-manoli.git
cd discord-bot-databse-manoli

# 2. Configurar
cp .env.example .env
nano .env  # completar con tus datos

# 3. Arrancar
docker compose up -d --build

# 4. Ver logs
docker compose logs -f
```

## Configuracion del .env

| Variable | Descripcion |
|---|---|
| `GMAIL_EMAIL` | Email de Gmail |
| `GMAIL_APP_PASSWORD` | App Password de Gmail (no la password normal) |
| `GMAIL_SEARCH_SUBJECT` | Subject del email con el backup |
| `GMAIL_CHECK_INTERVAL_MINUTES` | Cada cuantos minutos revisar Gmail |
| `DISCORD_TOKEN` | Token del bot de Discord |
| `DISCORD_PREFIX` | Prefijo de comandos (default: `!`) |
| `SQL_MAX_ROWS` | Limite de filas en consultas SQL |

### Gmail App Password

1. Ir a https://myaccount.google.com/apppasswords
2. Generar una password para "Correo"
3. Copiar las 16 letras al .env

### Discord Bot

1. Crear app en https://discord.com/developers/applications/
2. Bot > activar **Message Content Intent**
3. Copiar el token al .env
4. Invitar al server con permisos de lectura/escritura de mensajes

## Comandos del Bot

### Ganancias (bruta / simple / neta)
| Comando | Descripcion |
|---|---|
| `!ganancia hoy` | Ganancia del dia |
| `!ganancia mes 1 2026` | Ganancia del mes |
| `!ganancia rango 2026-01-01 2026-01-31` | Rango de fechas |
| `!ganancia promedio` | Promedio general |

> **Bruta** = total ventas | **Simple** = bruta - costo stock | **Neta** = simple - costos operativos diarios

### Ventas
| Comando | Descripcion |
|---|---|
| `!ventas hoy` | Ventas del dia |
| `!ventas dia 2026-02-06` | Ventas de un dia |
| `!ventas mes 1 2026` | Ventas del mes |
| `!ventas top 10` | Top productos vendidos |

### Productos
| Comando | Descripcion |
|---|---|
| `!producto buscar leche` | Buscar por nombre |
| `!producto info 42` | Info detallada por ID |
| `!producto stock 5` | Productos con bajo stock |

### Finanzas
| Comando | Descripcion |
|---|---|
| `!finanzas costos` | Costos operativos |
| `!finanzas impuestos` | Impuestos |
| `!finanzas balance` | Balance financiero |
| `!finanzas resumen` | Resumen general |
| `!finanzas caja` | Cierres de caja |

### Sistema
| Comando | Descripcion |
|---|---|
| `!sql SELECT * FROM productos LIMIT 5` | SQL generico (solo SELECT) |
| `!tablas` | Lista tablas de la DB |
| `!estado` | Estado del sistema |
| `!comandos` | Lista de comandos |

## API REST

Documentacion interactiva en `http://tu-ip:8000/docs`

Endpoints principales:
- `GET /api/ganancias/hoy` - Ganancia del dia
- `GET /api/ventas/top-productos` - Top productos
- `GET /api/productos/?q=leche` - Buscar productos
- `GET /api/finanzas/balance` - Balance financiero
- `POST /api/sql/query` - SQL generico
- `GET /api/sistema/tablas` - Lista de tablas

## Sin datos iniciales

Si arrancas sin JSON/DB, el sistema:
1. Ejecuta el pipeline inmediatamente al iniciar
2. Conecta a Gmail y busca el backup mas reciente
3. Descarga, descomprime y genera la DB
4. Si no hay email, la API responde 503 hasta que llegue uno
5. El scheduler reintenta cada 60 minutos

## Estructura

```
├── run.py                    # Entry point (orquesta todo)
├── app/
│   ├── config.py             # Settings desde .env
│   ├── core/
│   │   ├── converter.py      # JSON SNAP -> SQLite
│   │   ├── database.py       # SQLAlchemy automap
│   │   └── scheduler.py      # APScheduler
│   ├── services/
│   │   ├── gmail.py          # IMAP download
│   │   └── data_pipeline.py  # Orquestacion completa
│   ├── api/
│   │   ├── main.py           # FastAPI app
│   │   └── routers/          # 6 routers
│   └── bot/
│       ├── client.py         # Discord bot
│       ├── formatters.py     # Embeds
│       └── cogs/             # 5 cogs de comandos
├── Dockerfile
├── docker-compose.yml
└── requirements.txt
```

## Operaciones Docker

```bash
# Reiniciar
docker compose restart

# Rebuild
docker compose up -d --build

# Parar
docker compose down

# Logs en tiempo real
docker compose logs -f
```
