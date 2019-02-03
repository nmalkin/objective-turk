import logging

import colorlog

import objective_turk.objective_turk
import objective_turk.create_hit


def color_logs():
    """
    Enable colorful logs
    """
    handler = colorlog.StreamHandler()
    handler.setFormatter(
        colorlog.ColoredFormatter(
            "%(log_color)s%(asctime)s - %(name)s - %(levelname)s - %(message)s",
            log_colors={
                "DEBUG": "cyan",
                "INFO": "green",
                "WARNING": "yellow",
                "ERROR": "red",
                "CRITICAL": "red,bg_white",
            },
        )
    )

    objective_turk.objective_turk.logger.addHandler(handler)
    objective_turk.objective_turk.logger.propagate = False

    objective_turk.create_hit.logger.addHandler(handler)
    objective_turk.create_hit.logger.propagate = False

    logging.getLogger().handlers.pop()
    logging.getLogger().addHandler(handler)
