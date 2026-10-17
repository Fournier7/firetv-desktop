"""Prepara texto para o `input text` do Android (que só aceita ASCII simples)."""
from __future__ import annotations


def prepare_text(text: str) -> tuple[str, str]:
    """Devolve (texto pronto para ir entre aspas simples, caracteres ignorados)."""
    ready: list[str] = []
    skipped: list[str] = []
    for ch in text:
        if ch == " ":
            ready.append("%s")
        elif ch == "'":
            ready.append("'\\''")
        elif ch == "%" or not ch.isascii():
            skipped.append(ch)
        else:
            ready.append(ch)
    return "".join(ready), "".join(skipped)
