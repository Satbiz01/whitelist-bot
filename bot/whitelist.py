import discord
from discord.ext import commands
from aiohttp import web
import asyncio
import json
import os

# ─────────────────────────────────────────
#  НАСТРОЙКИ — замени на свои значения
# ─────────────────────────────────────────
BOT_TOKEN = os.environ.get("BOT_TOKEN")          # токен из discord.dev
WHITELIST_CHANNEL_ID = 1506248547169730570       # ID канала где работают команды
ADMIN_ROLE_NAME = "👑owner👑"              # роль которая может управлять вайтлистом
API_PORT = 8080                        # порт для HTTP запросов от Roblox
WHITELIST_FILE = "whitelist.json"      # файл хранения
# ─────────────────────────────────────────

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

# Загрузка вайтлиста из файла
def load_whitelist():
    if os.path.exists(WHITELIST_FILE):
        with open(WHITELIST_FILE, "r") as f:
            return json.load(f)
    return {}

# Сохранение вайтлиста в файл
def save_whitelist(data):
    with open(WHITELIST_FILE, "w") as f:
        json.dump(data, f, indent=2)

whitelist = load_whitelist()

# Проверка прав администратора
def is_admin(ctx):
    return any(role.name == ADMIN_ROLE_NAME for role in ctx.author.roles)

# ─────────────────────────────────────────
#  DISCORD КОМАНДЫ
# ─────────────────────────────────────────

@bot.event
async def on_ready():
    print(f"Бот запущен: {bot.user}")

@bot.command(name="whitelist")
async def whitelist_cmd(ctx, action: str = None, roblox_id: str = None, *, note: str = ""):
    if ctx.channel.id != WHITELIST_CHANNEL_ID:
        return

    if not is_admin(ctx):
        await ctx.send("❌ У тебя нет прав для этой команды.")
        return

    if action is None:
        await ctx.send("📋 Использование: `!whitelist add <ID>`, `!whitelist remove <ID>`, `!whitelist check <ID>`, `!whitelist list`")
        return

    # Добавить игрока
    if action == "add":
        if roblox_id is None:
            await ctx.send("❌ Укажи Roblox ID: `!whitelist add 12345678`")
            return
        if roblox_id in whitelist:
            await ctx.send(f"⚠️ ID `{roblox_id}` уже в вайтлисте.")
            return
        whitelist[roblox_id] = {
            "added_by": str(ctx.author),
            "note": note
        }
        save_whitelist(whitelist)
        await ctx.send(f"✅ ID `{roblox_id}` добавлен в вайтлист.")

    # Убрать игрока
    elif action == "remove":
        if roblox_id is None:
            await ctx.send("❌ Укажи Roblox ID: `!whitelist remove 12345678`")
            return
        if roblox_id not in whitelist:
            await ctx.send(f"⚠️ ID `{roblox_id}` не найден в вайтлисте.")
            return
        del whitelist[roblox_id]
        save_whitelist(whitelist)
        await ctx.send(f"🗑️ ID `{roblox_id}` удалён из вайтлиста.")

    # Проверить игрока
    elif action == "check":
        if roblox_id is None:
            await ctx.send("❌ Укажи Roblox ID: `!whitelist check 12345678`")
            return
        if roblox_id in whitelist:
            info = whitelist[roblox_id]
            await ctx.send(f"✅ ID `{roblox_id}` **в вайтлисте**.\nДобавил: {info.get('added_by', '?')}\nПометка: {info.get('note', '-')}")
        else:
            await ctx.send(f"❌ ID `{roblox_id}` **не в вайтлисте**.")

    # Список всех
    elif action == "list":
        if not whitelist:
            await ctx.send("📋 Вайтлист пустой.")
            return
        ids = "\n".join([f"`{uid}` — {info.get('note', '') or info.get('added_by', '')}" for uid, info in whitelist.items()])
        await ctx.send(f"📋 **Вайтлист ({len(whitelist)} игроков):**\n{ids}")

    else:
        await ctx.send("❌ Неизвестное действие. Используй: `add`, `remove`, `check`, `list`")

# ─────────────────────────────────────────
#  HTTP СЕРВЕР ДЛЯ ROBLOX
# ─────────────────────────────────────────

async def handle_check(request):
    """Roblox запрашивает: /check?id=12345678"""
    roblox_id = request.rel_url.query.get("id", "")
    if not roblox_id:
        return web.json_response({"whitelisted": False, "error": "no id"}, status=400)

    whitelisted = roblox_id in whitelist
    return web.json_response({"whitelisted": whitelisted})

async def start_api():
    app = web.Application()
    app.router.add_get("/check", handle_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", API_PORT)
    await site.start()
    print(f"HTTP API запущен на порту {API_PORT}")

# ─────────────────────────────────────────
#  ЗАПУСК
# ─────────────────────────────────────────

async def main():
    await start_api()
    await bot.start(BOT_TOKEN)

asyncio.run(main())
