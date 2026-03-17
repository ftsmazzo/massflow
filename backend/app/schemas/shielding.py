"""
Schemas para configuração global de blindagem (evitar e mitigar banimentos).
Estratégias modernas: delays aleatórios, lotes com pausas, limites, aquecimento,
rotação, detecção de risco, horário permitido, conteúdo.
"""
from pydantic import BaseModel, Field


# --- Sub-schemas por grupo ---


class ShieldingDelays(BaseModel):
    """Intervalo aleatório entre mensagens (nunca fixo)."""
    min_sec: int = Field(20, ge=5, le=300, description="Mínimo segundos entre mensagens")
    max_sec: int = Field(45, ge=5, le=300, description="Máximo segundos entre mensagens")


class ShieldingBatches(BaseModel):
    """Lotes com pausa entre lotes."""
    size_min: int = Field(15, ge=5, le=100, description="Mínimo mensagens por lote")
    size_max: int = Field(30, ge=5, le=100, description="Máximo mensagens por lote")
    pause_between_min_sec: int = Field(600, ge=60, le=3600, description="Pausa mínima entre lotes (seg)")
    pause_between_max_sec: int = Field(900, ge=60, le=3600, description="Pausa máxima entre lotes (seg)")


class ShieldingLongPause(BaseModel):
    """Pausa longa após X mensagens (simula comportamento humano)."""
    after_messages: int = Field(50, ge=20, le=200, description="Após quantas mensagens")
    duration_min_sec: int = Field(900, ge=300, le=7200, description="Duração mínima (seg)")
    duration_max_sec: int = Field(1800, ge=300, le=7200, description="Duração máxima (seg)")


class ShieldingLimits(BaseModel):
    """Limites por instância (hora/dia). Regra 5-10-30 e tetos por idade de conta."""
    max_per_hour: int = Field(30, ge=5, le=100, description="Máximo mensagens/hora por instância")
    max_per_day: int = Field(200, ge=20, le=500, description="Máximo mensagens/dia por instância")
    new_account_max_per_day: int = Field(50, ge=10, le=200, description="Conta nova: máx/dia (primeiros N dias)")
    new_account_days: int = Field(7, ge=1, le=30, description="Dias considerados 'conta nova'")


class ShieldingWarmup(BaseModel):
    """Aquecimento para instâncias novas."""
    enabled: bool = True
    days: int = Field(7, ge=1, le=30, description="Dias de aquecimento")
    max_per_day: int = Field(20, ge=5, le=50, description="Máx mensagens/dia durante aquecimento")


class ShieldingRotation(BaseModel):
    """Rotação automática de instâncias."""
    enabled: bool = True
    switch_after_messages: int = Field(100, ge=20, le=500, description="Trocar instância a cada N mensagens")


class ShieldingRisk(BaseModel):
    """Detecção de risco: 403/429, falhas consecutivas; pausar instância."""
    pause_on_403: bool = True
    pause_on_429: bool = True
    max_consecutive_errors: int = Field(3, ge=1, le=10, description="Pausar após N erros consecutivos")
    pause_duration_sec: int = Field(3600, ge=300, le=86400, description="Tempo de pausa da instância (seg)")


class ShieldingContent(BaseModel):
    """Alertas de conteúdo e opt-out."""
    max_repetition_alert_pct: int = Field(70, ge=50, le=100, description="Alerta se > X% das mensagens iguais")
    require_personalization: bool = Field(True, description="Recomendar variáveis (ex: {nome})")
    opt_out_keywords: list[str] = Field(
        default_factory=lambda: ["sair", "descadastrar", "stop", "parar", "remover", "cancelar"],
        description="Palavras que indicam pedido de descadastro",
    )


class ShieldingSchedule(BaseModel):
    """Janela de horário permitido para envio."""
    start_hour: int = Field(9, ge=0, le=23, description="Início (0-23)")
    end_hour: int = Field(18, ge=0, le=23, description="Fim (0-23)")
    timezone: str = Field("America/Sao_Paulo", max_length=60)


# --- Config completo (espelha o JSONB) ---


class ShieldingConfigBody(BaseModel):
    """Corpo da configuração global de blindagem."""
    delays: ShieldingDelays = Field(default_factory=ShieldingDelays)
    batches: ShieldingBatches = Field(default_factory=ShieldingBatches)
    long_pause: ShieldingLongPause = Field(default_factory=ShieldingLongPause)
    limits: ShieldingLimits = Field(default_factory=ShieldingLimits)
    warmup: ShieldingWarmup = Field(default_factory=ShieldingWarmup)
    rotation: ShieldingRotation = Field(default_factory=ShieldingRotation)
    risk: ShieldingRisk = Field(default_factory=ShieldingRisk)
    content: ShieldingContent = Field(default_factory=ShieldingContent)
    schedule: ShieldingSchedule = Field(default_factory=ShieldingSchedule)


def default_config_dict() -> dict:
    """Retorna o config como dict para JSONB (valores padrão)."""
    return ShieldingConfigBody().model_dump()


def config_from_dict(data: dict) -> ShieldingConfigBody:
    """Valida e preenche defaults para dict vindo do banco."""
    if not data:
        return ShieldingConfigBody.model_validate(default_config_dict())
    return ShieldingConfigBody.model_validate(data)
