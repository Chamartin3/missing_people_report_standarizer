BEGIN;

-- =============================================================================
-- 0. LIMPIEZA DE INTENTOS FALLIDOS ANTERIORES
-- =============================================================================
DROP TABLE IF EXISTS person_merge_log CASCADE;
DROP TABLE IF EXISTS face_match CASCADE;
DROP TABLE IF EXISTS person_timeline CASCADE;
DROP TABLE IF EXISTS persona_contacto CASCADE;
DROP TABLE IF EXISTS report CASCADE;
DROP TABLE IF EXISTS person CASCADE;
DROP TABLE IF EXISTS paradero CASCADE;

-- En caso de que se hayan creado los índices sueltos
DROP INDEX IF EXISTS idx_paradero_tipo;
DROP INDEX IF EXISTS idx_user_email;
DROP INDEX IF EXISTS idx_image_sha256;
DROP INDEX IF EXISTS idx_face_image;
DROP INDEX IF EXISTS idx_face_person;
DROP INDEX IF EXISTS idx_comment_person;

-- =============================================================================
-- 1. ADAPTACIÓN DEL ENUM DE ROLES (Evita el error de "hospital_staff")
-- =============================================================================
-- Como "userrole" ya existe, añadimos los nuevos valores si no están presentes
ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'curator';
ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'hospital_staff';
ALTER TYPE userrole ADD VALUE IF NOT EXISTS 'citizen';

-- Añadimos el índice si no existía
CREATE INDEX IF NOT EXISTS idx_user_email ON "user"(email);

-- =============================================================================
-- 2. CREACIÓN DE TABLAS MAESTRAS NUEVAS
-- =============================================================================

CREATE TABLE paradero (
    id SERIAL PRIMARY KEY,
    nombre VARCHAR(255) NOT NULL,
    tipo VARCHAR(50) NOT NULL,          
    direccion TEXT,
    capacidad_total INTEGER DEFAULT 0,
    capacidad_actual INTEGER DEFAULT 0,
    contacto_emergencia VARCHAR(100),
    estado_infraestructura VARCHAR(50) DEFAULT 'operacional', 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    
    CONSTRAINT chk_tipo_paradero CHECK (tipo IN ('hospital', 'refugio', 'morgue', 'asistencia_vial', 'centro_acopio')),
    CONSTRAINT chk_estado_infra CHECK (estado_infraestructura IN ('operacional', 'danado', 'colapsado'))
);
CREATE INDEX idx_paradero_tipo ON paradero(tipo);

CREATE TABLE person (
    id SERIAL PRIMARY KEY,
    cedula VARCHAR(50) UNIQUE, 
    first_name VARCHAR(150) NOT NULL,
    last_name VARCHAR(150) NOT NULL,
    display_name VARCHAR(300) GENERATED ALWAYS AS (first_name || ' ' || last_name) STORED, 
    is_minor BOOLEAN DEFAULT FALSE,
    status VARCHAR(50) DEFAULT 'desaparecido', 
    paradero_id INTEGER REFERENCES paradero(id) ON DELETE SET NULL, 
    merged_into INTEGER REFERENCES person(id) ON DELETE SET NULL,   
    notas TEXT,
    attributes JSONB DEFAULT '{}', 
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    deleted_at TIMESTAMP WITHOUT TIME ZONE,
    
    CONSTRAINT chk_status_person CHECK (status IN ('desaparecido', 'encontrado_vivo', 'fallecido', 'no_afectado'))
);
CREATE INDEX idx_person_paradero ON person(paradero_id);
CREATE INDEX idx_person_status ON person(status);
CREATE INDEX idx_person_cedula ON person(cedula) WHERE cedula IS NOT NULL;

-- =============================================================================
-- 3. ALTERACIONES POLIMÓRFICAS A TABLAS EXISTENTES (Con salvaguardas)
-- =============================================================================

-- Tabla Image
ALTER TABLE image ALTER COLUMN source SET DEFAULT 'web_report';
ALTER TABLE image ADD COLUMN IF NOT EXISTS uploaded_by INTEGER REFERENCES "user"(id) ON DELETE SET NULL;
ALTER TABLE image ADD COLUMN IF NOT EXISTS processed_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE image ADD COLUMN IF NOT EXISTS meta JSONB DEFAULT '{}';
CREATE INDEX IF NOT EXISTS idx_image_sha256 ON image(sha256);

-- Tabla Face
ALTER TABLE face ADD COLUMN IF NOT EXISTS person_id INTEGER REFERENCES person(id) ON DELETE SET NULL;
ALTER TABLE face ADD COLUMN IF NOT EXISTS box_2d JSONB NOT NULL DEFAULT '{}';
ALTER TABLE face ADD COLUMN IF NOT EXISTS embedding VECTOR(512); 
CREATE INDEX IF NOT EXISTS idx_face_image ON face(image_id);
CREATE INDEX IF NOT EXISTS idx_face_person ON face(person_id) WHERE person_id IS NOT NULL;

-- Tabla Comment
ALTER TABLE comment ADD COLUMN IF NOT EXISTS person_id INTEGER NOT NULL REFERENCES person(id) ON DELETE CASCADE;
ALTER TABLE comment ADD COLUMN IF NOT EXISTS user_id INTEGER REFERENCES "user"(id) ON DELETE SET NULL;
ALTER TABLE comment ADD COLUMN IF NOT EXISTS is_private BOOLEAN DEFAULT FALSE;
ALTER TABLE comment ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT TIMEZONE('utc', NOW());
CREATE INDEX IF NOT EXISTS idx_comment_person ON comment(person_id);

-- =============================================================================
-- 4. CREACIÓN DEL RESTO DE TABLAS NUEVAS
-- =============================================================================

CREATE TABLE report (
    id SERIAL PRIMARY KEY,
    person_id INTEGER REFERENCES person(id) ON DELETE SET NULL,
    reported_by INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
    tipo_reporte VARCHAR(50) NOT NULL, 
    ultimo_paradero_conocido TEXT,     
    fecha_suceso TIMESTAMP WITHOUT TIME ZONE,
    descripcion TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    
    CONSTRAINT chk_tipo_reporte CHECK (tipo_reporte IN ('busqueda', 'avistamiento'))
);
CREATE INDEX idx_report_person ON report(person_id);

CREATE TABLE persona_contacto (
    id SERIAL PRIMARY KEY,
    person_id INTEGER REFERENCES person(id) ON DELETE CASCADE, 
    nombre_contacto VARCHAR(255) NOT NULL,                     
    parentesco VARCHAR(100),                                   
    telefono_principal VARCHAR(50) NOT NULL,
    telefono_secundario VARCHAR(50),
    email VARCHAR(255),
    direccion_actual TEXT,
    recibir_notificaciones BOOLEAN DEFAULT TRUE,               
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);
CREATE INDEX idx_contacto_person_id ON persona_contacto(person_id);

CREATE TABLE person_timeline (
    id SERIAL PRIMARY KEY,
    person_id INTEGER REFERENCES person(id) ON DELETE CASCADE,
    paradero_id INTEGER REFERENCES paradero(id) ON DELETE SET NULL, 
    tipo_evento VARCHAR(50) NOT NULL,                               
    descripcion TEXT NOT NULL,                                      
    registrado_por INTEGER REFERENCES "user"(id) ON DELETE SET NULL,                    
    fecha_evento TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    
    CONSTRAINT chk_tipo_evento CHECK (tipo_evento IN ('ingreso', 'traslado', 'avistamiento', 'alta', 'deceso'))
);
CREATE INDEX idx_timeline_person ON person_timeline(person_id);
CREATE INDEX idx_timeline_fecha ON person_timeline(fecha_evento DESC);

CREATE TABLE face_match (
    id SERIAL PRIMARY KEY,
    face_id_origen INTEGER REFERENCES face(id) ON DELETE CASCADE,   
    face_id_destino INTEGER REFERENCES face(id) ON DELETE CASCADE,  
    similitud FLOAT NOT NULL,                                       
    estado VARCHAR(50) DEFAULT 'pendiente',                         
    validado_por INTEGER REFERENCES "user"(id) ON DELETE SET NULL,                     
    notas_validacion TEXT,
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT TIMEZONE('utc', NOW()),
    
    CONSTRAINT chk_estado_match CHECK (estado IN ('pendiente', 'verificado', 'descartado'))
);
CREATE INDEX idx_facematch_estado ON face_match(estado);
CREATE INDEX idx_facematch_similitud ON face_match(similitud DESC);

CREATE TABLE person_merge_log (
    id SERIAL PRIMARY KEY,
    person_id_origen INTEGER REFERENCES person(id) ON DELETE CASCADE, 
    person_id_destino INTEGER REFERENCES person(id) ON DELETE CASCADE, 
    ejecutado_por INTEGER REFERENCES "user"(id) ON DELETE SET NULL,
    motivo TEXT NOT NULL,               
    created_at TIMESTAMP WITHOUT TIME ZONE DEFAULT TIMEZONE('utc', NOW())
);

COMMIT;