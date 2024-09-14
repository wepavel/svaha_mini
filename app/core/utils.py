import ulid


def generate_session_id() -> str:
    return ulid.new().str
