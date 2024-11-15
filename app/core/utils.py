import ulid


def generate_id() -> str:
    return ulid.new().str
