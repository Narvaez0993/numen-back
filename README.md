# back-numen

Backend de **numen** (Gastos by IM v2). FastAPI + MongoDB + arquitectura **Hexagonal (Ports & Adapters)**.

## Stack

- **Python 3.12** + **FastAPI** async
- **MongoDB 7 + Beanie** (ODM async sobre motor); single-node replica set en dev para transactions
- **Redis 7 + ARQ** para jobs background (IA, detección de recurrentes, cuotas mensuales)
- **Anthropic Claude** (chat/visión) + **OpenAI Whisper** (voz) detrás de ports intercambiables
- **Cloudflare R2** (S3-compatible) para fotos de recibos
- **JWT** (PyJWT) con refresh tokens rotativos + **Argon2** para passwords
- **uv** package manager, **Ruff** lint/format, **mypy** strict, **import-linter** boundaries
- **structlog** + **Sentry** para observabilidad

## Cómo arrancar

```bash
# 1. Instalar deps (uv crea venv en .venv automáticamente)
uv sync

# 2. Copiar env
cp .env.example .env  # ajustá JWT_SECRET en local; dejá vacíos los keys de IA si no estás probando

# 3. Levantar todo en docker (recomendado — incluye Mongo replica set + Redis)
cd docker && docker compose up --build

# 4. Probar
curl http://localhost:8000/healthz
# {"status":"ok"}

# Docs OpenAPI
open http://localhost:8000/docs
```

### Sin Docker (solo si ya tenés Mongo + Redis locales)

```bash
# Necesitás Mongo corriendo como replica set:
#   mongod --replSet rs0 --dbpath ~/mongodata
#   mongosh --eval 'rs.initiate({_id:"rs0",members:[{_id:0,host:"127.0.0.1:27017"}]})'
# Y Redis:
#   brew services start redis

uv run uvicorn src.core.app:app --reload --port 8000
uv run arq src.core.workers.WorkerSettings  # worker en otra terminal
```

## Comandos

```bash
uv run ruff check .          # lint
uv run ruff format .         # format
uv run mypy src/             # type check strict
uv run lint-imports          # contratos hexagonales (boundaries)
uv run pytest tests/         # tests
uv run pytest tests/ -v --cov=src   # con cobertura
```

## Arquitectura

```
src/
├── modules/<bounded-context>/
│   ├── domain/              # ENTIDADES PURAS — cero deps externas
│   │   ├── entities/        # @dataclass: User, Expense, ...
│   │   ├── value_objects/   # Email, Money, HashedPassword
│   │   └── errors.py        # DomainError subclasses con http_status
│   ├── application/         # LA API DEL MÓDULO
│   │   ├── use_cases/       # = inbound ports (LoginUseCase, RegisterUseCase, ...)
│   │   ├── ports/           # outbound port Protocols (Repository, Hasher, ...)
│   │   └── dto/             # Pydantic DTOs in/out
│   └── adapters/
│       ├── inbound/         # los que MANEJAN la app
│       │   ├── http/        # FastAPI routers + Pydantic schemas
│       │   └── workers/     # ARQ jobs específicos del módulo
│       └── outbound/        # implementaciones de los ports
│           ├── persistence/ # Beanie Documents + Mongo repos + mappers
│           └── crypto/      # Argon2, JWT, etc.
│
├── shared/                  # cross-cutting (mismo patrón)
│   ├── domain/              # DomainError base, tipos comunes
│   ├── application/ports/   # Clock, EventPublisher, IDGenerator (futuro)
│   └── adapters/
│       ├── inbound/http/    # exception handlers, dependencies (get_current_user_id)
│       └── outbound/        # mongo client, settings, logging, R2, AI clients
│
└── core/                    # bootstrap
    ├── di/container.py      # composition root: cablea ports → adapters + use cases
    ├── app.py               # create_app() FastAPI factory (lifespan + middlewares + routers)
    └── workers.py           # ARQ worker entry point
```

### Reglas de capas (forzadas por `import-linter`)

Definidas en `.importlinter`. Si una nueva línea viola un contrato, **no agregues una excepción** — replantea la separación.

| Desde \ Hacia | domain | app/use_cases | app/ports | adapters/inbound | adapters/outbound | core |
|---|:--:|:--:|:--:|:--:|:--:|:--:|
| `domain/` | ✅ | ❌ | ❌ | ❌ | ❌ | ❌ |
| `app/use_cases` | ✅ | ✅ | ✅ | ❌ | ❌ | ❌ |
| `app/ports` | ✅ | ❌ | ✅ | ❌ | ❌ | ❌ |
| `adapters/inbound` | ✅ | ✅ | ✅ | ✅ | ❌ (directo) | ✅ (DI) |
| `adapters/outbound` | ✅ | ❌ | ✅ (impl) | ❌ | ✅ | ❌ |
| `core` | ✅ | ✅ | ✅ | ❌ | ✅ | — |

> `core/di/container.py` es la **composition root**: importa adapters/outbound (para instanciarlos) y los expone a inbound vía FastAPI Depends. Es la única ruta legítima entre inbound y outbound. El contrato `auth — adapters/inbound cannot import adapters/outbound (direct)` usa `allow_indirect_imports = True` para permitir solo este puente.

### Verificar la regla en acción

Crear un archivo `src/modules/auth/adapters/inbound/http/_test.py` con `from src.modules.auth.adapters.outbound.persistence.repositories.mongo_auth_repository import MongoAuthRepository` y correr `uv run lint-imports` — debe romperse el contrato.

## Cómo crear un módulo nuevo

Plantilla canónica: `src/modules/auth/`. Para crear `expenses` (por ejemplo):

1. **Estructura**: replicar el árbol `domain/{entities,value_objects}, application/{use_cases,ports,dto}, adapters/{inbound/http, outbound/persistence/{documents,repositories,mappers}}`.
2. **Domain primero**: entity con `@dataclass(frozen=True)`, value objects con `create()` que valida invariantes, errors heredando de `DomainError`.
3. **Application**: ports como `typing.Protocol`. Use cases como `@dataclass` con los ports inyectados; método `async def execute(input_dto) -> output_dto`.
4. **Outbound adapters**: `<Mongo|R2|Claude|...><Concept>` implementa el Protocol. Beanie Documents en `adapters/outbound/persistence/documents/`. Mappers separan entidad ↔ Document.
5. **Inbound adapters**: `routers.py` con FastAPI, `schemas.py` con Pydantic. Las rutas piden los use cases vía `Depends(...)` que tira del `core/di/container.py`.
6. **Registrar en core**: agregar el use case + ports a `Container` en `src/core/di/container.py`. Agregar el `Document` a `_DOCUMENTS` en `core/app.py` y `core/workers.py`. Incluir el `router` en `core/app.py`.
7. **import-linter**: replicar los 4 contratos del módulo `auth` en `.importlinter` para el módulo nuevo.
8. **Tests**: unit con fakes de los ports en `tests/unit/<module>/`; integration con `testcontainers-mongodb` en `tests/integration/<module>/` (futuro).

## Decisiones transversales

- **Separación pura Document ↔ entidad**: nada de SQLModel. Domain usa `@dataclass`. Beanie Documents viven en `adapters/outbound/persistence/documents/`. Mappers convierten.
- **Transacciones**: helper `with_transaction` en `src/shared/adapters/outbound/persistence/mongo.py`. Requiere replica set (configurado automáticamente en docker-compose).
- **Integridad referencial**: la valida la capa application. Antes de crear un gasto, los use cases validan que `account_id`/`category_id` existan y pertenezcan al user.
- **Multi-tenant**: cada query filtra por `user_id` extraído del JWT (`get_current_user_id` en `shared/adapters/inbound/http/dependencies.py`).
- **Errores → HTTP**: `DomainError` subclases definen `http_status` + `code`. El handler global en `shared/adapters/inbound/http/exception_handlers.py` los mapea a JSON consistente `{ code, message }`.

## Lo que NO está incluido todavía

- Otros módulos (`accounts`, `expenses`, `subscriptions`, `budgets`, `assistant`, `billing`) — cada uno tendrá su mini-plan.
- Social sign-in (Apple / Google) y reset de contraseña.
- Implementación real de transcripción/visión IA (puertos quedarán definidos en sus módulos, falta el adapter).
- Cuotas IA Free/Plus.
- Push notifications.
- CI/CD.
- Pre-commit hooks (las herramientas están instaladas; falta el `.pre-commit-config.yaml`).
- Integración Stripe/Mercado Pago.
- Provider de hosting (Railway/Fly.io/etc).

## Smoke test end-to-end (con docker compose arriba)

Email delivery is suspended: the verification code is logged by the API. Read it with
`docker compose logs api | grep verification_code_issued` (JSON field `code`).

```bash
# 1. Register — creates an unverified user, no tokens (201)
curl -X POST http://localhost:8000/auth/register \
  -H 'Content-Type: application/json' \
  -d '{"email":"sebastian@numen.app","password":"demo1234","display_name":"Sebastián"}'

# 2. Login before verifying → 403 auth.email_not_verified
curl -X POST http://localhost:8000/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"sebastian@numen.app","password":"demo1234"}'

# 3. Grab the code from the API log, then verify → 200 with access_token + refresh_token
curl -X POST http://localhost:8000/auth/verify-email \
  -H 'Content-Type: application/json' \
  -d '{"email":"sebastian@numen.app","code":"<code-from-log>"}'

# 4. Login now succeeds; /me shows email_verified: true
curl http://localhost:8000/auth/me -H "Authorization: Bearer <access_token>"

# 5. Rotate the session; reusing the old refresh token revokes the whole family (401)
curl -X POST http://localhost:8000/auth/refresh \
  -H 'Content-Type: application/json' \
  -d '{"refresh_token":"<refresh_token>"}'

# 6. Logout revokes the family
curl -X POST http://localhost:8000/auth/logout \
  -H 'Content-Type: application/json' \
  -d '{"refresh_token":"<refresh_token>"}'
```
