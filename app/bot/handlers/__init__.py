from app.bot.handlers.menu import router as menu_router
from app.bot.handlers.shop import router as shop_router
from app.bot.handlers.start import router as start_router
from app.bot.handlers.wallet_payment import router as wallet_payment_router

__all__ = ["start_router", "menu_router", "shop_router", "wallet_payment_router"]
