"""taixuan_translator.api.routers — API路由包"""
from taixuan_translator.api.routers.upload import router as upload_router
from taixuan_translator.api.routers.export import router as export_router
from taixuan_translator.api.routers.status import router as status_router
from taixuan_translator.api.routers.translate import router as translate_router
from taixuan_translator.api.routers.engines import router as engines_router

__all__ = [
    "upload_router",
    "export_router",
    "status_router",
    "translate_router",
    "engines_router",
]
