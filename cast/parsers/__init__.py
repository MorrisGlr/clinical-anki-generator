from collections.abc import Callable

from cast.core import ParsedQuestion


def get_parser(platform: str) -> tuple[Callable, str]:
    """Return (parse_fn, system_prompt) for the given platform."""
    if platform == "uworld":
        from cast.parsers.uworld import SYSTEM_PROMPT, parse
    elif platform == "amboss":
        from cast.parsers.amboss import SYSTEM_PROMPT, parse
    elif platform == "apgo":
        from cast.parsers.apgo import SYSTEM_PROMPT, parse
    elif platform == "nbme":
        from cast.parsers.nbme import SYSTEM_PROMPT, parse
    else:
        raise ValueError(f"Unknown platform: {platform!r}")
    return parse, SYSTEM_PROMPT
