from __future__ import annotations

from datetime import date

import pytest

from scripts.audit_dependencies import active_exception_ids


def test_security_exception_is_active_and_expires() -> None:
    assert active_exception_ids(today=date(2026, 7, 11)) == ["PYSEC-2026-311"]
    with pytest.raises(RuntimeError, match="expired"):
        active_exception_ids(today=date(2026, 8, 16))
