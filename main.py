import asyncio
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from config import BOT_TOKEN, LOG_LEVEL, ADMIN_IDS
from middlewares import AuthMiddleware
from handlers import admin, master, common
from database.engine import init_db, DatabaseManager, get_session

from core.dependencies import ServiceMiddleware
from models import OrderStatus
from services.services import OrderService

logging.basicConfig(
    level=getattr(logging, LOG_LEVEL),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


async def auto_assign_pending_orders(bot):
    """Background task: Check and assign pending orders"""
    try:
        async with get_session() as session:
            order_service = OrderService(session)
            
            # Faqat tayinlanmagan "new" statusdagi zayvkalarni olamiz
            pending_orders = await order_service.get_orders_by_filter(status=OrderStatus.new)
            
            assigned_count = 0
            for order in pending_orders:
                # MUHIM: Avval assignment borligini tekshiramiz
                existing_assignment = await order_service.assignment_repo.get_by_order(order.id)
                if existing_assignment:
                    # Bu zayvka allaqachon tayinlangan, o'tkazib yuboramiz
                    continue
                    
                
                # Master topishga harakat qilamiz
                master = await order_service.assign_to_master(order.id)
                if master:
                    assigned_count += 1
                    
                    # Masterga xabar yuboramiz
                    from core.keyboards import order_status_kb
                    try:
                        await bot.send_message(
                            master.telegram_id,
                            f"🆕 Новая заявка #{order.number}!\n\n"
                            f"👤 Клиент: {order.client_name}\n"
                            f"📞 Телефон: {order.phone}\n"
                            f"📍 Адрес: {order.address}\n"
                            f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n"
                            f"🔧 Техника: {order.type} {order.brand} {order.model}\n"
                            f"💬 Проблема: {order.comment}",
                            reply_markup=order_status_kb(order.id, order.status)
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify master {master.id}: {e}")
                    
                    # Adminlarga xabar
                    for admin_id in ADMIN_IDS:
                        try:
                            await bot.send_message(
                                admin_id, 
                                f"🤖 Автоматически назначена заявка #{order.number} мастеру {master.name}!"
                            )
                        except Exception:
                            pass
            
            if assigned_count > 0:
                logger.info(f"Scheduler assigned {assigned_count} pending orders")
    
    except Exception as e:
        logger.error(f"Error in auto_assign_pending_orders: {e}")


async def on_startup(bot: Bot):
    await init_db()
    
    # Start scheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        auto_assign_pending_orders,
        "interval",
        minutes=5,  # Check every 5 minutes
        args=(bot,)
    )
    scheduler.start()


async def on_shutdown(bot: Bot):
    await DatabaseManager.close()


async def main():
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    
    auth_middleware = AuthMiddleware()
    dp.update.middleware(auth_middleware)

    dp.message.middleware(ServiceMiddleware())
    dp.callback_query.middleware(ServiceMiddleware())

    
    dp.include_router(common.router)
    dp.include_router(admin.router)
    dp.include_router(master.router)
    
    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.info("👋 Бот остановлен")