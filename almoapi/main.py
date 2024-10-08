"""The main ALMoAPI module. Contains the FastAPI server and endpoints."""

import asyncio
import os
import pathlib
import platform
import signal
from loguru import logger
from typing import Optional

from auth import AuthManager
from common import gen_logging, model
from common.args import convert_args_to_dict, init_argparser
from common.actions import branch_to_actions
from common.signals import signal_handler
from config.config import config
from endpoints.server import start_api

from backends.exllamav2.version import check_exllama_version


async def entrypoint_async():
    """Async entry function for program startup"""

    host = config.network.host
    port = config.network.port

    gen_logging.broadcast_status()

    # If an initial model name is specified, create a container
    # and load the model
    if config.model.model_name:
        await model.load_model(
            model=config.model,
            draft=config.draft_model,
        )

        # Load loras after loading the model
        if config.lora.loras:
            lora_dir = pathlib.Path(config.lora.lora_dir)
            # TODO: remove model_dump()
            await model.container.load_loras(
                lora_dir.resolve(), **config.lora.model_dump()
            )

    # If an initial embedding model name is specified, create a separate container
    # and load the model
    embedding_model_name = config.embeddings.embedding_model_name
    if embedding_model_name:
        embedding_model_path = pathlib.Path(config.embeddings.embedding_model_dir)
        embedding_model_path = embedding_model_path / embedding_model_name

        try:
            # TODO: remove model_dump()
            await model.load_embedding_model(
                embedding_model_path, **config.embeddings.model_dump()
            )
        except ImportError as ex:
            logger.error(ex.msg)

    await start_api(host, port)


def entrypoint(arguments: Optional[dict] = None):
    # Set up signal aborting
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)

    # Parse and override config from args
    if arguments is None:
        parser = init_argparser()
        arguments = convert_args_to_dict(parser.parse_args(), parser)

    # load config
    config.load(arguments)

    # setup auth
    AuthManager.setup()

    # branch to default paths if required
    if branch_to_actions():
        return

    # Check exllamav2 version and give a descriptive error if it's too old
    # Skip if launching unsafely
    if config.developer.unsafe_launch:
        logger.warning(
            "UNSAFE: Skipping ExllamaV2 version check.\n"
            "If you aren't a developer, please keep this off!"
        )
    else:
        check_exllama_version()

    # Enable CUDA malloc backend
    if config.developer.cuda_malloc_backend:
        os.environ["PYTORCH_CUDA_ALLOC_CONF"] = "backend:cudaMallocAsync"
        logger.warning("EXPERIMENTAL: Enabled the pytorch CUDA malloc backend.")

    # Use Uvloop/Winloop
    if config.developer.uvloop:
        if platform.system() == "Windows":
            from winloop import install  # type: ignore
        else:
            from uvloop import install  # type: ignore

        # Set loop event policy
        install()

        logger.warning("EXPERIMENTAL: Running program with Uvloop/Winloop.")

    # Set the process priority
    if config.developer.realtime_process_priority:
        import psutil

        current_process = psutil.Process(os.getpid())
        if platform.system() == "Windows":
            current_process.nice(psutil.REALTIME_PRIORITY_CLASS)
        else:
            current_process.nice(psutil.IOPRIO_CLASS_RT)

        logger.warning(
            "EXPERIMENTAL: Process priority set to Realtime. \n"
            "If you're not running on administrator/sudo, the priority is set to high."
        )

    # Enter into the async event loop
    asyncio.run(entrypoint_async())


if __name__ == "__main__":
    entrypoint()
