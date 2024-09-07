
from pdam_app.models import Sensor_data, Station, Threshold_data
from django.conf import settings as django_settings
import datetime
import telegram
import asyncio

def split_message(message, max_length=4096):
    return [message[i:i+max_length] for i in range(0, len(message), max_length)]

async def send_telegram_messages(bot, chat_id, messages):
    for msg in messages:
        await bot.send_message(chat_id=chat_id, text=msg, parse_mode='HTML')

def telegram_notif():
    stations = Station.objects.exclude(id__in=[61, 62, 63])
    powerSupplyNotif = []
    dataNotif = []
    thresholdNotif = []

    for station_data in stations:
        # Retrieve the last 12 records for the current station
        last_12_records = Sensor_data.objects.filter(station_id=station_data.id).order_by('-id')[:12]
        
        # Convert the queryset to a list and sort it by date_time in ascending order
        last_12_records_list = sorted(last_12_records, key=lambda x: x.date_time)
        
        if last_12_records_list:
            firstData = last_12_records_list[0]
            lastData = last_12_records_list[-1]

            hour = lastData.date_time.hour
            day = lastData.date_time.weekday()

            thData = Threshold_data.objects.filter(station_id=station_data.id,hour=hour,day=day).last()
            now = datetime.datetime.now() + datetime.timedelta(hours=12)
            if lastData is not None:
                # Check Battery
                if lastData.battery < 11.5:
                    powerSupplyNotif.append([station_data.station_name, lastData.battery])
                
                # Check Data
                if now - lastData.date_time > datetime.timedelta(minutes=37) or now - firstData.date_time > datetime.timedelta(minutes=92):
                    dataNotif.append([station_data.station_name, f"{firstData.date_time.strftime('%Y-%m-%d %H:%M:%S')} - {lastData.date_time.strftime('%Y-%m-%d %H:%M:%S')}"])
                
                # Threshold (Example logic, modify according to your needs)
                if thData is not None:
                    for allData in last_12_records_list:
                        if allData.modCH5 > thData.maximum or allData.modCH5 < thData.minimum:
                            thresholdNotif.append([station_data.station_name, f"{thData.minimum}-{thData.maximum}", allData.modCH5, allData.date_time])
        
    telegram_settings = django_settings.TELEGRAM
    bot = telegram.Bot(token=telegram_settings['bot_token'])

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        if powerSupplyNotif:
            message = "<b>PERINGATAN POWER SUPPLY!!!</b>\n"
            message += "<b>Daftar Station Power Supply Kurang dari 11.5 Volt</b>\n\n"
            for msgData in powerSupplyNotif:
                message += f" Stasiun: <b>{msgData[0]}</b>, Supply: <b>{msgData[1]}</b>\n"
                message += f" -----------------------------------------------\n\n"
            
            # print(message)
            messages = split_message(message)
            loop.run_until_complete(send_telegram_messages(bot, telegram_settings['channel_name'], messages))
        
        if dataNotif:
            message = "<b>PERINGATAN DATA BELUM MASUK!!!</b>\n"
            message += "<b>Daftar Station Data Belum Masuk ke Database</b>\n\n"
            for msgData in dataNotif:
                message += f" Stasiun: <b>{msgData[0]}</b>, Lokasi Data: <b>{msgData[1]}</b>\n"
                message += f" -----------------------------------------------\n\n"

            # print(message)
            messages = split_message(message)
            loop.run_until_complete(send_telegram_messages(bot, telegram_settings['channel_name'], messages))

        if thresholdNotif:
            message = "<b>PERINGATAN THRESHOLD!!!</b>\n"
            message += "<b>Daftar Station Diluar Threshold</b>\n\n"
            for msgData in thresholdNotif:
                message += f" Stasiun: <b>{msgData[0]}</b>, Threshold: <b>{msgData[1]} L/s</b>\n"
                message += f" Nilai Debit: <b>{msgData[2]} L/s</b>, Waktu: <b>{msgData[3]}</b>\n"
                message += f" -----------------------------------------------\n\n"

            # print(message)
            messages = split_message(message)
            loop.run_until_complete(send_telegram_messages(bot, telegram_settings['channel_name'], messages))
    
    finally:
        loop.close()