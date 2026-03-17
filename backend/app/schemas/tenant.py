from pydantic import BaseModel


class TenantResponse(BaseModel):
    id: int
    name: str
    slug: str
    plan_type: int
    credits_balance: int
    active: bool

    class Config:
        from_attributes = True
