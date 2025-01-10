from datetime import datetime

import ulid


def generate_id(datetime_flag: bool = False, current_time: datetime = datetime.now()) -> str:
    if datetime_flag:
        return current_time.strftime('%y_%m_%d_%H%M_') + ulid.from_timestamp(current_time.timestamp()).randomness().str
    return ulid.new().str
