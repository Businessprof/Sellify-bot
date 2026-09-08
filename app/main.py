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


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Initializing database schemas...")
    await init_db()
    logger.info("Database schemas ready.")

    # In production with WEBHOOK_URL configured
    if settings.WEBHOOK_URL:
        webhook_info = await bot.get_webhook_info()
        if webhook_info.url != settings.WEBHOOK_URL:
            logger.info(f"Setting Telegram webhook to: {settings.WEBHOOK_URL}")
            await bot.set_webhook(
                url=settings.WEBHOOK_URL,
                secret_token=settings.WEBHOOK_SECRET,
                drop_pending_updates=True,
            )
    yield

    if settings.WEBHOOK_URL:
        logger.info("Removing Telegram webhook...")
        await bot.delete_webhook()
    await bot.session.close()


app = FastAPI(
    title=f"{settings.APP_NAME} Store API",
    version="1.0.0",
    lifespan=lifespan,
)

# Mount Web Admin Panel
app.include_router(admin_web_router)


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
