# 🗓️ Sistema de Gestión de Turnos

## Requisitos
- Docker
- Docker Compose

## Arrancar el proyecto

```bash
# 1. Clonar / descomprimir el proyecto
# 2. Levantar los contenedores
docker compose up --build

# La API estará disponible en:
# http://localhost:8081
# Documentación interactiva: http://localhost:8081/docs
```

## Credenciales iniciales

| Campo    | Valor      |
|----------|------------|
| Usuario  | `admin`    |
| Password | `admin1234`|

> ⚠️ Cambia la contraseña del admin y el `SECRET_KEY` en el `.env` antes de poner en producción.

## Endpoints disponibles

### Autenticación
| Método | Ruta                  | Descripción              | Auth |
|--------|-----------------------|--------------------------|------|
| POST   | /api/v1/auth/login    | Login, devuelve JWT      | No   |
| GET    | /api/v1/auth/me       | Usuario actual           | Sí   |

### Usuarios
| Método | Ruta                  | Descripción              | Auth     |
|--------|-----------------------|--------------------------|----------|
| GET    | /api/v1/users/        | Listar usuarios          | Usuario  |
| POST   | /api/v1/users/        | Crear usuario            | Superuser|
| GET    | /api/v1/users/{id}    | Ver usuario              | Usuario  |
| PATCH  | /api/v1/users/{id}    | Editar usuario           | Superuser|
| DELETE | /api/v1/users/{id}    | Eliminar usuario         | Superuser|

### Roles
| Método | Ruta                  | Descripción              | Auth     |
|--------|-----------------------|--------------------------|----------|
| GET    | /api/v1/roles/        | Listar roles             | Usuario  |
| POST   | /api/v1/roles/        | Crear rol                | Superuser|
| PATCH  | /api/v1/roles/{id}    | Editar rol               | Superuser|
| DELETE | /api/v1/roles/{id}    | Eliminar rol             | Superuser|

## Estructura del proyecto

```
proyecto/
├── docker-compose.yml
├── .env
└── backend/
    ├── Dockerfile
    ├── requirements.txt
    ├── alembic.ini
    ├── alembic/
    │   └── env.py
    └── app/
        ├── main.py
        ├── core/
        │   ├── config.py       # Variables de entorno
        │   ├── database.py     # Conexión PostgreSQL
        │   └── security.py     # JWT y hashing
        ├── models/
        │   ├── user.py         # Tabla usuarios
        │   └── role.py         # Tablas roles y permisos
        ├── schemas/
        │   ├── user.py         # Validación Pydantic
        │   └── role.py
        ├── routers/
        │   ├── auth.py         # /auth
        │   ├── users.py        # /users
        │   └── roles.py        # /roles
        └── services/
            ├── auth.py         # Lógica autenticación
            └── user.py         # CRUD usuarios
```

## Próximos pasos sugeridos

1. **Módulo de Empleados**: ficha del empleado con categoría, tipo de agente, licencias, etc.
2. **Módulo de Turnos**: definición de tipos de turno, horarios, coberturas necesarias
3. **Módulo de Asignaciones**: qué empleado cubre qué turno
4. **Reglas de negocio**: descansos obligatorios, horas máximas, incompatibilidades
5. **Notificaciones**: avisos de turno a los empleados

## Comandos útiles

```bash
# Ver logs
docker compose logs -f backend

# Entrar al contenedor
docker compose exec backend bash

# Generar migración (tras cambiar modelos)
docker compose exec backend alembic revision --autogenerate -m "descripcion"

# Aplicar migraciones
docker compose exec backend alembic upgrade head

# Parar todo
docker compose down

# Parar y borrar volúmenes (¡borra la BD!)
docker compose down -v
```
