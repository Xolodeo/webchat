from starlette.middleware.sessions import SessionMiddleware
from fastapi.staticfiles import StaticFiles
from jose import jwt
from passlib.context import CryptContext
from motor.motor_asyncio import AsyncIOMotorClient
from odmantic import AIOEngine, Model
from fastapi.templating import Jinja2Templates
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import FastAPI, Request, Form, Depends, HTTPException
import os

SECRET_KEY = "abdul"
ALGORITHM = "HS256"

app = FastAPI()


# Настройка хеширования паролей
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# Добавим поддержку сессий
app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY)

# Подключение к MongoDB 
client = AsyncIOMotorClient("mongodb://abdul:abdul@db:27017/users_db")
engine = AIOEngine(client=client, database="users_db")

# Модели данных через ODMantic
class User(Model):
    log_in: str
    hashed_password: str

class Chat(Model):
    chat_name: str

# Функции для хеширования пароля и его валидации
def hash_password(password: str):
    return pwd_context.hash(password)

def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)


# Папка с шаблонами
templates = Jinja2Templates(directory="frontend")

# Функция для создания токена
def create_access_token(data: dict):
    to_encode = data.copy()
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt


# Страница входа
@app.get("/log_in", response_class=HTMLResponse)
async def signin_page(request: Request):
    return templates.TemplateResponse("log_in.html", {"request": request})

# Обработка формы входа
@app.post("/log_in", response_class=HTMLResponse)
async def signin_user(request: Request, email: str = Form(...), password: str = Form(...)):
    user = await engine.find_one(User, User.log_in == email)
    if not user or not verify_password(password, user.hashed_password):
        return templates.TemplateResponse("log_in.html", {"request": request, "error": "Неверные данные для входа."})
    request.session["user"] = user.log_in
    return RedirectResponse("/choose", status_code=302)

# Выход из системы
@app.get("/logout")
async def logout(request: Request):
    request.session.pop("user", None)
    return RedirectResponse("/", status_code=302)

# Страница выбора действий
@app.get("/choose", response_class=HTMLResponse)
async def selection_page(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/log_in", status_code=302)
    return templates.TemplateResponse("choose.html", {"request": request})

# Страница создания беседы
@app.get("/begin_chat", response_class=HTMLResponse)
async def begin_chat_page(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/log_in", status_code=302)
    return templates.TemplateResponse("begin_chat.html", {"request": request})

# Обработка создания беседы
@app.post("/begin_chat", response_class=HTMLResponse)
async def begin_chat(request: Request, chat_name: str = Form(...)):
    if not request.session.get("user"):
        return RedirectResponse("/log_in", status_code=302)

    if len(chat_name) < 6:
        return templates.TemplateResponse("begin_chat.html", {"request": request, "error": "Название беседы должно содержать минимум 6 символов."})

    existing_chat = await engine.find_one(Chat, Chat.chat_name == chat_name)
    if existing_chat:
        return templates.TemplateResponse("begin_chat.html", {"request": request, "error": "Беседа с таким названием уже существует."})

    chat = Chat(chat_name=chat_name, messages=[])
    await engine.save(chat)

    return RedirectResponse(url=f"/chat/{chat_name}", status_code=303)

# Страница поиска бесед
@app.get("/chat_lookup", response_class=HTMLResponse)
async def find_chat_page(request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/log_in", status_code=302)

    chats = await engine.find(Chat)
    return templates.TemplateResponse("chat_lookup.html", {"request": request, "chats": chats})

# Обработка поиска бесед
@app.post("/chat_lookup", response_class=HTMLResponse)
async def find_chats(request: Request, query: str = Form(...)):
    if not request.session.get("user"):
        return RedirectResponse("/log_in", status_code=302)

    if len(query) < 6:
        return templates.TemplateResponse("chat_lookup.html", {"request": request, "error": "Запрос должен содержать минимум 6 символов."})

    chats = await engine.find(Chat, Chat.chat_name.match(query))
    return templates.TemplateResponse("chat_lookup.html", {"request": request, "chats": chats, "query": query})

# Удаление беседы
@app.post("/deletechat/{chat_name}")
async def delete_chat(chat_name: str, request: Request):
    if not request.session.get("user"):
        return RedirectResponse("/log_in", status_code=302)

    chat_to_delete = await engine.find_one(Chat, Chat.chat_name == chat_name)

    if chat_to_delete:
        await engine.delete(chat_to_delete)
        return RedirectResponse("/choose", status_code=303)
    else:
        return templates.TemplateResponse("talk.html", {"request": request, "error": "Беседа не найдена."})

# Страница беседы
@app.get("/chat/{chat_name}", response_class=HTMLResponse)
async def conversation_page(request: Request, chat_name: str):
    if not request.session.get("user"):
        return RedirectResponse("/log_in", status_code=302)
    user = request.session.get("user")
    token = create_access_token({"sub": user})
    return templates.TemplateResponse("talk.html", {"request": request, "chat_name": chat_name, "user": user, "token": token})

# Главная страница
@app.get("/", response_class=HTMLResponse)
async def index_page(request: Request):
    if request.session.get("user"):
        return templates.TemplateResponse("start_page.html", {"request": request, "user": request.session.get("user")})
    return templates.TemplateResponse("start_page.html", {"request": request})

# Страница регистрации
@app.get("/sign_up", response_class=HTMLResponse)
async def signup_page(request: Request):
    return templates.TemplateResponse("sign_up.html", {"request": request})

# Обработка формы регистрации
@app.post("/sign_up", response_class=HTMLResponse)
async def signup_user(request: Request, email: str = Form(...), password: str = Form(...)):
    existing_account = await engine.find_one(User, User.log_in == email)
    if existing_account:
        return templates.TemplateResponse("sign_up.html", {"request": request, "error": "Пользователь с таким email уже существует."})

    hashed_password = hash_password(password)
    user = User(log_in=email, hashed_password=hashed_password)
    await engine.save(user)

    request.session["user"] = user.log_in
    return RedirectResponse("/choose", status_code=302)
