# ==================== Текущие работы ====================


# ==================== Работы на сегодня ====================
@router.callback_query(F.data == "master_today_orders")
async def show_today_orders(callback: CallbackQuery, master: Master, master_service: MasterService, bot: Bot):
    """Показать заказы мастера на сегодня"""
    orders = await master_service.get_today_orders(master.id)
    
    if not orders:
        await callback.message.edit_text(
            "📅 На сегодня нет активных заказов.",
            reply_markup=master_orders_kb()
        )
        await callback.answer()
        return
    
    text = "📅 Работы на сегодня:\n\n"
    for order in orders:
        emoji = get_status_emoji(order.status.value)
        text += (
            f"{emoji} #{order.number}\n"
            f" Клиент: {order.client_name}\n"
            f" Адрес: {order.address}\n"
            f" Время: {order.datetime.strftime('%d.%m %H:%M')}\n"
            f" Статус: {order.status.value}\n\n"
        )
    
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Изменить #{o.number}", callback_data=f"edit_order_{o.id}")]
            for o in orders
        ] + [[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_orders")]])
    )
    await callback.answer()

# ==================== Все работы ====================
@router.callback_query(F.data == "master_all_orders")
async def show_all_orders(callback: CallbackQuery, master: Master, master_service: MasterService, bot: Bot):
    """Показать все заказы мастера"""
    orders = await master_service.get_master_orders(master.id)
    
    if not orders:
        await callback.message.edit_text(
            "📋 У вас нет заказов.",
            reply_markup=master_orders_kb()
        )
        await callback.answer()
        return
    
    text = "📋 Все работы:\n\n"
    for order in orders:
        emoji = get_status_emoji(order.status.value)
        text += (
            f"{emoji} #{order.number}\n"
            f" Клиент: {order.client_name}\n"
            f" Адрес: {order.address}\n"
            f" Время: {order.datetime.strftime('%d.%m %H:%M')}\n"
            f" Статус: {order.status.value}\n\n"
        )
    
    active_orders = [o for o in orders if o.status in [OrderStatus.new, OrderStatus.confirmed, OrderStatus.in_progress, OrderStatus.arrived]]
    await callback.message.edit_text(
        text,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text=f"Изменить #{o.number}", callback_data=f"edit_order_{o.id}")]
            for o in active_orders
        ] + [[InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_orders")]])
    )
    await callback.answer()

# ==================== Архив ====================
@router.callback_query(F.data == "master_orders_archive")
async def show_archive_orders(callback: CallbackQuery, master: Master, master_service: MasterService):
    """Показать завершенные заказы"""
    orders = await master_service.get_master_orders(master.id)
    completed = [o for o in orders if o.status == OrderStatus.completed]
    
    if not completed:
        await callback.message.edit_text(
            "✅ Архив пуст",
            reply_markup=master_orders_kb()
        )
        await callback.answer()
        return
    
    text = "✅ Завершенные заявки:\n\n"
    total_profit = 0
    
    for order in completed[:10]:
        text += (
            f"#{order.number} - {order.client_name}\n"
            f" Прибыль: {order.profit} ₽\n"
        )
        total_profit += order.profit
    
    text += f"\n💎 Общая прибыль: {total_profit} ₽"
    
    await callback.message.edit_text(text, reply_markup=master_orders_kb())
    await callback.answer()

# ==================== Изменение статуса заказа ====================
@router.callback_query(F.data.startswith("edit_order_"))
async def edit_order(callback: CallbackQuery, master: Master, order_service: OrderService, master_service: MasterService, bot: Bot):
    """Изменение статуса заказа"""
    order_id = int(callback.data.split("_")[2])
    order = await order_service.order_repo.get(order_id)
    
    if not order:
        await callback.message.edit_text(
            "❌ Заявка не найдена!",
            reply_markup=master_orders_kb()
        )
        await callback.answer()
        return
    
    if order.status == OrderStatus.completed:
        await callback.message.edit_text(
            f"✅ Заявка #{order.number} завершена и не может быть изменена.\n\n"
            f"👥 Клиент: {order.client_name}\n"
            f"📞 Телефон: {order.phone}\n"
            f"📍 Адрес: {order.address}\n"
            f"📅 Время: {order.datetime.strftime('%d.%m %H:%M')}\n"
            f"💬 Проблема: {order.comment}",
            reply_markup=master_orders_kb()
        )
        await callback.answer()
        return
    
    text = (
        f"📋 Заявка #{order.number}\n"
        f"👥 Клиент: {order.client_name}\n"
        f"📞 Телефон: {order.phone}\n"
        f"📍 Адрес: {order.address}\n"
        f"📅 Время: {order.datetime.strftime('%d.%m %H:%M')}\n"
        f"💬 Проблема: {order.comment}\n"
        f"🔄 Статус: {order.status.value}"
    )
    
    await callback.message.edit_text(
        text,
        reply_markup=order_status_kb(order.id, order.status)
    )
    await callback.answer()

# ==================== Управление статусами ====================
@router.callback_query(F.data.startswith("confirm_"))
async def confirm_order(callback: CallbackQuery, master: Master, order_service: OrderService, master_service: MasterService, bot: Bot):
    """Подтверждение заявки мастером"""
    order_id = int(callback.data.split("_")[1])
    order = await order_service.update_status(order_id, OrderStatus.confirmed)
    
    # Графикни yangilash
    await master_service.update_schedule(master.id, order.datetime, "busy")
    await order_service.session.commit()
    
    await notify_admins(
        bot,
        f"✅ Мастер принял заказ!\n\n"
        f"👤 Мастер: {master.name}\n"
        f"📋 Заказ: #{order.number}\n"
        f"👥 Клиент: {order.client_name}\n"
        f"📞 Телефон: {order.phone}\n"
        f"📍 Адрес: {order.address}\n"
        f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}"
    )
    
    await callback.message.edit_text(
        f"✅ Вы подтвердили заявку #{order.number}!\n\n"
        f"👥 Клиент: {order.client_name}\n"
        f"📞 Телефон: {order.phone}\n"
        f"📍 Адрес: {order.address}\n"
        f"💬 Проблема: {order.comment}\n"
        f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}",
        reply_markup=order_status_kb(order.id, order.status)
    )
    await callback.answer("✅ Заявка подтверждена")

@router.callback_query(F.data.startswith("depart_"))
async def depart_order(callback: CallbackQuery, master: Master, order_service: OrderService, bot: Bot):
    """Выезд к клиенту"""
    order_id = int(callback.data.split("_")[1])
    order = await order_service.update_status(order_id, OrderStatus.in_progress)
    
    await notify_admins(
        bot,
        f"🚗 Мастер выехал на заказ!\n\n"
        f"👤 Мастер: {master.name}\n"
        f"📋 Заказ: #{order.number}\n"
        f"👥 Клиент: {order.client_name}\n"
        f"📞 Телефон: {order.phone}\n"
        f"📍 Адрес: {order.address}\n"
        f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}"
    )
    
    await callback.message.edit_text(
        f"🚗 Вы выехали на заявку #{order.number}!\n\n"
        f"👥 Клиент: {order.client_name}\n"
        f"📞 Телефон: {order.phone}\n"
        f"📍 Адрес: {order.address}\n"
        f"💬 Проблема: {order.comment}\n"
        f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}",
        reply_markup=order_status_kb(order.id, order.status)
    )
    await callback.answer("🚗 В пути")

@router.callback_query(F.data.startswith("arrive_"))
async def arrive_order(callback: CallbackQuery, master: Master, order_service: OrderService, bot: Bot):
    """Прибытие на место"""
    order_id = int(callback.data.split("_")[1])
    order = await order_service.update_status(order_id, OrderStatus.arrived)
    
    await notify_admins(
        bot,
        f"🏠 Мастер прибыл на место!\n\n"
        f"👤 Мастер: {master.name}\n"
        f"📋 Заказ: #{order.number}\n"
        f"👥 Клиент: {order.client_name}\n"
        f"📞 Телефон: {order.phone}\n"
        f"📍 Адрес: {order.address}\n"
        f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}"
    )
    
    await callback.message.edit_text(
        f"🏠 Вы прибыли на заявку #{order.number}!\n\n"
        f"👥 Клиент: {order.client_name}\n"
        f"📞 Телефон: {order.phone}\n"
        f"📍 Адрес: {order.address}\n"
        f"💬 Проблема: {order.comment}\n"
        f"📅 Время: {order.datetime.strftime('%d.%m.%Y %H:%M')}\n\n"
        f"Начинайте работу.\n"
        f"После завершения нажмите 'Завершить'.",
        reply_markup=order_status_kb(order.id, order.status)
    )
    await callback.answer("🏠 Прибыли")