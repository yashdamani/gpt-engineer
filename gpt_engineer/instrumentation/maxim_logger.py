import os
import uuid

from typing import Any, List

from maxim import Logger
from maxim.logger.components import (
    ErrorConfig,
    FeedbackDict,
    FileAttachment,
    GenerationRequestMessage,
    RetrievalConfigDict,
    SpanConfigDict,
    ToolCallConfigDict,
)
from maxim.logger.components.generation import GenerationConfigDict
from maxim.logger.logger import LoggerConfigDict

_logger = None
_session = None


def get_logger() -> Logger:
    global _logger
    if _logger is None:
        config: LoggerConfigDict = {
            "id": os.getenv("MAXIM_LOGGER_ID", str(uuid.uuid4()))
        }
        api_key = os.getenv("MAXIM_API_KEY", "")
        _logger = Logger(config, api_key=api_key)
    return _logger


def start_session() -> Any:
    global _session
    logger = get_logger()
    _session = logger.session({"id": str(uuid.uuid4()), "name": "gpt-engineer"})
    repo_id = os.getenv("MAXIM_REPO_ID")
    if repo_id:
        _session.add_tag("repo_id", repo_id)
    return _session


def get_session() -> Any:
    if _session is None:
        return start_session()
    return _session


def end_session():
    if _session is not None:
        _session.end()


def start_trace(name: str, input_data: str = "") -> Any:
    session = get_session()
    trace = session.trace({"id": str(uuid.uuid4()), "name": name, "input": input_data})
    trace.add_tag("step", name)
    return trace


def end_trace(trace: Any):
    trace.end()


def _msg_to_generation(message) -> GenerationRequestMessage:
    role = getattr(message, "type", "user")
    return {"role": role, "content": message.content}


def log_generation(trace: Any, messages: List[Any], result: Any, model: str):
    gen_conf: GenerationConfigDict = {
        "id": str(uuid.uuid4()),
        "provider": "openai",
        "model": model,
        "messages": [_msg_to_generation(m) for m in messages],
    }
    generation = trace.generation(gen_conf)
    generation.result(result)


def log_retrieval(trace: Any, name: str, query: str, docs: Any):
    retr_conf: RetrievalConfigDict = {
        "id": str(uuid.uuid4()),
        "name": name,
    }
    retrieval = trace.retrieval(retr_conf)
    retrieval.input(query)
    retrieval.output(docs)


def log_tool_call(trace: Any, name: str, metadata: dict, result: Any):
    tool_conf: ToolCallConfigDict = {
        "id": str(uuid.uuid4()),
        "name": name,
    }
    tool = trace.tool_call(tool_conf)
    tool.update(metadata)
    tool.result(result)


def log_attachment(trace: Any, data: dict):
    attachment = FileAttachment(**data)
    trace.add_attachment(attachment)


def start_span(trace: Any, name: str, metadata: dict | None = None) -> Any:
    span_conf: SpanConfigDict = {
        "id": str(uuid.uuid4()),
        "name": name,
    }
    span = trace.span(span_conf)
    if metadata:
        span.add_metadata(metadata)
    return span


def end_span(span: Any):
    span.end()


def log_error(trace: Any, message: str, code: str | None = None):
    err_conf: ErrorConfig = {"message": message}
    if code:
        err_conf["code"] = code
    trace.error(err_conf)


def log_feedback(trace: Any, feedback: FeedbackDict):
    trace.feedback(feedback)


def flush():
    logger = get_logger()
    logger.flush()
