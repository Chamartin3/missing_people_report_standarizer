# Arquitectura

El motor son tres pasos listos para usar: **detectar → incrustar → buscar**. No
se entrena nada. La similitud es una sola consulta SQL sobre
[pgvector](https://github.com/pgvector/pgvector).

```
sube una foto
  → InsightFace detecta los rostros y devuelve un vector de 512 dim. por rostro
  → pgvector encuentra los rostros existentes más cercanos (coseno, índice HNSW)
  → agrupa por persona → "esto podría ser ya la Persona #42 (0.71)"
  → una persona confirma   ← el sistema sugiere, nunca fusiona automáticamente
```

La búsqueda por foto es el *mismo camino*, solo que de lectura.

Stack: **Python · InsightFace (`buffalo_l`) · PostgreSQL + pgvector · SQLModel ·
FastAPI · React (Vite)**. Solo CPU, costo cero por imagen.

## Mapa de módulos

Por capas, con **reglas de importación obligatorias** (`import-linter`, ver más
abajo). Cada capa solo conoce las de debajo.

```
api/        HTTP (FastAPI)              — solo importa services + auth + constants
services/   flujos: upload · identify · casefile · auth · ocr
domains/    lógica pura: recognition (el motor de IA) · curation · auth · ocr
data/       db (modelos SQLModel + managers) · storage (bytes de archivos)
constants/  configuración + enums + tipos; no importa nada del resto
```

| Paquete | Módulos | Responsabilidad |
|---|---|---|
| `api/` | `auth · dashboard · images · faces · persons · identify · users · deps` | Routers FastAPI. Validan entrada, llaman a un servicio, serializan la salida. Sin lógica de negocio ni acceso a la BD. `deps.py` resuelve el `User` actual desde el JWT. |
| `services/` | `upload · identify · casefile · auth · ocr · base` | Orquestan un flujo completo (varios managers + dominios). Cargan al `actor` (`BaseService`) para atribuir cada cambio. |
| `domains/` | `recognition/{engine,dedup} · curation/rules · ocr/engine · auth/{security,tokens}` | Lógica pura, sin BD. `recognition.engine` envuelve InsightFace; `dedup` agrupa vecinos por persona; `curation.rules` valida transiciones de confirmación; `auth` hace hashing + JWT. |
| `data/db/` | `_base · user · image · face · person · report · comment` | Un `Manager` por tabla. Devuelve **siempre** modelos pydantic (`*Data`), nunca filas ORM. La sesión (`scope`/`atomic`) es privada del paquete. |
| `data/storage/` | `files` | Bytes de archivos vía `fsspec` (disco hoy, `s3://` cambiando una variable). Direccionamiento por contenido (`sha256`). |
| `constants/` | `settings · enums · types` | Config (pydantic-settings, por prefijos de entorno), enums y *contratos de datos*. Hoja del grafo: no importa nada de `facefinder`. |

### Responsabilidad módulo por módulo

La regla en una frase: **cada módulo conoce solo las capas de debajo y devuelve
tipos de `constants`, nunca tipos de la capa que tiene debajo.** La frontera se
nota en los tipos de retorno: un `service` devuelve `*Data`/`TypedDict`, no filas
ORM; un `router` devuelve JSON, no objetos de servicio.

**`api/` — la cáscara HTTP.** Cada router valida la entrada, llama a **un**
servicio y serializa la salida. No tiene lógica de negocio ni toca la BD.
- `deps.py` — dependencia compartida: resuelve el `User` actual desde el `Bearer`
  JWT; es el único punto donde la autenticación entra en `api`.
- `auth` — login, `me`, cambio de contraseña. · `dashboard` — arma las
  estadísticas y la actividad reciente leyendo varios managers. · `images` —
  carga (2 pasos), procesar, servir bytes y texto OCR. · `faces` — listar,
  filtrar, recorte, asignar, buscar por foto. · `persons` — expediente completo
  (CRUD, informes, comentarios, archivar, fusionar). · `identify` — buscar por
  foto (solo lectura). · `users` — alta/gestión de curadores (solo admin).

**`services/` — los flujos.** Orquestan varios managers y dominios para completar
un caso de uso. Cargan al `actor` para atribuir cada cambio; no saben de HTTP.
- `base.BaseService` — lleva el `actor` y centraliza `require_actor()`, así ningún
  servicio re-pasa `user_id` por cada llamada.
- `upload.UploadService` — los dos pasos de la carga: `store` (bytes + dedup por
  `sha256`) y `process` (detectar/incrustar/recortar, idempotente).
- `identify.IdentifyService` — vecinos + dedup, asignar rostro a persona, crear y
  asignar. Aplica `check_transition` antes de tocar un nivel de confirmación.
- `casefile.CasefileService` — personas, informes, comentarios, archivar y
  fusionar; resuelve la cadena `merged_into`.
- `ocr.OcrService` — texto por imagen (cacheado). · `auth` — `AuthService` (login,
  hashing, emisión de JWT) y `seed_default_admin`.

**`domains/` — lógica pura, sin BD ni HTTP.** Reciben dicts/valores y devuelven
dicts/valores; cada uno se puede probar en aislamiento.
- `recognition/engine` — única envoltura de InsightFace (`buffalo_l`); singleton
  perezoso, filtra por `det_threshold`, devuelve `DetectedFace`. **Es el único
  módulo que importa el modelo de IA.**
- `recognition/dedup` — agrupa los vecinos por persona, convierte distancia a
  similitud y asigna `MatchBand`. Sin estado, sin BD (recibe un `Protocol`).
- `curation/rules` — la máquina de estados de `ConfirmationLevel`: qué transición
  es legal y que solo un humano sube de `suggested`.
- `ocr/engine` — envoltura de `tesseract`/`pytesseract`. · `auth/security` —
  hashing de contraseñas. · `auth/tokens` — codificar/decodificar JWT.

**`data/` — persistencia, aislada del resto.** Dos sub-paquetes:
- `data/db/_base` — `engine`, `init_db`, las sesiones privadas (`scope`/`atomic`),
  `enum_column` y el `Manager` genérico. Nada fuera de `data/db` abre una sesión.
- `data/db/{user,image,face,person,report,comment}` — un `Manager` por tabla:
  define el modelo SQLModel (la tabla) y las consultas de esa entidad (`nearest`,
  `page`, `for_person`, `assign`, …), devolviendo siempre su `*Data`.
- `data/storage/files` — bytes de archivos por `fsspec` (disco o `s3://`),
  direccionados por contenido; `sha256_bytes`, `put`, `open_bytes`, `crop`.

**`constants/` — la hoja del grafo.** No importa nada de `facefinder`, así que
cualquier capa puede depender de él sin crear ciclos.
- `settings` — toda la config, agrupada por dominio, leída de variables de entorno.
- `enums` — los `StrEnum` que comparten BD, dominios y API.
- `types` — los contratos de datos (`*Data` + los `TypedDict` del pipeline): el
  vocabulario común que cruza fronteras de capa.

### Reglas de importación (`import-linter`, en `pyproject.toml`)

`lint-imports` las verifica en CI; romperlas falla la build.

- **`data` está aislado** — `facefinder.data` no puede importar `api`, `services`
  ni `domains`. La capa de datos no sabe nada de quién la usa.
- **`api` es una cáscara** — `facefinder.api` no puede importar `domains` ni
  `data` directamente. Todo pasa por `services`.

`constants` no aparece en ninguna regla porque no importa nada: cualquiera puede
depender de él.

## Contratos de datos

Frontera dura entre la BD y todo lo demás: los managers nunca devuelven una fila
SQLModel, devuelven un modelo pydantic (`from_attributes=True`). Definidos en
`constants/types.py`.

### Entidades persistidas (una por tabla)

| Modelo | Campos clave | Notas |
|---|---|---|
| `UserData` | `id · email · password_hash · display_name · role · is_active · created_at` | `email` único. `role`: `curator \| admin`. |
| `ImageData` | `id · sha256 · path · format · source · uploaded_by · uploaded_at · processed_at · meta` | `sha256` **no** es único (recarga forzada). `processed_at=None` ⇒ aún sin detectar rostros. `meta` = EXIF. |
| `FaceData` | `id · image_id · crop_path · bbox · embedding(512) · det_score · person_id · confidence · confirmation · assigned_by · assigned_at` | `embedding` = `Vector(512)` (pgvector, índice HNSW coseno). `person_id=None` ⇒ rostro sin asignar. |
| `PersonData` | `id · display_name · first/last_name · expected/current_location · last_seen · cedula · is_minor · notas · status · attributes · created_at · deleted_at · merged_into` | `deleted_at` = borrado lógico (archivar). `merged_into` apunta al superviviente de una fusión. `attributes` = JSON libre. |
| `ReportData` | `id · person_id · image_id · kind · location · seen_at · reporter · notes · created_at` | `kind`: `note \| merge`. Una fusión se registra como un `Report` de tipo `merge`. |
| `CommentData` | `id · person_id · author · body · created_at` | Hilo de comentarios por persona. |

Todos los campos de auditoría (`uploaded_by · assigned_by · reporter · author`)
son FK a `user.id`.

### Contratos del pipeline de reconocimiento (dicts puros, sin BD)

Lo que viaja entre `domains/recognition` y los servicios:

| Tipo | Forma | Uso |
|---|---|---|
| `DetectedFace` | `{bbox, det_score, embedding}` | Salida de `detect_and_embed()`. |
| `CandidateEntry` | `{person_id, similarity, band}` | Una persona candidata para un rostro. |
| `IdentifyCandidate` | `{bbox, det_score, candidates[]}` | Por rostro detectado en una búsqueda. |
| `IdentifyImageResult` | `{faces_detected, matches[]}` | Respuesta de identificar una imagen entera. |

`CandidateMatch` (dataclass en `recognition/dedup.py`) es la versión enriquecida
interna: añade `distance`, `display_name` y la lista de `faces` agrupados.

### Enums (`constants/enums.py`)

Son `StrEnum`; el valor **en minúscula** es la única verdad y es lo que se guarda
en Postgres (ver `enum_column` en `data/db/_base.py`).

- `ConfirmationLevel`: `suggested → probable → confirmed`, más `disputed` /
  `rejected`. Las transiciones legales las impone `curation.rules.check_transition`
  (la máquina solo puede dejar `suggested`; subir de nivel exige un humano).
- `MatchBand`: `strong · possible · weak` — fuerza de un candidato, por umbral.
- `PersonStatus`: `missing · searching · found · reunited · deceased`.
- `ReportKind`: `note · merge`. · `UserRole`: `curator · admin`. ·
  `StorageKind`: `images · faces`.

## Flujos principales (services)

**Carga (dos pasos) — `UploadService`**
1. `store(data, force=False)` → guarda **solo los bytes**. Calcula `sha256`; si ya
   existe y no es forzado, devuelve `{status: "duplicate"}` (la SPA muestra la
   nueva y la existente lado a lado). `processed_at` queda en `NULL`.
2. `process(image_id)` → detecta + incrusta, guarda recortes, marca
   `processed_at`, y devuelve candidatos por rostro. **Idempotente**: re-procesar
   una imagen ya procesada devuelve sus rostros existentes.

**Identificar — `IdentifyService`**
- `identify(embedding)` = `deduplicate(Faces.nearest(...))`: k-vecinos en pgvector,
  agrupados por persona, ordenados por similitud.
- `assign(face_id, person_id, level, …)` valida la transición y atribuye el cambio
  al `actor`. `create_person_and_assign(...)` crea la persona y asigna en un paso.

**Expediente — `CasefileService`**
- CRUD de personas, informes y comentarios. `archive` = borrado lógico
  (`deleted_at`). `merge(survivor, loser)` mueve rostros/informes/comentarios al
  superviviente, marca `merged_into`, y registra un `Report` de tipo `merge`.
  `get()` sigue la cadena `merged_into` hasta el superviviente.

> `merge` son varias sentencias, no una transacción (cada manager tiene su propia
> sesión); es idempotente al re-ejecutar. Marcado con `ponytail:` en el código.

**OCR — `OcrService`** extrae texto de cada imagen (`tesseract` vía `pytesseract`)
para alimentar la captura de identidad en la pantalla de Revisión.

## Superficie HTTP

Todas las rutas (salvo `/auth/login` y `/health`) exigen un JWT (`Bearer`).

| Prefijo | Rutas | Servicio |
|---|---|---|
| `/auth` | `POST /login · GET /me · PATCH /me · POST /password` | `AuthService` |
| `/dashboard` | `GET ""` (estadísticas + actividad reciente) | varios managers |
| `/images` | `GET "" · POST "" · POST /{id}/process · GET /{id}/file · GET /{id}/text` | `UploadService`, `OcrService` |
| `/faces` | `GET "" · GET /{id} · GET /{id}/crop · POST /{id}/assign · POST /search` | `IdentifyService` |
| `/persons` | `GET "" · POST "" · GET /{id} · PATCH /{id} · POST /{id}/reports · /comments · /archive · POST /merge · POST /create-and-assign` | `CasefileService`, `IdentifyService` |
| `/identify` | `POST ""` (buscar por foto, solo lectura) | `IdentifyService` |
| `/users` | `GET "" · POST "" · PATCH /{id}` | `AuthService` (solo admin) |

## Configuración

`constants/settings.py` — pydantic-settings agrupado por dominio; cada grupo lee
sus variables por prefijo (todo desde `.env` o el entorno).

| Grupo | Prefijo | Lo importante |
|---|---|---|
| `database` | `DATABASE_` | `host · port · user · password · name` → `url`. |
| `auth` | `AUTH_` | `jwt_secret` (≥32 chars en producción), `jwt_expiry_minutes`. |
| `scores` | `SCORES_` | `det_threshold` (descarta detecciones flojas), `match_strong` / `match_possible` (cortes de banda). |
| `storage` | `IMAGES` / `FACES` | Ruta local o URL fsspec (`s3://bucket/crops`). Credenciales cloud por la cadena de fsspec (`AWS_*`). |
| `seed` | `SEED_ADMIN_` | Admin por defecto en una instalación vacía. Contraseña vacía ⇒ no se siembra. |

## Persistencia y arranque

`init_db()` (en `data/db/_base.py`, llamado en el `lifespan` de FastAPI) crea las
tablas, la extensión `vector`, el índice HNSW y aplica unos parches idempotentes
de esquema (columnas nuevas, índice de `sha256`, backfill de `processed_at`). **No
hay migraciones que aplicar a mano.**
</content>
