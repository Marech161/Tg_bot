import logging
import subprocess
import os
import re
import paramiko
import psycopg2
from psycopg2 import Error
from dotenv import load_dotenv
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, ConversationHandler

load_dotenv()
pg_host = os.getenv('DB_HOST')
pg_port = os.getenv('DB_PORT')
pg_user = os.getenv('DB_USER')
pg_password = os.getenv('DB_PASSWORD')
pg_database = os.getenv('DB_DATABASE')
TOKEN = os.getenv('TOKEN')
ssh_host = os.getenv('RM_HOST')
ssh_port = os.getenv('RM_PORT')
ssh_username = os.getenv('RM_USER')
ssh_password = os.getenv('RM_PASSWORD')


logging.basicConfig(
    filename='logfile.txt', format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO
)

logger = logging.getLogger(__name__)

def connect_database():
    try:
        pg_connection = psycopg2.connect(user=pg_user,
                                         password=pg_password,
                                         host=pg_host,
                                         port=pg_port,
                                         database=pg_database)

        logging.info("Connect to database")
        return pg_connection
    except (Exception, Error) as error:
        logging.error("Ошибка при работе с PostgreSQL: %s", error)


def ssh_connect():
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    client.connect(hostname=ssh_host, username=ssh_username, password=ssh_password, port=ssh_port)
    return client

def get_repl_logs(update: Update, context):
    result = subprocess.run(
        "cat /var/log/postgresql/*.log | grep 'replica'",
        shell=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )

    if result.returncode != 0:
        print(f"Ошибка при выполнении команды: {result.stderr}")
    else:
        update.message.reply_text(result.stdout)

def get_emails(update: Update, context):
    pg_connection = connect_database()
    cursor = pg_connection.cursor()
    cursor.execute("SELECT * FROM Emails;")
    data = cursor.fetchall()
    cursor.close()
    pg_connection.close()
    formatted_data = "\n".join([f"№ {item[0]}, Email: {item[1]}" for item in data])
    update.message.reply_text(formatted_data)


def get_phone_numbers(update: Update, context):
    pg_connection = connect_database()
    cursor = pg_connection.cursor()
    cursor.execute("SELECT * FROM Phones;")
    data = cursor.fetchall()
    cursor.close()
    pg_connection.close()
    formatted_data = "\n".join([f"№ {item[0]}, Phone: {item[1]}" for item in data])
    update.message.reply_text(formatted_data)

def find_phone_number_command(update: Update, context):
    update.message.reply_text('Введите текст для поиска телефонных номеров: ')

    return 'find_phone_number'


def find_phone_number(update: Update, context):
    user_input = update.message.text

    phone_num_regex = re.compile(r'(\+7|8)[\s-]?\(?(\d{3})\)?[\s-]?(\d{3})[\s-]?(\d{2})[\s-]?(\d{2})')

    phone_number_list = phone_num_regex.findall(user_input)

    if not phone_number_list:
        update.message.reply_text('Телефонные номера не найдены')
        return

    context.user_data['phone_numbers'] = phone_number_list
    phone_text = ''
    for i, phone in enumerate(phone_number_list, start=1):
        full_number = ''.join(phone).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
        phone_text += f"Номер {i}: {full_number}\n"
    phone_text += "Записать найденные номера в БД? (Y/N)"
    update.message.reply_text(phone_text)
    return 'confirm_add_phone_number'


def confirm_add_phone_number(update: Update, context):
    user_response = update.message.text.lower()

    if user_response == 'y':
        phone_numbers = context.user_data.get('phone_numbers')
        pg_connection = connect_database()
        cursor = pg_connection.cursor()

        try:
            cursor.execute("BEGIN;")
            for phone in phone_numbers:
                full_number = ''.join(phone).replace(' ', '').replace('-', '').replace('(', '').replace(')', '')
                cursor.execute(f"SELECT * FROM Phones WHERE value = {full_number}")
                exists = cursor.fetchone()[0]
                if not exists:
                    cursor.execute(f"INSERT INTO Phones (value) VALUES ('{full_number}');")
            cursor.execute("COMMIT;")
            pg_connection.commit()
            cursor.close()
            pg_connection.close()
            update.message.reply_text("Номера телефонов добавлены в БД.")
        except Exception as e:
            cursor.execute("ROLLBACK;")
            cursor.close()
            pg_connection.close()
            update.message.reply_text(f"Номера не добавлены в БД: {e}")
    elif user_response == 'n':
        update.message.reply_text("Номера не будут добавлены в БД.")
    else:
        update.message.reply_text("Повторите команду еще раз, введя верные данные (Y/N)")

    return ConversationHandler.END


def find_email_command(update: Update, context):
    update.message.reply_text('Введите текст для поиска email: ')
    return 'find_email'


def find_email(update: Update, context):
    user_input = update.message.text

    email_regex = re.compile(
        r"\b[a-zA-Z0-9]+@[a-zA-Z0-9-]+\.[a-zA-Z]{2,}\b")

    email_list = email_regex.findall(user_input)

    if not email_list:
        update.message.reply_text('Email не найдены')
        return

    context.user_data['emails'] = email_list
    emails = ''
    for i, email in enumerate(email_list, start=1):
        emails += f'{i}. {email}\n'

    emails += "Записать найденные Emails в БД? (Y/N)"
    update.message.reply_text(emails)
    return 'confirm_add_emails'


def confirm_add_emails(update: Update, context):
    user_response = update.message.text.lower()
    # user_response = update.message.text.lower()

    if user_response == 'y':
        emails = context.user_data.get('emails')
        pg_connection = connect_database()
        cursor = pg_connection.cursor()

        try:
            cursor.execute("BEGIN;")
            for email in emails:
                cursor.execute(f"SELECT * FROM Emails WHERE value = '{email}'")
               # exists = cursor.fetchone()
               # update.message.reply_text(exists)
                cursor.execute(f"INSERT INTO Emails (value) VALUES ('{email}');")
            cursor.execute("COMMIT;")
            pg_connection.commit()
            cursor.close()
            pg_connection.close()
            update.message.reply_text("Email добавлены в БД.")
        except Exception as e:
            cursor.execute("ROLLBACK;")
            cursor.close()
            pg_connection.close()
            update.message.reply_text(f"Email не добавлены в БД: {e}")
    elif user_response == 'n':
        update.message.reply_text("Email не будут добавлены в БД.")
    else:
        update.message.reply_text("Повторите команду еще раз, введя верные данные (Y/N)")

    return ConversationHandler.END


def verify_password_command(update: Update, context):
    update.message.reply_text('Введите пароль для проверки: ')
    return 'verify_password'


def verify_password(update: Update, context):
    user_input = update.message.text

    pass_regex = re.compile(
        r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[!@#$%^&*()])[A-Za-z\d!@#$%^&*()]{8,}$")

    pass_list = pass_regex.search(user_input)

    if not pass_list:
        update.message.reply_text('Пароль простой')
        return

    else:
        update.message.reply_text("Пароль сложный")
    return ConversationHandler.END


def get_release(update: Update, context):
    client = ssh_connect()
    stdin, stdout, stderr = client.exec_command('lsb_release -a')
    data = stdout.read() + stderr.read()
    client.close()
    decoded_data = data.decode('utf-8')
    update.message.reply_text(f'Информация об архитектуре процессора, имени хоста системы и версии ядра:'
                              f'\n{decoded_data}')


def get_uname(update: Update, context):
    client = ssh_connect()
    stdin, stdout, stderr = client.exec_command('uname -mrs')
    data = stdout.read() + stderr.read()
    client.close()
    decoded_data = data.decode('utf-8')
    update.message.reply_text(f'Информация об архитектуре процессора, имени хоста системы и версии ядра:'
                              f'\n{decoded_data}')


def get_uptime(update: Update, context):
    client = ssh_connect()
    stdin, stdout, stderr = client.exec_command('uptime -p')
    data = stdout.read() + stderr.read()
    client.close()
    decoded_data = data.decode('utf-8')
    update.message.reply_text(f'Информация о времени работы:'
                              f'\n{decoded_data}')


def get_df(update: Update, context):
    client = ssh_connect()
    stdin, stdout, stderr = client.exec_command('df -h')
    data = stdout.read() + stderr.read()
    client.close()
    decoded_data = data.decode('utf-8')
    update.message.reply_text(f'Информация о состоянии файловой системы:'
                              f'\n{decoded_data}')


def get_free(update: Update, context):
    client = ssh_connect()
    stdin, stdout, stderr = client.exec_command('free -h')
    data = stdout.read() + stderr.read()
    client.close()
    decoded_data = data.decode('utf-8')
    update.message.reply_text(f'Информация о состоянии оперативной памяти:'
                              f'\n{decoded_data}')


def get_mpstat(update: Update, context):
    client = ssh_connect()
    stdin, stdout, stderr = client.exec_command('mpstat')
    data = stdout.read() + stderr.read()
    client.close()
    decoded_data = data.decode('utf-8')
    update.message.reply_text(f'Информация о производительности системы:'
                              f'\n{decoded_data}')


def get_w(update: Update, context):
    client = ssh_connect()
    stdin, stdout, stderr = client.exec_command('w')
    data = stdout.read() + stderr.read()
    client.close()
    decoded_data = data.decode('utf-8')
    update.message.reply_text(f'Информация о работающих в данной системе пользователях:'
                              f'\n{decoded_data}')


def get_auths(update: Update, context):
    client = ssh_connect()
    stdin, stdout, stderr = client.exec_command('last -n 10')
    data = stdout.read() + stderr.read()
    client.close()
    decoded_data = data.decode('utf-8')
    update.message.reply_text(f'Последние 10 входов в систему:'
                              f'\n{decoded_data}')


def get_critical(update: Update, context):
    client = ssh_connect()
    stdin, stdout, stderr = client.exec_command("grep -i 'critical' /var/log/syslog | tail -n 5")
    data = stdout.read() + stderr.read()
    client.close()
    decoded_data = data.decode('utf-8')
    update.message.reply_text(f'Последние 5 критических событий:'
                              f'\n{decoded_data}')


def get_ps(update: Update, context):
    client = ssh_connect()
    stdin, stdout, stderr = client.exec_command("ps aux")
    data = stdout.read() + stderr.read()
    client.close()
    decode_data = data.decode('utf-8')
    with open('ps_list.txt', 'w') as f:
        f.write(decode_data)
    update.message.reply_document(document=open('ps_list.txt', 'rb'),
                                  caption='Список процессов')
    return ConversationHandler.END


def get_ss(update: Update, context):
    client = ssh_connect()
    stdin, stdout, stderr = client.exec_command("ss -tuln")
    data = stdout.read() + stderr.read()
    client.close()
    decoded_data = data.decode('utf-8')
    update.message.reply_text(f'Информация о об используемых портах:'
                              f'\n{decoded_data}')


def get_apt_list_command(update: Update, context):
    update.message.reply_text('Введите имя пакета, информацию о котором хотите получить информацию или введите all,'
                              'чтобы получить информацию о всех пакетах')
    return 'get_apt_list'


def get_apt_list(update: Update, context):
    user_input = update.message.text
    client = ssh_connect()

    if user_input == 'all':
        stdin, stdout, stderr = client.exec_command("apt list --installed")
        data = stdout.read() + stderr.read()
        client.close()
        decode_data = data.decode('utf-8')
        with open('apt_list.txt', 'w') as f:
            f.write(decode_data)
        update.message.reply_document(document=open('apt_list.txt', 'rb'),
                                      caption='Список установленных пакетов')
        return ConversationHandler.END
    else:
        stdin, stdout, stderr = client.exec_command(f"apt-cache show {user_input}")
        data = stdout.read() + stderr.read()
        client.close()
        decoded_data = data.decode('utf-8')
        update.message.reply_text(decoded_data)
        return ConversationHandler.END


def get_services(update: Update, context):
    client = ssh_connect()
    stdin, stdout, stderr = client.exec_command("systemctl list-units --type=service --state=running")
    data = stdout.read() + stderr.read()
    client.close()
    decoded_data = data.decode('utf-8')
    update.message.reply_text(f'Информация о о запущенных сервисах:'
                              f'\n{decoded_data}')


def main():
    updater = Updater(TOKEN, use_context=True)

    dp = updater.dispatcher

    conv_handler_find_phone_numbers = ConversationHandler(
        entry_points=[CommandHandler('find_phone_number', find_phone_number_command)],
        states={
            'find_phone_number': [MessageHandler(Filters.text & ~Filters.command, find_phone_number)],
            'confirm_add_phone_number': [MessageHandler(Filters.text & ~Filters.command, confirm_add_phone_number)]
        },
        fallbacks=[]
    )

    conv_handler_find_email = ConversationHandler(
        entry_points=[CommandHandler('find_email', find_email_command)],
        states={
            'find_email': [MessageHandler(Filters.text & ~Filters.command, find_email)],
            'confirm_add_emails': [MessageHandler(Filters.text & ~Filters.command, confirm_add_emails)],
        },
        fallbacks=[]
    )

    conv_handler_verify_password = ConversationHandler(
        entry_points=[CommandHandler('verify_password', verify_password_command)],
        states={
            'verify_password': [MessageHandler(Filters.text & ~Filters.command, verify_password)],
        },
        fallbacks=[]
    )

    conv_handler_get_apt_list = ConversationHandler(
        entry_points=[CommandHandler('get_apt_list', get_apt_list_command)],
        states={
            'get_apt_list': [MessageHandler(Filters.text & ~Filters.command, get_apt_list)],
        },
        fallbacks=[]
    )

    dp.add_handler(conv_handler_find_phone_numbers)
    dp.add_handler(conv_handler_find_email)
    dp.add_handler(conv_handler_verify_password)
    dp.add_handler(CommandHandler("get_release", get_release))
    dp.add_handler(CommandHandler("get_uname", get_uname))
    dp.add_handler(CommandHandler("get_uptime", get_uptime))
    dp.add_handler(CommandHandler("get_df", get_df))
    dp.add_handler(CommandHandler("get_free", get_free))
    dp.add_handler(CommandHandler("get_mpstat", get_mpstat))
    dp.add_handler(CommandHandler("get_w", get_w))
    dp.add_handler(CommandHandler("get_auths", get_auths))
    dp.add_handler(CommandHandler("get_critical", get_critical))
    dp.add_handler(CommandHandler("get_ps", get_ps))
    dp.add_handler(CommandHandler("get_ss", get_ss))
    dp.add_handler(conv_handler_get_apt_list)
    dp.add_handler(CommandHandler("get_services", get_services))
    dp.add_handler(CommandHandler("get_repl_logs", get_repl_logs))
    dp.add_handler(CommandHandler("get_emails", get_emails))
    dp.add_handler(CommandHandler("get_phone_numbers", get_phone_numbers))

    updater.start_polling()

    updater.idle()


if __name__ == '__main__':
    main()
