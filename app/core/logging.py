# import inspect
#
# class ContextFilter(logging.Filter):
#     def filter(self, record):
#         frame = inspect.currentframe()
#         while frame:
#             co = frame.f_code
#             filename = co.co_filename
#             func_name = co.co_name
#             if 'logging' not in filename: # Исключаем логирующий модуль
#                 break
#             frame = frame.f_back
#         record.filename = filename
#         record.funcName = func_name
#         return
#
# class StreamToLogger:
#     """
#     Fake file-like stream object that redirects writes to a logger instance.
#     """
#
#     def __init__(self, logger, log_level) -> None:
#         super().__init__(log_level)
#         self.logger = logger
#         self.log_level = log_level
#         self.linebuf = ''
#
#     def write(self, buf) -> None:
#         for line in buf.rstrip().splitlines():
#             self.logger.log(self.log_level, line.rstrip())
#
#     def flush(self) -> None:
#         pass
#
#     def isatty(self) -> bool:
#         return False
# #
# # logging.basicConfig(
# #     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(filename)s:%(funcName)s]',
# # )
#
# logger = logging.getLogger("app_logger")
# logger.setLevel(logging.DEBUG)
# #
# # context_filter = ContextFilter()
# # logger.addFilter(context_filter)
#
#
# if __name__ == "__main__":
#     logger.debug("This is a debug message")
#     logger.info("This is an info message")
#     logger.warning("This is a warning message")
#     logger.error("This is an error message")
#     try:
#         1 / 0
#     except ZeroDivisionError:
#         logger.exception("An exception occurred")


from collections.abc import Mapping
from datetime import datetime, timezone
from enum import Enum
import logging
import traceback
from typing import Any

import orjson
import structlog
from structlog.contextvars import bind_contextvars

# from app.api.middleware.request_id import event_id
from app.core.config import settings

# load_dotenv(override=False)


class UvicornCommonLogFormatter(logging.Formatter):
    def __init__(self) -> None:
        super().__init__()
        self.level = settings.LOG_LEVEL

    @classmethod
    def _serialize(cls, message: Mapping) -> bytes:  # type: ignore[type-arg]
        def default(o: Any) -> str | float:  # noqa: ANN401
            if isinstance(o, Enum):
                raise NotImplementedError
            if isinstance(o, datetime):
                return o.isoformat()
            return '<not serializable>'

        return orjson.dumps(message, default=default, option=orjson.OPT_NON_STR_KEYS)

    def format(self, record: logging.LogRecord) -> str:
        message: dict[str, str | list[Any]] = {
            # 'request_id': event_id.get(),
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'level': record.levelname.lower(),
        }

        if isinstance(record.msg, dict):
            message.update(record.msg)

        elif isinstance(record.msg, str):
            if 'message' in record.__dict__ and record.message:
                message.update(dict(message=record.message))
            elif not record.args:
                message.update(dict(message=record.msg))
            else:
                message.update(dict(message=record.msg % record.args))

        if record.exc_info:
            message.update(dict(trace=str(traceback.format_exc())))

        serialized_message = self._serialize(message).decode()
        return serialized_message


class UvicornAccessLogFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        host, method, path, _http_version, status = record.args  # type: ignore[misc]

        # Extract IP address from host
        # ip = host.split(':')[0]
        #
        # # Convert IP address to numeric format
        # try:
        #     ip_obj = ipaddress.ip_address(ip)
        #     ip_as_int = int(ip_obj)
        # except ValueError:
        #     ip_as_int = ip

        message = {
            # 'request_id': event_id.get(),
            'service': 'backend',
            'timestamp': datetime.fromtimestamp(record.created, tz=timezone.utc).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
            'level': 'access',
            'host': host.split(':')[0],
            'method': method,
            'path': path,
            'status': status,
            'message': 'request handled',
        }
        return self._serialize(message).decode()

    @classmethod
    def _serialize(cls, message: Mapping) -> bytes:  # type: ignore[type-arg]
        def default(o: Any) -> str:  # noqa: ANN401
            if isinstance(o, datetime):
                return o.isoformat()
            return '<not serializable>'

        return orjson.dumps(message, default=default)


def __order_keys(dic: dict[str, Any], **kw) -> str:  # type: ignore[no-untyped-def] # noqa: ANN003
    order = ['request_id', 'timestamp', 'level']
    ordered_log_message = {}

    for key in order:
        if key in dic:
            ordered_log_message[key] = dic[key]

    for k in dic:
        if k not in order:
            ordered_log_message[k] = dic[k]
    return orjson.dumps(ordered_log_message, **kw).decode('utf-8')


processors = [
    structlog.processors.EventRenamer('message'),
    structlog.contextvars.merge_contextvars,
    # structlog.processors.StackInfoRenderer(),
    # structlog.dev.set_exc_info,
    structlog.processors.ExceptionRenderer(),  # structlog.processors.dict_tracebacks
    structlog.processors.add_log_level,
    structlog.processors.TimeStamper(fmt='iso'),
    structlog.processors.JSONRenderer(serializer=__order_keys),
    # structlog.processors.LogfmtRenderer(),
]

structlog.configure(
    processors=processors,  # type: ignore[arg-type]
    wrapper_class=structlog.make_filtering_bound_logger(logging.NOTSET),
    context_class=dict,
    logger_factory=structlog.PrintLoggerFactory(),
    cache_logger_on_first_use=True,
)


logger = structlog.get_logger()
bind_contextvars(service='backend')

if __name__ == '__main__':
    logger.info('Hello, world!')
    logger.info('Hello, world!', user_id=1)

    logger.info('recived', request=[dict(a=1, b=2), dict(a=3, b=4)])

    log = logger.bind(request=[dict(a=1, b=2), dict(a=3, b=4)])
    log.info('recived')

    try:
        1 / 0  # noqa: B018 # pyright: ignore[reportUnusedExpression]
    except ZeroDivisionError:
        logger.exception('Cannot compute!')
