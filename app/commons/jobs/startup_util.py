import asyncio
from typing import Tuple

from app.commons.config.app_config import AppConfig
from app.commons.config.utils import init_app_config
from app.commons.context.app_context import AppContext, create_app_context
from app.commons.instrumentation import sentry
from app.commons.jobs.pool import JobPool
from app.commons.stats import init_global_statsd


def init_worker_resources(
    pool_name: str = "stripe"
) -> Tuple[AppConfig, AppContext, JobPool]:
    """

    :return: a tuple containing the app config, a pared version of the web app_context and a job pool for executing
    tasks
    """

    app_config = init_app_config()

    if app_config.SENTRY_CONFIG:
        sentry.init_sentry_sdk(app_config.SENTRY_CONFIG)

    # set up global statsd
    init_global_statsd(
        prefix=app_config.GLOBAL_STATSD_PREFIX,
        host=app_config.STATSD_SERVER,
        fixed_tags={"env": app_config.ENVIRONMENT},
    )

    loop = asyncio.get_event_loop()
    app_context = loop.run_until_complete(create_app_context(app_config))
    stripe_pool = JobPool.create_pool(size=10, name=pool_name)

    return app_config, app_context, stripe_pool
