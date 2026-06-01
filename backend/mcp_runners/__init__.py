from .slack import run as _slack
from .email_sender import run as _email
from .pdf_report import run as _pdf
from .data_analyzer import run as _analyzer

_RUNNERS = {
    "slack":         _slack,
    "email":         _email,
    "pdf_report":    _pdf,
    "data_analyzer": _analyzer,
}


def dispatch(tool_type: str, config: dict, result_text: str, query: str, user_params: dict) -> dict:
    runner = _RUNNERS.get(tool_type)
    if not runner:
        raise ValueError(f"Unknown tool type: {tool_type!r}")
    return runner(config, result_text, query, user_params)
