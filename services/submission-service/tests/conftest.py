import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./test_submission.db")
os.environ.setdefault("JWT_SECRET", "test-secret-test-secret-test-secret")
os.environ.setdefault("S3_ENDPOINT_URL", "http://localhost:9000")
