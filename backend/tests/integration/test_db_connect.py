import os

import pytest
from sqlalchemy import create_engine, text

pytestmark = pytest.mark.integration

TEST_URL = os.environ.get(
    "TEST_DATABASE_URL", "postgresql+psycopg://sonar:sonar@localhost:55432/sonar_test"
)


def test_connects_and_has_uuid_function():
    engine = create_engine(TEST_URL)
    with engine.connect() as conn:
        assert conn.execute(text("SELECT 1")).scalar() == 1
        assert conn.execute(text("SELECT gen_random_uuid()")).scalar() is not None
    engine.dispose()
