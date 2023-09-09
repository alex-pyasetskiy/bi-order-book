from fastapi import FastAPI, Request

from app.api import router
from app.engine import *
from app.websocket import order_book_stream
from fastapi.middleware.cors import CORSMiddleware

# LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
#
# logging.basicConfig(format=LOG_FORMAT, level=logging.DEBUG)
# log = logging.getLogger(__name__)
# log.setLevel(logging.DEBUG)

ORIGINS = [
    "http://localhost:3000",
    "localhost:3000",
    "http://localhost:8989",
    "localhost:8989"
]
def create_app():
    app = FastAPI()

    # app.add_event_handler("startup", get_db_conn)
    # app.add_event_handler("shutdown", close_db)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"]
    )

    app.include_router(router)
    app.add_api_websocket_route('/ws/{client_id}', order_book_stream)

    @app.middleware("http")
    async def response_headers_middleware(request: Request, call_next):
        response = await call_next(request)
        response.headers["Access-Control-Allow-Origin"] ="*"
        response.headers["Access-Control-Allow-Credentials"] = 'true'
        return response
    return app

APP = create_app()


# client = AsyncIOMotorClient(os.environ["MONGO_URL"])
# db = client.college


# @app.on_event("startup")
# async def startup_event():
#     loop = asyncio.get_event_loop()
#     task = loop.create_task(watch_and_print())
#     loop.add_signal_handler(signal.SIGINT, lambda: task.cancel())
#     loop.add_signal_handler(signal.SIGQUIT, lambda: task.cancel())
#     loop.add_signal_handler(signal.SIGTERM, lambda: task.cancel())
#     try:
#         loop.run_until_complete(task)
#     except asyncio.CancelledError:
#         pass

# @app.get("/")
# async def root():
#     return f"OK"
#
#
# @app.get("/register")
# async def get_client_id():
#     return C_MANAGER.register_client()
