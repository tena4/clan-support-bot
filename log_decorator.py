from functools import wraps
from logging import Logger

from discord import ApplicationContext, Interaction


class CommandLogDecorator:
    def __init__(self, logger: Logger) -> None:
        self.logger = logger

    def info(self, message):
        def _log_decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                if len(args) >= 2:
                    ctx: ApplicationContext = args[1]
                    extra = {
                        "guild_id": ctx.guild_id,
                        "channel_id": ctx.channel_id,
                        "user_id": ctx.user.id if ctx.user else None,
                    }
                    self.logger.info(message, extra={"json_fields": extra})

                else:
                    self.logger.error(f"wrong number of arguments with {message}")

                return await func(*args, **kwargs)

            return wrapper

        return _log_decorator

    def error(self, message):
        def _log_decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                if len(args) == 3:
                    ctx: ApplicationContext = args[1]
                    err = args[2]
                    extra = {
                        "guild_id": ctx.guild_id,
                        "channel_id": ctx.channel_id,
                        "user_id": ctx.user.id if ctx.user else None,
                        "error": err,
                    }
                    self.logger.error(message, extra={"json_fields": extra})

                else:
                    self.logger.error(f"wrong number of arguments with {message}")

                return await func(*args, **kwargs)

            return wrapper

        return _log_decorator


class ButtonLogDecorator:
    def __init__(self, logger: Logger) -> None:
        self.logger = logger

    def log(self, message):
        def _log_decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                if len(args) == 3:
                    interaction: Interaction = args[2]
                    extra = {
                        "guild_id": interaction.guild_id,
                        "channel_id": interaction.channel_id,
                        "message_id": interaction.message.id if interaction.message else None,
                        "user_id": interaction.user.id if interaction.user else None,
                    }
                    self.logger.info(message, extra={"json_fields": extra})

                else:
                    self.logger.error(f"wrong number of arguments with {message}")

                return await func(*args, **kwargs)

            return wrapper

        return _log_decorator


class CallbackLogDecorator:
    def __init__(self, logger: Logger) -> None:
        self.logger = logger

    def info(self, message):
        def _log_decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                if len(args) == 2:
                    interaction: Interaction = args[1]
                    extra = {
                        "guild_id": interaction.guild_id,
                        "channel_id": interaction.channel_id,
                        "message_id": interaction.message.id if interaction.message else None,
                        "user_id": interaction.user.id if interaction.user else None,
                    }
                    self.logger.info(message, extra={"json_fields": extra})

                else:
                    self.logger.error(f"wrong number of arguments with {message}")

                return await func(*args, **kwargs)

            return wrapper

        return _log_decorator

    def error(self, message):
        def _log_decorator(func):
            @wraps(func)
            async def wrapper(*args, **kwargs):
                if len(args) == 3:
                    err: Exception = args[1]
                    interaction: Interaction = args[2]
                    extra = {
                        "guild_id": interaction.guild_id,
                        "channel_id": interaction.channel_id,
                        "message_id": interaction.message.id if interaction.message else None,
                        "user_id": interaction.user.id if interaction.user else None,
                    }
                    self.logger.error(message, extra={"json_fields": extra}, exc_info=err)

                else:
                    self.logger.error(f"wrong number of arguments with {message}")

                return await func(*args, **kwargs)

            return wrapper

        return _log_decorator
