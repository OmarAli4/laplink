from abc import ABC, abstractmethod
from decimal import Decimal


class DiscountStrategy(ABC):
    """Abstract Base Class for Discount Strategies."""
    @abstractmethod
    def calculate_discount(self, total: Decimal, discount_value: Decimal) -> Decimal:
        pass


class PercentageDiscountStrategy(DiscountStrategy):
    """Calculates discount as a percentage of the total."""
    def calculate_discount(self, total: Decimal, discount_value: Decimal) -> Decimal:
        return total * (discount_value / Decimal('100'))


class FixedDiscountStrategy(DiscountStrategy):
    """Subtracts a flat amount, capping at the total so the order doesn't become negative."""
    def calculate_discount(self, total: Decimal, discount_value: Decimal) -> Decimal:
        return min(total, discount_value)


def get_discount_strategy(discount_type: str) -> DiscountStrategy:
    """Factory to retrieve the correct strategy instance based on the string type."""
    if discount_type == 'fixed':
        return FixedDiscountStrategy()
    return PercentageDiscountStrategy()
