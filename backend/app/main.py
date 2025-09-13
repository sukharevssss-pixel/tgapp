# --- Pydantic-схемы ---
class InitPayload(BaseModel):
    telegram_id: int
    username: str | None = None

class CreatePollPayload(BaseModel):
    telegram_id: int
    question: str
    options: list[str]
    min_bet_amount: int

class PlaceBetPayload(BaseModel):
    telegram_id: int
    poll_id: int
    option_id: int
    amount: int

class ClosePollPayload(BaseModel):
    telegram_id: int
    poll_id: int
    winning_option_id: int

class OpenChestPayload(BaseModel):
    telegram_id: int
    chest_id: int
