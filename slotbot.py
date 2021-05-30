import logging
import json
import requests
from datetime import date
from telegram import (
    ReplyKeyboardMarkup, 
    ReplyKeyboardRemove, 
    Update
    )
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    Filters,
    ConversationHandler,
    CallbackContext,
    JobQueue
)

headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/56.0.2924.76 Safari/537.36'}

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

updater = Updater("1838631744:AAF4azB8XIU17Tsx40-0OjPPeQAPo_pbWMQ")

DISTRICT, AGE, JOB = range(3)
state_dictionary = {}
district_dictionary = {}

class User:
    name = None
    age = None
    district = None

def start(update: Update, context: CallbackContext) -> int:
    update.message.reply_text("This bot is to get alerts when vaccine slots are available at location of your choice. Please select/enter state-district-age.")
    states = json.loads(requests.get("https://cdn-api.co-vin.in/api/v2/admin/location/states", headers=headers).text)['states']
    states_name = [ state['state_name'] for state in states ]
    for state in states:
        state_dictionary[state['state_name']]=state['state_id']
    update.message.reply_text('Select State',reply_markup=ReplyKeyboardMarkup(getKeyboardButtons(states_name), one_time_keyboard=True))
    return DISTRICT

def district(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    chosen_state = update.message.text.strip()
    districts = json.loads(requests.get("https://cdn-api.co-vin.in/api/v2/admin/location/districts/"+str(state_dictionary[chosen_state]), headers=headers).text)['districts']
    district_name = [ district['district_name'] for district in districts ]
    for district in districts:
        district_dictionary[district['district_name']]=district['district_id']
    update.message.reply_text('Select district',reply_markup=ReplyKeyboardMarkup(getKeyboardButtons(district_name), one_time_keyboard=True))
    return AGE


def age(update: Update, context: CallbackContext) -> int:
    User.district = update.message.text.strip()
    update.message.reply_text('Vaccine slots are available only for age group of 18+ as of now. Is your age 45+? select or enter yes/no',reply_markup=ReplyKeyboardMarkup([['yes','no']], one_time_keyboard=True))
    return JOB

def scheduleJob(update: Update, context: CallbackContext):
    user = update.message.from_user
    logger.info("User %s has requested alerts for district - %s.", user.first_name, User.district);
    #User.age = update.message.text.strip() TODO: add check for Age
    context.job_queue.run_repeating(callback_alarm, 60, context=update.message.chat_id)

def callback_alarm(context: CallbackContext):
    centers = json.loads(requests.get("https://cdn-api.co-vin.in/api/v2/appointment/sessions/public/calendarByDistrict?district_id=" + str(district_dictionary[User.district]) + "&date=" + date.today().strftime("%d-%m-%Y"), headers=headers).text)['centers']
    centers_having_vaccine = []
    for center in centers:
        for session in center['sessions']:
            if(session['available_capacity']>0):
                center_detail = {}
                center_detail['Name'] = center['name']
                center_detail['Pincode'] = center['pincode']
                center_detail['date'] = session['date']
                center_detail['Fee'] = center['fee_type']
                center_detail['Vaccine'] = session['vaccine']
                context.bot.send_message(chat_id=context.job.context, text=str(centers_having_vaccine))
                centers_having_vaccine.append(center_detail) 
    if len(centers_having_vaccine)>0:
        context.bot.send_message(chat_id=context.job.context, text='enter /cancel to stop receiving alerts')

def cancel(update: Update, context: CallbackContext) -> int:
    user = update.message.from_user
    logger.info("User %s canceled the conversation.", user.first_name)
    update.message.reply_text('Stay Healthy! Stay Safe!', reply_markup=ReplyKeyboardRemove())
    context.job_queue.stop()
    return ConversationHandler.END

def getKeyboardButtons(location_names):
    i=0
    reply_keyboard=[]
    while i < len(location_names):
        if (i+3)<len(location_names):
            reply_keyboard.append(location_names[i:(i+3)])
        else:
            reply_keyboard.append(location_names[i:])
        i+=3
    return reply_keyboard

def main() -> None:
    dispatcher = updater.dispatcher
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            DISTRICT: [MessageHandler(Filters.text & ~Filters.command, district)],
            AGE: [MessageHandler(Filters.text & ~Filters.command, age)],
            JOB: [MessageHandler(Filters.text & ~Filters.command, scheduleJob)]
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    dispatcher.add_handler(conv_handler)
    updater.start_polling()
    updater.idle()


if __name__ == '__main__':
    main()
