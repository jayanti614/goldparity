"""
Reference data for MCX's gold contract family.

These are fixed facts published by MCX (see the hackathon brief's
"Contract Mechanics" table) — not data we fetch, just constants we
normalize against.

    trading_unit_g   : size of one lot, in grams
    purity           : fineness (995 or 999)
    quote_per_g      : the gram-denomination the exchange quotes price in
                        (e.g. GOLDM is quoted "per 10g" even though the
                        lot itself is 100g)
    expiry_window    : the day-of-month range in which the contract expires
    listed_from      : first month GOLDTEN traded (it's newer than the rest)
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class ContractSpec:
    symbol: str
    trading_unit_g: float
    purity: int
    quote_per_g: float
    expiry_window: tuple[int, int]
    listed_from: str | None = None


CONTRACTS: dict[str, ContractSpec] = {
    "GOLDM": ContractSpec(
        symbol="GOLDM",
        trading_unit_g=100,
        purity=995,
        quote_per_g=10,
        expiry_window=(3, 5),
    ),
    "GOLDTEN": ContractSpec(
        symbol="GOLDTEN",
        trading_unit_g=10,
        purity=999,
        quote_per_g=10,
        expiry_window=(27, 31),
        listed_from="2025-01-01",  # only trades from its 2025 listing onward
    ),
    "GOLDGUINEA": ContractSpec(
        symbol="GOLDGUINEA",
        trading_unit_g=8,
        purity=999,
        quote_per_g=8,
        expiry_window=(27, 31),
    ),
    "GOLDPETAL": ContractSpec(
        symbol="GOLDPETAL",
        trading_unit_g=1,
        purity=999,
        quote_per_g=1,
        expiry_window=(27, 31),
    ),
}

ALL_SYMBOLS = list(CONTRACTS.keys())


def get_contract(symbol: str) -> ContractSpec:
    key = symbol.strip().upper()
    if key not in CONTRACTS:
        raise KeyError(f"Unknown MCX gold contract symbol: {symbol!r}")
    return CONTRACTS[key]
