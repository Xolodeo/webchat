// Инициализация администратора в базе данных admin
db = db.getSiblingDB('admin');
db.createUser({
    user: 'admin',
    pwd: 'abdul',
    roles: [
        { role: 'root', db: 'admin' }
    ]
});

// Инициализация пользователя в базе данных users_db
db = db.getSiblingDB('users_db');
db.createUser({
    user: 'abdul',
    pwd: 'abdul',
    roles: [
        { role: 'readWrite', db: 'users_db' }
    ]
});
