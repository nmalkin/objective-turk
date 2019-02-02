import logging

import colorlog

import objective_turk


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

    objective_turk.logger.addHandler(handler)
    objective_turk.logger.propagate = False

    logging.getLogger().handlers.pop()
    logging.getLogger().addHandler(handler)
