from dataclasses import dataclass
from typing import ClassVar

from pilot.tasks import Task, on_success, step


@dataclass(kw_only=True)
class SwitchBranchTask(Task):
    command: ClassVar[str] = "switch-branch"

    name: str
    branch: str
    force: bool = False

    def run(self) -> None:
        from pilot.managers.environment import PythonEnvManager

        app = self.bench.app(self.name)
        previous_branch = app.current_branch
        previous_sha = app.head_sha
        previous_configured_branch = app.config.branch
        env = PythonEnvManager(self.bench)

        try:
            self.checkout(app)
            self.validate(app)
            self.install(env, app)
            self.build_assets(env, app)
            app.record_branch()
        except Exception as task_error:
            if self._checkout_changed(
                app,
                previous_branch,
                previous_sha,
                previous_configured_branch,
            ):
                try:
                    self.rollback(app, env, previous_branch, previous_sha, previous_configured_branch)
                except Exception as rollback_error:
                    raise ExceptionGroup(
                        "Branch switch failed and rollback did not complete.",
                        [task_error, rollback_error],
                    ) from rollback_error
            raise

        print(f"'{self.name}' switched to '{self.branch}' successfully.")

    @on_success
    def reload_workers(self) -> dict:
        """Long-lived web and background workers hold the old app list and
        import map, so they need a restart once this task lands."""
        return {"web_only": False}

    @step("checkout", lambda self: f"Switch to branch '{self.branch}'")
    def checkout(self, app) -> None:
        app.switch_branch(self.branch, force=self.force)

    @step("validate", lambda self: f"Validate {self.name} on '{self.branch}'")
    def validate(self, app) -> None:
        app.validate()

    @step("install", lambda self: f"Reinstall {self.name}")
    def install(self, env, app) -> None:
        env.install_app(app)

    @step("assets", "Build assets")
    def build_assets(self, env, app) -> None:
        env.build_assets_for_app(app)

    @staticmethod
    def _checkout_changed(
        app,
        previous_branch: str,
        previous_sha: str,
        previous_configured_branch: str,
    ) -> bool:
        """Whether the failed operation changed the live app checkout/config."""
        return (
            app.current_branch != previous_branch
            or app.head_sha != previous_sha
            or app.config.branch != previous_configured_branch
        )

    def rollback(
        self,
        app,
        env,
        previous_branch: str,
        previous_sha: str,
        previous_configured_branch: str,
    ) -> None:
        """Restore the exact checkout and environment that were live before the switch.

        Rollback failures deliberately propagate to the caller so the task can
        report both the original failure and the incomplete restoration with
        their full tracebacks.
        """
        app.restore_revision(previous_branch, previous_sha, previous_configured_branch)
        app.record_branch()
        env.install_app(app)
        env.build_assets_for_app(app)


if __name__ == "__main__":
    SwitchBranchTask.main()
