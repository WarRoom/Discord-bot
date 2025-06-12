import discord
from discord.ext import commands, tasks
import asyncio
import random
from datetime import datetime, timedelta
import pytz
import os
from flask import Flask
from threading import Thread

# ==== Настройки интентов ====
intents = discord.Intents.default()
intents.message_content = True
intents.messages = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=[".", "!", "/"], intents=intents, help_command=None)

# ==== Веб-сервер для Render / UptimeRobot ====
app = Flask('')

@app.route('/')
def home():
    return "Бот жив!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# ==== Словарь для переименования канала по датам ====
channel_renames = {
    "2025-07-12": "Лето 🌞",
    "2025-07-13": "Осень 🍂",
    "2025-07-14": "Зима ❄️",
    "2025-07-15": "Весна 🌸"
}

RENAME_CHANNEL_ID = 123456789012345678  # ЗАМЕНИ на ID канала
YOUR_GUILD_ID = 123456789012345678      # ЗАМЕНИ на ID сервера

@tasks.loop(minutes=1)
async def rename_channel_loop():
    now = datetime.now(pytz.timezone("Europe/Moscow"))
    today_str = now.strftime("%Y-%m-%d")
    guild = bot.get_guild(YOUR_GUILD_ID)
    channel = guild.get_channel(RENAME_CHANNEL_ID)
    if channel and today_str in channel_renames:
        new_name = channel_renames[today_str]
        if channel.name != new_name:
            await channel.edit(name=new_name)
            print(f"Переименован канал: {new_name}")

# ==== Простейшие команды ====

@bot.command(help="Приветствие от бота")
async def hello(ctx):
    await ctx.send("Привет!")

@bot.command(help="Показывает текущее время по МСК")
async def time(ctx):
    now = datetime.now(pytz.timezone("Europe/Moscow"))
    await ctx.send(f"🕒 Сейчас {now.strftime('%d.%m.%Y %H:%M:%S')} МСК")

@bot.command(help="Подбросить монетку")
async def coin(ctx):
    await ctx.send(random.choice(["Орёл", "Решка"]))

@bot.command(help="Бросить кубик")
async def dice(ctx):
    await ctx.send(f"Выпало число: {random.randint(1, 6)}")

@bot.command(help="Выбор случайного варианта")
async def choose(ctx, *, options):
    items = [item.strip() for item in options.split(',')]
    if len(items) < 2:
        await ctx.send("Введи хотя бы 2 варианта через запятую.")
    else:
        await ctx.send(f"Я выбираю: {random.choice(items)}")

@bot.command(help="Показывает твой Discord ID")
async def myid(ctx):
    await ctx.send(f"Твой ID: {ctx.author.id}")

@bot.command(help="Удаляет сообщения")
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f"Удалено {len(deleted)} сообщений", delete_after=3)

@bot.command(help="Отправляет сообщение от имени бота (только для админов)")
@commands.has_permissions(administrator=True)
async def say(ctx, *, message):
    await ctx.message.delete()
    await ctx.send(message)

@bot.command(help="Отправляет сообщение в указанный канал (только для админов)")
@commands.has_permissions(administrator=True)
async def sayto(ctx, channel: discord.TextChannel, *, message):
    await ctx.message.delete()
    await channel.send(message)

# ==== Ответы на сообщения ====
greeting_words = ["привет", "ку", "здравствуй", "здравствуйте", "добрый день", "доброе утро", "добрый вечер", "приветствую"]
farewells = ["пока", "до свидания", "чао", "бай"]
thanks = ["спасибо", "благодарю"]
swear_words = ["мат1", "мат2", "мат3"]  # Замени на реальные
user_swears = {}

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    content = message.content.lower()
    mentioned = bot.user in message.mentions
    replied = message.reference and (await message.channel.fetch_message(message.reference.message_id)).author == bot.user

    if mentioned or replied:
        if any(word in content for word in greeting_words):
            await message.channel.send(random.choice(["Привет!", "Здравствуйте!", "Ку!", "Добрый день!", "Добро пожаловать!"]))
        elif any(word in content for word in farewells):
            await message.channel.send(random.choice(["Пока!", "До встречи!", "Чао!", "Удачи!", "До свидания!"]))
        elif "кто ты" in content:
            await message.channel.send("Я Discord-бот, созданный, чтобы помогать и развлекать!")
        elif "как дела" in content:
            await message.channel.send(random.choice(["Нормально.", "Отлично!", "Пока жив, всё хорошо.", "Лучше, чем вчера.", "Живу, работаю!"]))
        elif any(word in content for word in thanks):
            await message.channel.send("Пожалуйста!")

    await handle_swears(message)
    await bot.process_commands(message)

async def handle_swears(message):
    content = message.content.lower()
    author = message.author
    if any(word in content for word in swear_words):
        now = datetime.utcnow()
        swears = user_swears.get(author.id, [])
        swears = [t for t in swears if now - t < timedelta(hours=12)]
        swears.append(now)
        user_swears[author.id] = swears

        if len(set([t.minute for t in swears])) >= 3:
            mute_role = discord.utils.get(message.guild.roles, name="Muted")
            if mute_role:
                await author.add_roles(mute_role)
                await message.channel.send(f"{author.mention}, ты слишком много ругаешься. Тебе мут на 30 минут.")
                await asyncio.sleep(1800)
                await author.remove_roles(mute_role)
        else:
            await message.channel.send(f"{author.mention}, тише, а то админ услышит!")

# ==== Автоочистка ====
DAYS = {
    "понедельник": 0, "вторник": 1, "среда": 2,
    "четверг": 3, "пятница": 4, "суббота": 5, "воскресенье": 6
}
clean_schedule = {}
clean_report_channel_id = None

@bot.command(help="Добавляет канал в автоочистку")
@commands.has_permissions(administrator=True)
async def setclean(ctx, channel: discord.TextChannel, day: str, time_str: str):
    day = day.lower()
    if day not in DAYS:
        await ctx.send("Неверный день недели.")
        return
    try:
        hour, minute = map(int, time_str.split(":"))
        clean_schedule[channel.id] = {"day": DAYS[day], "hour": hour, "minute": minute}
        await ctx.send(f"Канал {channel.mention} будет очищаться: {day.capitalize()} {time_str}")
    except:
        await ctx.send("Неверный формат времени. Используй HH:MM")

@bot.command(help="Список каналов с автоочисткой")
async def cleanchannels(ctx):
    if not clean_schedule:
        await ctx.send("Нет каналов с автоочисткой.")
        return
    text = "📅 Расписание автоочистки:\n"
    for cid, sched in clean_schedule.items():
        channel = bot.get_channel(cid)
        day_str = list(DAYS.keys())[list(DAYS.values()).index(sched['day'])].capitalize()
        time_str = f"{sched['hour']:02d}:{sched['minute']:02d}"
        text += f"- {channel.mention if channel else f'Unknown (ID: {cid})'} — {day_str} {time_str} МСК\n"
    await ctx.send(text)

@bot.command(help="Устанавливает канал для отчётов об автоочистке")
@commands.has_permissions(administrator=True)
async def setcleanreport(ctx, channel: discord.TextChannel):
    global clean_report_channel_id
    clean_report_channel_id = channel.id
    await ctx.send(f"Канал {channel.mention} установлен для отчётов.")

@tasks.loop(minutes=1)
async def cleaner_loop():
    now = datetime.now(pytz.timezone("Europe/Moscow"))
    report_lines = []
    for cid, sched in clean_schedule.items():
        if now.weekday() == sched["day"] and now.hour == sched["hour"] and now.minute == sched["minute"]:
            channel = bot.get_channel(cid)
            if channel:
                deleted = await channel.purge(limit=1000)
                try:
                    await channel.send(f"✅ Автоочистка: удалено {len(deleted)} сообщений.", delete_after=5)
                except:
                    pass
                report_lines.append(f"- {channel.mention}: {len(deleted)} сообщений")
    if report_lines and clean_report_channel_id:
        report_channel = bot.get_channel(clean_report_channel_id)
        if report_channel:
            now_str = now.strftime("%d.%m.%Y %H:%M")
            await report_channel.send(f"🧼 **Отчёт ({now_str} МСК):**\n" + "\n".join(report_lines))

# ==== Команда help ====

@bot.command(help="Список всех команд")
async def help(ctx):
    help_text = "📖 Команды бота:\n"
    for command in bot.commands:
        if command.name not in ["say", "sayto"]:
            help_text += f".{command.name} — {command.help or 'Без описания'}\n"
    await ctx.send(help_text)

# ==== Запуск ====

@bot.event
async def on_ready():
    print(f"✅ Бот запущен как {bot.user}")
    cleaner_loop.start()
    rename_channel_loop.start()

keep_alive()
bot.run(os.getenv("TOKEN"))
