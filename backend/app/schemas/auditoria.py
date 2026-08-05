from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditoriaLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    auditoria_id: int
    entidad: str
    entidad_id: int
    accion: str
    usuario_id: int
    usuario_nombre: str
    detalle_json: dict | None
    creado_en: datetime

    @classmethod
    def from_model(cls, obj) -> "AuditoriaLogOut":
        # Fallback "Usuario #{id}" cuando la relación no resuelve — la
        # suite de tests emite JWTs con usuario_id sin sembrar una fila
        # Usuario real (ver models/auditoria.py), así que esto no es
        # defensividad de más, es necesario para no romper esos tests.
        usuario_nombre = f"Usuario #{obj.usuario_id}"
        if obj.usuario is not None:
            usuario_nombre = f"{obj.usuario.nombres} {obj.usuario.apellidos}"
        return cls(
            auditoria_id=obj.auditoria_id,
            entidad=obj.entidad,
            entidad_id=obj.entidad_id,
            accion=obj.accion,
            usuario_id=obj.usuario_id,
            usuario_nombre=usuario_nombre,
            detalle_json=obj.detalle_json,
            creado_en=obj.creado_en,
        )
