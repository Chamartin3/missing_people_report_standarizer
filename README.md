# Estandarizador

Ingiere fotos de personas que desaparecieron durante una crisis, convierte cada
rostro en un vector buscable y deja que una persona cure qué rostro pertenece a
qué persona — mostrando personas similares en cada carga para que nadie se
registre dos veces.

**Todo el motor son tres pasos listos para usar: detectar → incrustar → buscar.**
No se entrena nada. La similitud es una sola consulta SQL sobre [pgvector](https://github.com/pgvector/pgvector).

## Ejecutar en local

### Docker (recomendado — sin preparar nada en el equipo)

Levanta los tres servicios: `db` (pgvector), `app` (FastAPI) y `web` (la SPA
detrás de nginx, que además redirige `/api` → app).

```bash
docker compose up --build          # o bien: scripts/up.sh  (build + up en segundo plano)
```

`scripts/up.sh` construye e inicia todo (db + backend + frontend) en segundo
plano; añade `--logs` para seguir los registros de `app` y `web`.

Luego abre **http://localhost:8080**, haz clic en **Register** para crear la
primera cuenta de persona curadora e inicia sesión. Puertos: web `8080`,
Postgres `5433` (host) → `5432` (contenedor). Los bytes de las imágenes cargadas
y los recortes de rostros persisten en `./storage/`.

`init_db()` se ejecuta al arrancar (crea las tablas, la extensión pgvector y el
índice HNSW), así que no hay migraciones que aplicar a mano.

### Scripts (dentro del contenedor `app`)

```bash
docker compose run --rm app python scripts/upload_demo.py     # carga las imágenes de muestra
docker compose run --rm app python scripts/identify_demo.py   # busca por foto
docker compose run --rm app python scripts/curate_demo.py     # asigna rostros a personas
docker compose run --rm app python scripts/init_db.py         # crea el esquema a mano
```

`scripts/extract_samples.py` y `scripts/verify_03_06.py` ayudan a preparar datos y
a comprobar el flujo de extremo a extremo. Cualquier script o verificación corre
igual con `docker compose run --rm app <cmd>`.

### Modo desarrollo (recarga en caliente)

Ejecuta la API y el servidor de desarrollo de Vite en el equipo, apuntando a la
base de datos en Docker.

```bash
# 1. solo la base de datos
docker compose up -d db

# 2. backend — accede a la BD del contenedor por el puerto 5433 del host
uv sync
DATABASE_PORT=5433 AUTH_JWT_SECRET=dev-secret-change-me-min-32-chars \
  uv run uvicorn facefinder.main:app --reload --port 8000

# 3. frontend (otra terminal) — usa por defecto la API en http://localhost:8000
cd web && npm install && npm run dev
```

### Verificaciones

Las cinco puertas de control (ejecútalas dentro del contenedor, o en el equipo
tras `uv sync`):

```bash
ruff check . && ruff format --check . && pyright && lint-imports && pytest
```

O bien, todo de una vez (las cinco puertas + la build del frontend):

```bash
scripts/check.sh           # en el equipo, tras `uv sync`
scripts/check.sh docker    # las puertas de Python dentro del contenedor
```

## La aplicación

Un backend en FastAPI más una interfaz de página única (SPA) en React (Vite). Las
personas curadoras inician sesión y luego trabajan en cuatro pantallas:

- **Tablero (Dashboard)** — la página inicial. Un panorama de la colección
  (imágenes cargadas, procesadas vs. sin procesar, rostros aún sin persona,
  personas registradas), además del control de carga y la actividad reciente. La
  carga es de **dos pasos**: la imagen se almacena primero y *después* se procesa
  para detectar rostros — así una carga puede quedar "sin procesar" hasta que la
  revises. Si los mismos bytes ya se habían cargado, la interfaz muestra la imagen
  nueva y la existente **lado a lado** y te permite revisar la existente o
  almacenarla como nueva de todos modos.
- **Revisión (Review, modal)** — se abre tras una carga o desde cualquier fila de
  imagen. Muestra los rostros detectados y el texto extraído por OCR, y te permite
  asignar cada rostro a una persona (existente o recién creada) y registrar un
  informe. Un aviso advierte mientras algún rostro siga sin asignar — todo rostro
  debería pertenecer a una persona.
- **Rostros (Faces)** — cada rostro detectado, filtrable por nivel de
  confirmación; también puedes asignar o crear una persona desde aquí.
- **Personas (People)** — el listado; abre una persona para ver sus rostros,
  informes y comentarios.

Las asignaciones avanzan por niveles de confirmación (`suggested → probable →
confirmed`); la máquina solo puede *sugerir* — una persona realiza cada promoción,
y cada cambio se atribuye al `User` que tiene la sesión iniciada.

### Extracción e identificación de personas

Más allá de los rostros, el sistema extrae **texto** de cada imagen mediante OCR
(`tesseract`, vía `pytesseract`) — útil cuando la foto incluye un documento de
identidad o un cartel con datos. En la pantalla de **Revisión**, ese texto se
muestra junto a los rostros y alimenta la captura de la identidad.

Cada **Persona** guarda datos de identificación estructurados, no solo un nombre
para mostrar:

| campo | descripción |
|---|---|
| `first_name` / `last_name` | nombre y apellido |
| `cedula` | número de documento de identidad |
| `expected_location` | ubicación o lugar esperado |
| `notas` | texto libre (p. ej. el OCR del documento) |
| `attributes` | datos adicionales (p. ej. `minor`) |

El flujo de identificación combina dos señales independientes: **el rostro**
(vector + búsqueda por similitud) sugiere personas parecidas, y **el texto** (OCR)
sugiere personas por coincidencia de palabras contra los registros existentes. La
persona curadora confirma: asigna el rostro a una persona —existente o nueva— y
captura o corrige sus datos de identidad. Nada se rellena de forma automática sin
confirmación humana.

## Decisiones (definidas)

- **Eliminar una Persona → borrado lógico (archivar).** `deleted_at`; el historial
  nunca se pierde.
- **Fusionar → operación auditada** con deshacer (registro `PersonMerge`).
  División aplazada.
- **Cuentas de usuario reales + inicio de sesión** (JWT); todos los campos de
  auditoría apuntan (FK) a `User`.
- **Escala: miles de imágenes** → CPU, ingesta síncrona, sin cola, sin GPU.

## Arquitectura

Por capas, con reglas de importación obligatorias (`import-linter`):
`api → services → domains → data → constants`. El mapa de módulos, la separación
de responsabilidades de cada módulo, los contratos de datos y la superficie HTTP
están en **[docs/ARCH.md](docs/ARCH.md)**.
</content>
