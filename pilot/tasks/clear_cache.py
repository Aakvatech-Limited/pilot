from dataclasses import dataclass
from typing import ClassVar

from pilot.tasks import Task, step


@dataclass(kw_only=True)
class ClearCacheTask(Task):
    command: ClassVar[str] = "clear-cache"

    site: str = ""  # empty clears every site

    def run(self) -> None:
        self.clear_cache()

    @step("clear_cache", lambda self: f"Clear cache for {self.site or 'every site'}")
    def clear_cache(self) -> None:
        if self.site:
            self.bench.site(self.site).clear_cache()
        else:
            self.bench.clear_cache()


if __name__ == "__main__":
    ClearCacheTask.main()
