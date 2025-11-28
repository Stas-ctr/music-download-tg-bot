from .search import router as search_router
from .start import router as start_router
from .admin import router as admin_router

routers = [start_router, search_router, admin_router]   