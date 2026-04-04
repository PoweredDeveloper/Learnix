from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def learn_controls() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="⏭ Skip", callback_data="learn:skip"),
                InlineKeyboardButton(text="🛑 End", callback_data="learn:end"),
            ],
        ]
    )


def task_done_keyboard(task_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Done", callback_data=f"p:done:{task_id}"),
                InlineKeyboardButton(text="⏭ Skip", callback_data=f"p:skip:{task_id}"),
            ],
        ]
    )
