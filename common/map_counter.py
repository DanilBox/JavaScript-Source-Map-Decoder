class MapCounter:
    """Да, в Python есть [collections.Counter], но я захотел написать свой. :)"""

    def __init__(self) -> None:
        self._stats: dict[str, int] = {}
        self._keys: list[str] = []

    def increment(self, key: str) -> None:
        if key not in self._keys:
            self._stats[key] = 0
            self._keys.append(key)

        self._stats[key] += 1

    @property
    def total(self) -> dict[str, int]:
        return self._stats
