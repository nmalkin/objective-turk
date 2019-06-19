"""
Helper for importing the objective_turk library with convenient defaults
"""

import logging
import os
import pathlib

from objective_turk import *

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

env_production = os.getenv("MTURK_PRODUCTION")
if env_production is None:
    logger.info("MTurk environment not specified; assuming sandbox")
    environment = Environment.sandbox
elif env_production.lower() == "true":
    environment = Environment.production
else:
    environment = Environment.sandbox

profile = os.getenv("AWS_PROFILE")
if profile is None:
    logger.critical("AWS_PROFILE not specified")
    import sys

    sys.exit(1)

db_path = pathlib.Path("./data/raw/turk") / f"{profile}_{environment.value}.db"
init(environment, db_path)
