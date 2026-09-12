import os

# Recorded providers are an explicit test-only seam. Normal application defaults stay live-only.
os.environ["OMNITRADE_ENV"] = "test"
os.environ["OMNITRADE_FIXTURE_MODE"] = "true"
os.environ["OMNITRADE_DATABASE_URL"] = "sqlite:///./test-omnitrade.db"
os.environ["OMNITRADE_REDIS_URL"] = "redis://localhost:6379/15"
