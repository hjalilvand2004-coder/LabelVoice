# -*- coding: utf-8 -*-
"""زیرسیستم استخراج فیلدهای ساختاریافته."""
from .classify import classify_product_type
from .fields import extract_fields, FIELD_LABELS_FA

__all__ = ["classify_product_type", "extract_fields", "FIELD_LABELS_FA"]
