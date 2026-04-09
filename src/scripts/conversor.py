

#!/usr/bin/env python3
"""Conversor de coordenadas DMS (graus/minutos/segundos) -> graus decimais.

Exemplos de entrada aceitos:
- 22°52'56"S 47°02'50"W
- 22 52 56 S, 47 02 50 W
- 22°52'56" S 47°02'50" W

Saída (4 casas decimais):
-22.8822, -47.0472
"""

from __future__ import annotations

import re
import sys
from typing import Tuple


_DMS_RE = re.compile(
    r"""(?ix)
    ^\s*
    (?P<deg>\d{1,3})\s*(?:°|\s+)\s*
    (?P<min>\d{1,2})\s*(?:'|\s+)\s*
    (?P<sec>\d{1,2}(?:\.\d+)?)\s*(?:"|\s+)?\s*
    (?P<hem>[NSEW])
    \s*$
    """
)


def dms_to_decimal(deg: float, minutes: float, seconds: float, hemisphere: str) -> float:
    """Converte DMS + hemisfério (N/S/E/W) para graus decimais."""
    decimal = float(deg) + float(minutes) / 60.0 + float(seconds) / 3600.0
    hemisphere = hemisphere.upper()
    if hemisphere in ("S", "W"):
        decimal *= -1.0
    return decimal


def parse_dms_token(token: str) -> float:
    """Faz parse de um token DMS único (ex: 22°52'56\"S) e retorna decimal."""
    token = token.strip().rstrip(",")
    m = _DMS_RE.match(token)
    if not m:
        raise ValueError(f"Token DMS inválido: {token!r}")

    deg = float(m.group("deg"))
    minutes = float(m.group("min"))
    seconds = float(m.group("sec"))
    hem = m.group("hem")

    if minutes >= 60 or seconds >= 60:
        raise ValueError(f"Minutos/segundos fora do intervalo em: {token!r}")

    return dms_to_decimal(deg, minutes, seconds, hem)


def parse_line(line: str) -> Tuple[float, float]:
    """Parseia uma linha contendo latitude e longitude em DMS."""
    line = line.strip()
    if not line:
        raise ValueError("Linha vazia")

    # Tenta separar por espaço, mas também aceita uma vírgula no meio.
    parts = [p for p in re.split(r"\s+", line.replace(",", " ")) if p]

    # Caso 1: já vem em 2 tokens tipo 22°..S 47°..W
    if len(parts) == 2:
        lat = parse_dms_token(parts[0])
        lon = parse_dms_token(parts[1])
        return lat, lon

    # Caso 2: usuário digitou separado (ex: 22 52 56 S 47 02 50 W)
    if len(parts) == 8:
        lat = dms_to_decimal(float(parts[0]), float(parts[1]), float(parts[2]), parts[3])
        lon = dms_to_decimal(float(parts[4]), float(parts[5]), float(parts[6]), parts[7])
        return lat, lon

    raise ValueError(
        "Formato inválido. Use, por exemplo: 22°52'56\"S 47°02'50\"W (ou 22 52 56 S 47 02 50 W)."
    )


def format_pair(lat: float, lon: float, decimals: int = 4) -> str:
    return f"{lat:.{decimals}f}, {lon:.{decimals}f}"


def main(argv: list[str]) -> int:
    # Modo 1: coordenadas passadas como argumentos
    if len(argv) > 1:
        # Junta tudo para permitir aspas opcionais no terminal.
        line = " ".join(argv[1:])
        try:
            lat, lon = parse_line(line)
            print(format_pair(lat, lon))
            return 0
        except ValueError as e:
            print(f"Erro: {e}", file=sys.stderr)
            return 2

    # Modo 2: lê várias linhas do usuário (até linha vazia)
    print("Cole uma coordenada por linha (ex: 22°52'56\"S 47°02'50\"W).")
    print("Para finalizar, envie uma linha vazia.\n")

    while True:
        try:
            line = input("> ").strip()
        except EOFError:
            break

        if not line:
            break

        try:
            lat, lon = parse_line(line)
            print(format_pair(lat, lon))
        except ValueError as e:
            print(f"Erro: {e}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))