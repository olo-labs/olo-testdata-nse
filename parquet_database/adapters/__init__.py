"""Input adapters shipped with the parquet database builder."""

from .nse_day_delivery import NseDayDeliveryAdapter
from .nse_minute_zip import NseMinuteZipAdapter

__all__ = ["NseDayDeliveryAdapter", "NseMinuteZipAdapter"]

