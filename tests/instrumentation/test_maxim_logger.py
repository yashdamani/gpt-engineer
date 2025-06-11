import types

from gpt_engineer.applications.cli.collect import collect_learnings
from gpt_engineer.applications.cli.learning import Review
from gpt_engineer.core.default.disk_execution_env import DiskExecutionEnv
from gpt_engineer.core.default.disk_memory import DiskMemory
from gpt_engineer.core.prompt import Prompt
from gpt_engineer.instrumentation import maxim_logger


def test_start_session(monkeypatch):
    events = {}

    class DummySession:
        def add_tag(self, k, v):
            events["tag"] = (k, v)

        def end(self):
            events["end"] = True

    class DummyLogger:
        def session(self, conf):
            events["conf"] = conf
            return DummySession()

    monkeypatch.setattr(maxim_logger, "get_logger", lambda: DummyLogger())
    maxim_logger._session = None
    maxim_logger.start_session()
    assert events["conf"]["name"] == "gpt-engineer"


def test_log_generation(monkeypatch):
    events = {}

    class DummyGen:
        def result(self, out):
            events["result"] = out

    class DummyTrace:
        def generation(self, conf):
            events["conf"] = conf
            return DummyGen()

    maxim_logger.log_generation(
        DummyTrace(), [types.SimpleNamespace(content="hi")], "out", "model"
    )
    assert events["conf"]["provider"] == "openai"
    assert events["result"] == "out"


def test_flush(monkeypatch):
    events = {}

    class DummyLogger:
        def flush(self):
            events["flush"] = True

    monkeypatch.setattr(maxim_logger, "get_logger", lambda: DummyLogger())
    maxim_logger.flush()
    assert events["flush"]


def test_disk_memory_getitem_logs(monkeypatch, tmp_path):
    events = []

    def start_trace(name, inp=""):
        events.append(("start", name, inp))
        return "t"

    def log_retrieval(trace, name, query, docs):
        events.append(("retrieval", query, docs))

    def end_trace(trace):
        events.append(("end", trace))

    monkeypatch.setattr(maxim_logger, "start_trace", start_trace)
    monkeypatch.setattr(maxim_logger, "log_retrieval", log_retrieval)
    monkeypatch.setattr(maxim_logger, "end_trace", end_trace)

    memory = DiskMemory(tmp_path)
    (tmp_path / "a.txt").write_text("hello")
    assert memory["a.txt"] == "hello"
    assert events[0][0] == "start"
    assert events[-1][0] == "end"


def test_collect_learnings_logs_feedback(monkeypatch, tmp_path):
    events = []

    def start_trace(name, inp=""):
        events.append(("start", name))
        return "trace"

    def log_feedback(trace, feedback):
        events.append(("feedback", feedback))

    def log_error(trace, msg):
        events.append(("error", msg))

    def end_trace(trace):
        events.append(("end", trace))

    monkeypatch.setattr(maxim_logger, "start_trace", start_trace)
    monkeypatch.setattr(maxim_logger, "log_feedback", log_feedback)
    monkeypatch.setattr(maxim_logger, "log_error", log_error)
    monkeypatch.setattr(maxim_logger, "end_trace", end_trace)

    memory = DiskMemory(tmp_path)
    review = Review(ran=True, perfect=True, works=True, comments="ok", raw="y")
    collect_learnings(Prompt("p"), "model", 0.1, ("fn",), memory, review)

    assert events[0][0] == "start"
    assert events[1][0] == "feedback"
    assert events[-1][0] == "end"


def test_execution_env_run_logs(monkeypatch, tmp_path):
    events = []

    def start_trace(name, inp=""):
        events.append(("start", name))
        return "trace"

    def log_tool_call(trace, name, metadata, result):
        events.append(("tool", name, result))

    def log_error(trace, msg):
        events.append(("error", msg))

    def end_trace(trace):
        events.append(("end", trace))

    monkeypatch.setattr(maxim_logger, "start_trace", start_trace)
    monkeypatch.setattr(maxim_logger, "log_tool_call", log_tool_call)
    monkeypatch.setattr(maxim_logger, "log_error", log_error)
    monkeypatch.setattr(maxim_logger, "end_trace", end_trace)

    env = DiskExecutionEnv(tmp_path)
    out, err, rc = env.run("echo hi")
    assert "hi" in out
    assert rc == 0
    assert events[0][0] == "start"
    assert events[-1][0] == "end"
