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


def theory_controls() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="▶ Continue", callback_data="learn:continue"),
                InlineKeyboardButton(text="🛑 End", callback_data="learn:end"),
            ],
        ]
    )


def exam_controls() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🛑 End", callback_data="learn:end")],
        ]
    )


def study_keyboard_for_segment(segment: str | None) -> InlineKeyboardMarkup:
    if segment == "theory":
        return theory_controls()
    if segment == "exam":
        return exam_controls()
    return learn_controls()
