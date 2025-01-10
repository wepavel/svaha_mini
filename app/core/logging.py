# import inspect
# import logging
# from app.core.config import settings
# from pathlib import Path
# from typing import Any
# from datetime import datetime
# from collections.abc import Mapping
# import orjson
# import traceback
# from enum import Enum
# from fastapi.logger import logger as fastapi_logger
#
# class ContextFilter(logging.Filter):
#     def filter(self, record):
#         frame = inspect.currentframe()
#         while frame:
#             co = frame.f_code
#             filename = co.co_filename
#             func_name = co.co_name
#             if 'logging' not in filename:  # Исключаем логирующий модуль
#                 break
#             frame = frame.f_back
#
#         record.filename = filename
#         record.funcName = func_name
#         return True
#
#
# # class JSONFormatter(logging.Formatter):
# #     def __init__(self) -> None:
# #         super().__init__()
# #         self.level = settings.LOG_LEVEL
# #
# #     def format(self, record: logging.LogRecord) -> str:
# #         message: dict[str, Any] = {
# #             # 'request_id': event_id.get(),
# #             'timestamp': datetime.fromtimestamp(record.created).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
# #             'level': record.levelname.lower(),
# #             'filename': record.filename,
# #             'funcName': record.funcName,
# #         }
# #
# #         if isinstance(record.msg, dict):
# #             message.update(record.msg)
# #         elif isinstance(record.msg, str):
# #             if 'message' in record.__dict__ and record.message:
# #                 message.update(dict(message=record.message))
# #             elif not record.args:
# #                 message.update(dict(message=record.msg))
# #             else:
# #                 message.update(dict(message=record.msg % record.args))
# #
# #         if record.exc_info:
# #             message.update(dict(trace=str(traceback.format_exc())))
# #
# #         return self._serialize(message).decode()
# #
# #     @classmethod
# #     def _serialize(cls, message: Mapping[str, Any]) -> bytes:
# #         def default(o: Any) -> str | float:
# #             if isinstance(o, Enum):
# #                 return o.value
# #             if isinstance(o, datetime):
# #                 return o.isoformat()
# #             return str(o)
# #
# #         return orjson.dumps(message, default=default, option=orjson.OPT_NON_STR_KEYS)
#
# class JSONFormatter(logging.Formatter):
#     def format(self, record: logging.LogRecord) -> str:
#         message: dict[str, Any] = {
#             'timestamp': datetime.fromtimestamp(record.created).strftime('%Y-%m-%dT%H:%M:%S.%fZ'),
#             'level': record.levelname.lower(),
#             'message': record.getMessage(),
#             'logger': record.name,
#         }
#         if hasattr(record, 'request_id'):
#             message['request_id'] = record.request_id
#         if record.exc_info:
#             message['exception'] = self.formatException(record.exc_info)
#         return orjson.dumps(message).decode()
#
# class StreamToLogger:
#     """
#     Fake file-like stream object that redirects writes to a logger instance.
#     """
#
#     def __init__(self, logger, log_level):
#         self.logger = logger
#         self.log_level = settings.LOG_LEVEL
#         self.linebuf = ''
#
#     def write(self, buf):
#         for line in buf.rstrip().splitlines():
#             self.logger.log(self.log_level, line.rstrip())
#
#     def flush(self):
#         pass
#
#     def isatty(self) -> bool:
#         return False
#
#
# # log_dir = Path(settings.LOG_PATH)
# # log_dir.mkdir(parents=True, exist_ok=True)
# # log_file = log_dir / 'app.log'
#
# # logging.basicConfig(
# #     # filename="logs/vc_service.log",
# #     # format='%(asctime)s %(message)s',
# #     format='%(asctime)s - %(name)s - %(levelname)s - %(message)s [%(filename)s:%(funcName)s]',
# #     # filemode='w'
# # )
#
# def setup_logger() -> logging.Logger:
#     logging.basicConfig(format='%(message)s')
#     logger = logging.getLogger('app_logger')
#     logger.setLevel(settings.LOG_LEVEL)
#
#     context_filter = ContextFilter()
#     logger.addFilter(context_filter)
#
#     json_formatter = JSONFormatter()
#     handler = logging.StreamHandler()
#     handler.setFormatter(json_formatter)
#     logger.handlers = [handler]
#
#     return logger
#
#
# def setup_logging():
#     # Настройка корневого логгера
#     root_logger = logging.getLogger()
#     root_logger.setLevel(logging.INFO)
#
#     # Удаление всех существующих обработчиков
#     for handler in root_logger.handlers[:]:
#         root_logger.removeHandler(handler)
#
#     # Добавление нового обработчика с JSON форматтером
#     json_handler = logging.StreamHandler()
#     json_handler.setFormatter(JSONFormatter())
#     root_logger.addHandler(json_handler)
#
#     # Настройка логгера uvicorn.access
#     uvicorn_access_logger = logging.getLogger("uvicorn.access")
#     uvicorn_access_logger.handlers = [json_handler]
#
#     # Настройка логгера uvicorn.error
#     uvicorn_error_logger = logging.getLogger("uvicorn.error")
#     uvicorn_error_logger.handlers = [json_handler]
#
#     # Настройка логгера FastAPI
#     fastapi_logger.handlers = [json_handler]
#
# logger = setup_logger()
# # logger = logging.getLogger('app_logger')
# # logger.setLevel(logging.DEBUG)
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


import logging
import os
import traceback
from collections.abc import Mapping
from datetime import datetime, timezone
from enum import Enum
from typing import Any
from typing import Union

import orjson
import structlog
from structlog.contextvars import bind_contextvars, clear_contextvars
from dotenv import load_dotenv

# from app.api.middleware.request_id import event_id
from app.core.config import settings
import inspect
import ipaddress
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
