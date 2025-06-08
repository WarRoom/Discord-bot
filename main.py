import discord
from discord.ext import commands
import asyncio
import random
from datetime import datetime
import pytz
import os
from flask import Flask
from threading import Thread

#Создание бота с несколькими префиксами
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix=["!", ".", "/"], intents=intents, help_command=None)

# Веб-сервер для UptimeRobot
app = Flask('')

@app.route('/')
def home():
    return "Бот жив!"

def run_web():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run_web)
    t.start()

# Команда hello
@bot.command(help="Приветствие от бота")
async def hello(ctx):
    await ctx.send("Привет!")

# Команда time — текущее время
@bot.command(help="Показывает текущее время по МСК")
async def time(ctx):
    now = datetime.now(pytz.timezone("Europe/Moscow"))
    await ctx.send(f"🕒 Сейчас {now.strftime('%d.%m.%Y %H:%M:%S')} МСК")

# Команда coin — монетка
@bot.command(help="Подбросить монетку")
async def coin(ctx):
    result = random.choice(["🪙 Орёл", "🪙 Решка"])
    await ctx.send(result)

# Команда dice — кубик
@bot.command(help="Бросить кубик")
async def dice(ctx):
    result = random.randint(1, 6)
    await ctx.send(f"🎲 Выпало число: {result}")

# Команда choose — выбор из вариантов
@bot.command(help="Выбирает случайный вариант. Пример: `.choose чай, кофе, вода`")
async def choose(ctx, *, options):
    items = [item.strip() for item in options.split(',')]
    if len(items) < 2:
        await ctx.send("❗ Введи хотя бы 2 варианта через запятую.")
    else:
        choice = random.choice(items)
        await ctx.send(f"🎯 Я выбираю: **{choice}**")

# Команда myid — ID пользователя
@bot.command(help="Показывает твой Discord ID")
async def myid(ctx):
    await ctx.send(f"🆔 Твой ID: `{ctx.author.id}`")

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return
    lower_msg = message.content.lower()
    if "как дела" in lower_msg or "kak dela" in lower_msg:
        responses = [
            "Отлично! 😄",
            "Лучше, чем всегда!",
            "Бывало и лучше...",
            "Плохо, но не сдаюсь!",
            "Отлично, а у тебя как?",
            "Нормально. Спасибо, что спросил!"
        ]
        await message.channel.send(random.choice(responses))
    await bot.process_commands(message)

# Автоматическая справка
@bot.command(name="help", help="Показывает список всех команд")
async def help_command(ctx):
    help_text = "**📖 Команды бота:**
"
    for command in bot.commands:
        if command.name not in ["say", "sayto"]:
            help_text += f"**.{command.name}** — {command.help or 'Без описания'}
"
    await ctx.send(help_text)

# Очистка
DAYS = {
    "понедельник": 0,
    "вторник": 1,
    "среда": 2,
    "четверг": 3,
    "пятница": 4,
    "суббота": 5,
    "воскресенье": 6
}

clean_schedule = {}

@bot.event
async def on_ready():
    print(f'✅ Бот запущен как {bot.user}')
    cleaner_loop.start()

@bot.command(help="Добавляет канал в автоочистку. Пример: .setclean #канал воскресенье 03:00")
async def setclean(ctx, channel: discord.TextChannel, day: str, time_str: str):
    day = day.lower()
    if day not in DAYS:
        await ctx.send("⚠️ День недели должен быть на русском: понедельник-воскресенье.")
        return
    try:
        hour, minute = map(int, time_str.split(":"))
        clean_schedule[channel.id] = {
            "day": DAYS[day],
            "hour": hour,
            "minute": minute
        }
        await ctx.send(f"✅ Канал **{channel.mention}** добавлен в расписание автоочистки: **{day.capitalize()} {hour:02d}:{minute:02d}** МСК.")
    except:
        await ctx.send("❗ Формат времени должен быть HH:MM. Пример: `03:00`")

@bot.command(help="Показывает все каналы с автоочисткой.")
async def cleanchannels(ctx):
    if not clean_schedule:
        await ctx.send("📭 Список каналов для автоочистки пуст.")
        return
    text = "**🧼 Расписание автоочистки каналов:**
"
    for cid, sched in clean_schedule.items():
        channel = bot.get_channel(cid)
        day_str = list(DAYS.keys())[list(DAYS.values()).index(sched['day'])].capitalize()
        time_str = f"{sched['hour']:02d}:{sched['minute']:02d}"
        text += f"- {channel.mention if channel else f'Unknown (ID: {cid})'} — **{day_str} {time_str} МСК**
"
    await ctx.send(text)

@bot.command(help="Удаляет сообщения. Пример: .purge 100")
@commands.has_permissions(manage_messages=True)
async def purge(ctx, amount: int):
    deleted = await ctx.channel.purge(limit=amount)
    await ctx.send(f"**🧹 Удалено {len(deleted)} сообщений**", delete_after=3)

@bot.loop(minutes=1)
async def cleaner_loop():
    now = datetime.now(pytz.timezone("Europe/Moscow"))
    for cid, sched in clean_schedule.items():
        if now.weekday() == sched["day"] and now.hour == sched["hour"] and now.minute == sched["minute"]:
            channel = bot.get_channel(cid)
            if channel:
                deleted = await channel.purge(limit=1000)
                await channel.send(f"**Перезагрузка бота...**
✅ **Выполнено очищение чата: ({len(deleted)})**")
    await asyncio.sleep(60)

keep_alive()
bot.run(os.getenv("TOKEN"))