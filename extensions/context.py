import os

from copier_templates_extensions import ContextHook
from copier.errors import UserMessageError


class ContextUpdater(ContextHook):
    def hook(self, context):
        try:
            context["BOTS_REGISTRY_URL"] = os.environ["BOTS_REGISTRY_URL"]
        except KeyError as exc:
            raise UserMessageError(f"{exc.args[0]} is not provided in environment")

        return context
