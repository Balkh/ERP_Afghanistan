from decimal import Decimal
from datetime import date
from enum import Enum
from typing import Optional
from dataclasses import dataclass, field


class StockSelectionMode(str, Enum):
    FEFO = 'FEFO'
    FIFO = 'FIFO'


@dataclass
class StockAllocation:
    batch_id: any
    batch_number: str
    product_id: any
    product_name: str
    quantity: Decimal
    expiry_date: date
    warehouse_id: any
    warehouse_name: str
    unit_cost: Decimal


@dataclass
class StockOperationResult:
    success: bool
    message: str
    movements: list = field(default_factory=list)
    allocations: list = field(default_factory=list)
    warnings: list = field(default_factory=list)
    errors: list = field(default_factory=list)
    stock_shortages: list = field(default_factory=list)
