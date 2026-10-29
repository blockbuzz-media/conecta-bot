"""Bot CONECTA (MVP, aiogram 3).

Primera pantalla: solo el selector de idioma (un globo, sin texto en un
idioma concreto). Después, todo en el idioma elegido y guardado.
Chat: relevo por identificadores internos; nunca se revela el teléfono
ni el @ personal de Telegram entre usuarios. MVP: solo texto en el chat.
Sin pagos: /premium responde que aún no está disponible.
"""
import asyncio
import sqlite3

from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, StateFilter
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message,
)

from . import db as store
from .config import ADMIN_IDS, BOT_TOKEN, DATABASE_PATH, FREE_DAILY_LIKES
from .i18n import t

router = Router()
conn = store.connect(DATABASE_PATH)


class Reg(StatesGroup):
    display_name = State()
    platform_username = State()
    age = State()
    gender = State()
    seeking = State()
    relationship = State()
    country = State()
    city = State()
    languages = State()
    interests = State()
    bio = State()
    photo = State()
    age_min = State()
    age_max = State()
    preview = State()


class Chat(StatesGroup):
    chatting = State()


def lang_of(user_id):
    user = store.get_user(conn, user_id)
    return user["language"] if user and user["language"] else "es"


def kb_lang():
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Español", callback_data="lang:es"),
        InlineKeyboardButton(text="English", callback_data="lang:en"),
    ], [
        InlineKeyboardButton(text="Português", callback_data="lang:pt"),
        InlineKeyboardButton(text="Italiano", callback_data="lang:it"),
    ]])


def kb_options(lang, options):
    buttons = [[InlineKeyboardButton(text=t(lang, key), callback_data=f"opt:{state}:{value}")]
               for key, state, value in options]
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def card_text(cand, lang):
    return (
        f"{cand['display_name']}, {cand['age']}\n"
        f"{cand['bio'] or ''}\n"
        f"{t(lang, 'label_languages')}: {cand['languages'] or '-'}\n"
        f"{t(lang, 'label_interests')}: {cand['interests'] or '-'}"
    )


def card_kb(cand_id, lang):
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=t(lang, "btn_like"), callback_data=f"like:{cand_id}"),
         InlineKeyboardButton(text=t(lang, "btn_pass"), callback_data=f"pass:{cand_id}")],
        [InlineKeyboardButton(text=t(lang, "btn_view"), callback_data=f"view:{cand_id}"),
         InlineKeyboardButton(text=t(lang, "btn_report"), callback_data=f"report:{cand_id}"),
         InlineKeyboardButton(text=t(lang, "btn_block"), callback_data=f"block:{cand_id}")],
    ])


async def show_candidate(target, user_id):
    lang = lang_of(user_id)
    cands = store.discover(conn, user_id, limit=1)
    if not cands:
        await target.answer(t(lang, "discover_empty"))
        return
    cand = cands[0]
    photo = store.get_main_photo(conn, cand["telegram_id"])
    if photo:
        await target.answer_photo(photo, caption=card_text(cand, lang),
                                  reply_markup=card_kb(cand["telegram_id"], lang))
    else:
        await target.answer(card_text(cand, lang),
                            reply_markup=card_kb(cand["telegram_id"], lang))


@router.message(Command("start"))
async def cmd_start(message: Message):
    user = store.create_or_get_user(conn, message.from_user.id)
    if not user["language"]:
        await message.answer("🌐", reply_markup=kb_lang())
        return
    await message.answer(t(user["language"], "help_text"))


@router.message(Command("idioma"))
async def cmd_lang(message: Message):
    store.create_or_get_user(conn, message.from_user.id)
    await message.answer("🌐", reply_markup=kb_lang())


@router.callback_query(F.data.startswith("lang:"))
async def set_lang(call: CallbackQuery):
    lang = call.data.split(":", 1)[1]
    store.create_or_get_user(conn, call.from_user.id)
    store.set_language(conn, call.from_user.id, lang)
    await call.answer()
    await call.message.answer(t(lang, "language_saved"))
    await call.message.answer(t(lang, "reg_start"))


@router.message(Command("ayuda"))
async def cmd_help(message: Message):
    await message.answer(t(lang_of(message.from_user.id), "help_text"))


@router.message(Command("premium"))
async def cmd_premium(message: Message):
    await message.answer(t(lang_of(message.from_user.id), "premium_not_available"))


@router.message(Command("registro"))
async def cmd_register(message: Message, state: FSMContext):
    lang = lang_of(message.from_user.id)
    await state.set_state(Reg.display_name)
    await message.answer(t(lang, "reg_start"))
    await message.answer(t(lang, "ask_display_name"))


@router.message(StateFilter(Reg.display_name))
async def reg_name(message: Message, state: FSMContext):
    await state.update_data(display_name=message.text.strip()[:50])
    await state.set_state(Reg.platform_username)
    await message.answer(t(lang_of(message.from_user.id), "ask_platform_username"))


@router.message(StateFilter(Reg.platform_username))
async def reg_username(message: Message, state: FSMContext):
    lang = lang_of(message.from_user.id)
    name = message.text.strip().lstrip("@").lower()
    if len(name) < 3 or " " in name:
        await message.answer(t(lang, "ask_platform_username"))
        return
    taken = conn.execute(
        "SELECT 1 FROM users WHERE platform_username=? AND telegram_id!=?",
        (name, message.from_user.id)).fetchone()
    if taken:
        await message.answer(t(lang, "ask_platform_username_taken"))
        return
    await state.update_data(platform_username=name)
    await state.set_state(Reg.age)
    await message.answer(t(lang, "ask_age"))


@router.message(StateFilter(Reg.age))
async def reg_age(message: Message, state: FSMContext):
    lang = lang_of(message.from_user.id)
    try:
        age = int(message.text.strip())
    except ValueError:
        age = 0
    if age < 18 or age > 100:
        await message.answer(t(lang, "ask_age_invalid"))
        return
    await state.update_data(age=age)
    await state.set_state(Reg.gender)
    await message.answer(t(lang, "ask_gender"), reply_markup=kb_options(lang, [
        ("opt_gender_female", "gender", "female"),
        ("opt_gender_male", "gender", "male"),
        ("opt_gender_nonbinary", "gender", "nonbinary"),
        ("opt_gender_prefer_not", "gender", "prefer_not"),
    ]))


@router.callback_query(F.data.startswith("opt:gender:"))
async def reg_gender(call: CallbackQuery, state: FSMContext):
    lang = lang_of(call.from_user.id)
    await state.update_data(gender=call.data.split(":")[2])
    await state.set_state(Reg.seeking)
    await call.answer()
    await call.message.answer(t(lang, "ask_seeking"), reply_markup=kb_options(lang, [
        ("opt_seeking_female", "seeking", "female"),
        ("opt_seeking_male", "seeking", "male"),
        ("opt_seeking_any", "seeking", "any"),
    ]))


@router.callback_query(F.data.startswith("opt:seeking:"))
async def reg_seeking(call: CallbackQuery, state: FSMContext):
    lang = lang_of(call.from_user.id)
    await state.update_data(seeking=call.data.split(":")[2])
    await state.set_state(Reg.relationship)
    await call.answer()
    await call.message.answer(t(lang, "ask_relationship"), reply_markup=kb_options(lang, [
        ("opt_rel_friendship", "relationship", "friendship"),
        ("opt_rel_serious", "relationship", "serious"),
        ("opt_rel_casual", "relationship", "casual"),
    ]))


@router.callback_query(F.data.startswith("opt:relationship:"))
async def reg_rel(call: CallbackQuery, state: FSMContext):
    lang = lang_of(call.from_user.id)
    await state.update_data(relationship=call.data.split(":")[2])
    await state.set_state(Reg.country)
    await call.answer()
    await call.message.answer(t(lang, "ask_country"))


def _optional(text):
    text = text.strip()
    return None if text == "-" else text[:80]


@router.message(StateFilter(Reg.country))
async def reg_country(message: Message, state: FSMContext):
    await state.update_data(country=_optional(message.text))
    await state.set_state(Reg.city)
    await message.answer(t(lang_of(message.from_user.id), "ask_city"))


@router.message(StateFilter(Reg.city))
async def reg_city(message: Message, state: FSMContext):
    await state.update_data(city=_optional(message.text))
    await state.set_state(Reg.languages)
    await message.answer(t(lang_of(message.from_user.id), "ask_languages"))


@router.message(StateFilter(Reg.languages))
async def reg_languages(message: Message, state: FSMContext):
    await state.update_data(languages=message.text.strip()[:120])
    await state.set_state(Reg.interests)
    await message.answer(t(lang_of(message.from_user.id), "ask_interests"))


@router.message(StateFilter(Reg.interests))
async def reg_interests(message: Message, state: FSMContext):
    await state.update_data(interests=message.text.strip()[:120])
    await state.set_state(Reg.bio)
    await message.answer(t(lang_of(message.from_user.id), "ask_bio"))


@router.message(StateFilter(Reg.bio))
async def reg_bio(message: Message, state: FSMContext):
    await state.update_data(bio=message.text.strip()[:150])
    await state.set_state(Reg.photo)
    await message.answer(t(lang_of(message.from_user.id), "ask_photo"))


@router.message(StateFilter(Reg.photo), F.photo)
async def reg_photo(message: Message, state: FSMContext):
    file_id = message.photo[-1].file_id
    await state.update_data(photo=file_id)
    await state.set_state(Reg.age_min)
    await message.answer(t(lang_of(message.from_user.id), "ask_age_min"))


@router.message(StateFilter(Reg.photo))
async def reg_photo_invalid(message: Message):
    await message.answer(t(lang_of(message.from_user.id), "ask_photo"))


@router.message(StateFilter(Reg.age_min))
async def reg_age_min(message: Message, state: FSMContext):
    lang = lang_of(message.from_user.id)
    try:
        value = int(message.text.strip())
    except ValueError:
        value = 0
    if value < 18 or value > 100:
        await message.answer(t(lang, "ask_age_range_invalid"))
        return
    await state.update_data(age_min=value)
    await state.set_state(Reg.age_max)
    await message.answer(t(lang, "ask_age_max"))


@router.message(StateFilter(Reg.age_max))
async def reg_age_max(message: Message, state: FSMContext):
    lang = lang_of(message.from_user.id)
    data = await state.get_data()
    try:
        value = int(message.text.strip())
    except ValueError:
        value = 0
    if value < data.get("age_min", 18) or value > 100:
        await message.answer(t(lang, "ask_age_range_invalid"))
        return
    await state.update_data(age_max=value)
    await state.set_state(Reg.preview)
    summary = (
        f"{data['display_name']}, {data['age']}\n{data['bio']}\n"
        f"{t(lang, 'label_languages')}: {data['languages']}\n"
        f"{t(lang, 'label_interests')}: {data['interests']}"
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text=t(lang, "btn_publish"), callback_data="publish"),
        InlineKeyboardButton(text=t(lang, "btn_edit"), callback_data="edit"),
    ]])
    photo = data.get("photo")
    if photo:
        await message.answer_photo(photo, caption=f"{t(lang, 'preview_title')}\n{summary}",
                                   reply_markup=kb)
    else:
        await message.answer(f"{t(lang, 'preview_title')}\n{summary}", reply_markup=kb)


@router.callback_query(F.data == "publish", StateFilter(Reg.preview))
async def publish(call: CallbackQuery, state: FSMContext):
    data = await state.get_data()
    uid = call.from_user.id
    store.update_profile(conn, uid,
                         display_name=data["display_name"],
                         platform_username=data["platform_username"],
                         age=data["age"], gender=data["gender"],
                         seeking=data["seeking"], relationship=data["relationship"],
                         country=data.get("country"), city=data.get("city"),
                         languages=data["languages"], interests=data["interests"],
                         bio=data["bio"], age_min=data["age_min"],
                         age_max=data["age_max"], status="active")
    if data.get("photo"):
        store.add_photo(conn, uid, data["photo"], is_main=True)
    await state.clear()
    await call.answer()
    await call.message.answer(t(lang_of(uid), "profile_published"))


@router.callback_query(F.data == "edit", StateFilter(Reg.preview))
async def edit_profile(call: CallbackQuery, state: FSMContext):
    await state.clear()
    await call.answer()
    await call.message.answer(t(lang_of(call.from_user.id), "reg_start"))


@router.message(Command("descubrir"))
async def cmd_discover(message: Message):
    user = store.get_user(conn, message.from_user.id)
    if not user or user["status"] != "active":
        await message.answer(t(lang_of(message.from_user.id), "profile_not_active"))
        return
    await show_candidate(message, message.from_user.id)


@router.message(Command("perfil"))
async def cmd_profile(message: Message):
    user = store.get_user(conn, message.from_user.id)
    lang = lang_of(message.from_user.id)
    if not user or not user["display_name"]:
        await message.answer(t(lang, "profile_not_active"))
        return
    photo = store.get_main_photo(conn, message.from_user.id)
    text = card_text(user, lang)
    if photo:
        await message.answer_photo(photo, caption=text)
    else:
        await message.answer(text)


@router.message(Command("pausar"))
async def cmd_pause(message: Message):
    user = store.get_user(conn, message.from_user.id)
    lang = lang_of(message.from_user.id)
    if not user or user["status"] not in ("active", "paused"):
        await message.answer(t(lang, "profile_not_active"))
        return
    new_status = "paused" if user["status"] == "active" else "active"
    store.update_profile(conn, message.from_user.id, status=new_status)
    key = "paused_done" if new_status == "paused" else "activated_done"
    await message.answer(t(lang, key))


@router.message(Command("eliminar"))
async def cmd_delete(message: Message):
    lang = lang_of(message.from_user.id)
    kb = InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="✅", callback_data="delete:yes"),
        InlineKeyboardButton(text="❌", callback_data="delete:no"),
    ]])
    await message.answer(t(lang, "delete_confirm"), reply_markup=kb)


@router.callback_query(F.data.startswith("delete:"))
async def delete_confirm(call: CallbackQuery):
    lang = lang_of(call.from_user.id)
    if call.data == "delete:yes":
        store.delete_account(conn, call.from_user.id)
        await call.message.answer(t(lang, "account_deleted"))
    else:
        await call.message.answer(t(lang, "delete_cancelled"))
    await call.answer()


@router.callback_query(F.data.startswith("like:"))
async def do_like(call: CallbackQuery, bot: Bot):
    uid, peer = call.from_user.id, int(call.data.split(":")[1])
    lang = lang_of(uid)
    if store.daily_likes(conn, uid) >= FREE_DAILY_LIKES:
        await call.answer(t(lang, "daily_limit"), show_alert=True)
        return
    is_match = store.record_action(conn, uid, peer, "like")
    await call.answer()
    if is_match:
        peer_lang = lang_of(peer)
        await call.message.answer(t(lang, "match_you"))
        try:
            await bot.send_message(peer, t(peer_lang, "match_other"))
        except Exception:
            pass
    await show_candidate(call.message, uid)


@router.callback_query(F.data.startswith("pass:"))
async def do_pass(call: CallbackQuery):
    peer = int(call.data.split(":")[1])
    store.record_action(conn, call.from_user.id, peer, "pass")
    await call.answer()
    await show_candidate(call.message, call.from_user.id)


@router.callback_query(F.data.startswith("view:"))
async def do_view(call: CallbackQuery):
    peer = int(call.data.split(":")[1])
    cand = store.get_user(conn, peer)
    lang = lang_of(call.from_user.id)
    if not cand:
        await call.answer(t(lang, "error_generic"))
        return
    text = (f"{cand['display_name']}, {cand['age']}\n{cand['bio'] or ''}\n"
            f"📍 {cand['country'] or '-'} / {cand['city'] or '-'}\n"
            f"{t(lang, 'label_languages')}: {cand['languages'] or '-'}\n"
            f"{t(lang, 'label_interests')}: {cand['interests'] or '-'}")
    await call.answer()
    await call.message.answer(text)


@router.callback_query(F.data.startswith("report:"))
async def do_report(call: CallbackQuery):
    peer = int(call.data.split(":")[1])
    store.report_user(conn, call.from_user.id, peer)
    store.record_action(conn, call.from_user.id, peer, "pass")
    await call.answer()
    await call.message.answer(t(lang_of(call.from_user.id), "reported_done"))
    await show_candidate(call.message, call.from_user.id)


@router.callback_query(F.data.startswith("block:"))
async def do_block(call: CallbackQuery):
    peer = int(call.data.split(":")[1])
    store.block_user(conn, call.from_user.id, peer)
    store.record_action(conn, call.from_user.id, peer, "pass")
    await call.answer()
    await call.message.answer(t(lang_of(call.from_user.id), "blocked_done"))
    await show_candidate(call.message, call.from_user.id)


@router.message(Command("matches"))
async def cmd_matches(message: Message):
    lang = lang_of(message.from_user.id)
    matches = store.list_matches(conn, message.from_user.id)
    if not matches:
        await message.answer(t(lang, "discover_empty"))
        return
    buttons = [[InlineKeyboardButton(
        text=f"💬 {m['display_name']}",
        callback_data=f"chat:{m['telegram_id']}")] for m in matches]
    await message.answer(t(lang, "btn_matches"),
                         reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons))


@router.callback_query(F.data.startswith("chat:"))
async def start_chat(call: CallbackQuery, state: FSMContext):
    peer = int(call.data.split(":")[1])
    lang = lang_of(call.from_user.id)
    if not store.can_message(conn, call.from_user.id, peer):
        await call.answer(t(lang, "chat_no_match"), show_alert=True)
        return
    await state.update_data(peer_id=peer)
    await state.set_state(Chat.chatting)
    await call.answer()
    await call.message.answer(t(lang, "chat_started"))


@router.message(Command("salir"), StateFilter(Chat.chatting))
async def exit_chat(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(t(lang_of(message.from_user.id), "chat_ended"))


@router.message(StateFilter(Chat.chatting), F.text)
async def relay_text(message: Message, state: FSMContext, bot: Bot):
    lang = lang_of(message.from_user.id)
    data = await state.get_data()
    peer = data.get("peer_id")
    sender = store.get_user(conn, message.from_user.id)
    if not peer or not store.can_message(conn, message.from_user.id, peer):
        await state.clear()
        await message.answer(t(lang, "chat_no_match"))
        return
    try:
        store.send_message(conn, message.from_user.id, peer, message.text)
    except ValueError:
        await state.clear()
        await message.answer(t(lang, "chat_no_match"))
        return
    peer_lang = lang_of(peer)
    name = sender["display_name"] if sender else "CONECTA"
    await bot.send_message(peer, t(peer_lang, "match_message", name=name, text=message.text))


@router.message(StateFilter(Chat.chatting), F.photo)
async def relay_photo_blocked(message: Message):
    await message.answer(t(lang_of(message.from_user.id), "chat_photo_not_supported"))


@router.message(Command("admin"))
async def cmd_admin(message: Message):
    if message.from_user.id not in ADMIN_IDS:
        await message.answer(t(lang_of(message.from_user.id), "error_generic"))
        return
    stats = store.admin_stats(conn)
    await message.answer(t(lang_of(message.from_user.id), "admin_stats", **stats))


async def main():
    if not BOT_TOKEN:
        print("Falta BOT_TOKEN en .env. Crea el bot en @BotFather y completa .env.")
        return
    bot = Bot(token=BOT_TOKEN)
    dp = Dispatcher(storage=MemoryStorage())
    dp.include_router(router)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
