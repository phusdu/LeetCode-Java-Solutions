from dataclasses import dataclass
from datetime import datetime
from typing import Optional

from sqlalchemy import Column, Integer, DateTime, Text
from typing_extensions import final

from app.commons.database.model import TableDefinition, DBEntity
from app.commons.utils.dataclass_extensions import no_init_field


@final
@dataclass(frozen=True)
class MarqetaCardTable(TableDefinition):
    name: str = no_init_field("marqeta_card")
    token: Column = no_init_field(
        Column("token", Text, primary_key=True, nullable=False)
    )
    delight_number: Column = no_init_field(
        Column("delight_number", Integer, nullable=False)
    )
    terminated_at: Column = no_init_field(Column("terminated_at", DateTime(True)))
    last4: Column = no_init_field(Column("last4", Text, nullable=False))


class MarqetaCard(DBEntity):
    token: str
    delight_number: int
    terminated_at: Optional[datetime]
    last4: str