from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response
from aiogram.types import Update

from app.api.admin_web import router as admin_web_router
from app.bot.bot_instance import create_bot, create_dispatcher
from app.core.config import settings
from app.core.logger import logger
from app.database.session import init_db

bot = create_bot()
dp = create_dispatcher()


import os
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database schemas...")
    await init_db()
    logger.info("Database schemas ready.")

    # Auto-seed database if fresh
    try:
        from scripts.seed_demo_data import seed_data
        await seed_data()
    except Exception as e:
        logger.warning(f"Auto-seed check: {e}")

    # In production with WEBHOOK_URL or RENDER_EXTERNAL_URL configured
    webhook_base = settings.WEBHOOK_URL or os.environ.get("RENDER_EXTERNAL_URL", "")
    if webhook_base:
        webhook_target = webhook_base.rstrip("/")
        if not webhook_target.endswith("/api/v1/webhooks/telegram"):
            webhook_target = f"{webhook_target}/api/v1/webhooks/telegram"

        webhook_info = await bot.get_webhook_info()
        if webhook_info.url != webhook_target:
            logger.info(f"Setting Telegram webhook to: {webhook_target}")
            await bot.set_webhook(
                url=webhook_target,
                secret_token=settings.WEBHOOK_SECRET or None,
                drop_pending_updates=True,
            )
    yield

    webhook_base = settings.WEBHOOK_URL or os.environ.get("RENDER_EXTERNAL_URL", "")
    if webhook_base:
        logger.info("Removing Telegram webhook...")
        await bot.delete_webhook()
    await bot.session.close()


app = FastAPI(
    title=f"{settings.APP_NAME} Store API",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount Static Files & Web Admin Panel
static_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "web", "static"))
if os.path.exists(static_dir):
    app.mount("/static", StaticFiles(directory=static_dir), name="static")

app.include_router(admin_web_router)


@app.get("/")
async def root_redirect():
    """Redirect root to admin dashboard."""
    return RedirectResponse(url="/admin")


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "app": settings.APP_NAME,
        "currency": settings.CURRENCY_SYMBOL,
    }


@app.post("/api/v1/webhooks/telegram")
async def telegram_webhook(request: Request) -> Response:
    """Telegram webhook endpoint."""
    if settings.WEBHOOK_SECRET:
        secret = request.headers.get("X-Telegram-Bot-Api-Secret-Token")
        if secret != settings.WEBHOOK_SECRET:
            return Response(content="Forbidden", status_code=403)

    data = await request.json()
    update = Update.model_validate(data, context={"bot": bot})
    await dp.feed_update(bot, update)
    return Response(status_code=200)


async def run_polling():
    """Run bot in standalone long-polling mode (ideal for local testing)."""
    logger.info("Starting bot in polling mode...")
    await init_db()
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)


if __name__ == "__main__":
    import asyncio
    asyncio.run(run_polling())
