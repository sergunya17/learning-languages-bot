from environs import Env
from time import sleep
from random import random, choice
import requests
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import CallbackContext
from googletrans import Translator


def translate_word(eng_word: str) -> str:
    for t in range(20):
        translator = Translator(service_urls=['translate.google.com'])
        try:
            ru_word = translator.translate(eng_word, src='en', dest='ru').text
            if eng_word == eng_word.lower():
                ru_word = ru_word.lower()
            return ru_word
        except Exception:
            sleep(5)

    return 'не найдено'

def get_random_word() -> str:
    env = Env()
    env.read_env()
    api_key = env.str('API_KEY')

    params = {'minCorpusCount': 5000, 'minDictionaryCount': 10, 'hasDictionaryDef': True, 'api_key': api_key,
              'excludePartOfSpeech': 'interjection,pronoun,preposition,abbreviation,affix,article,auxiliary-verb,'
                                     'conjunction,definite-article,family-name,given-name,noun-posessive,'
                                     'past-participle,phrasal-prefix,proper-noun,proper-noun-plural,'
                                     'proper-noun-posessive,suffix'}
    for t in range(20):
        try:
            response = requests.get('https://api.wordnik.com/v4/words.json/randomWord', params=params)
            response.raise_for_status()
            word = response.json().get('word')
            return word
        except requests.exceptions.HTTPError:
            sleep(5)

    return 'not found'


def send_word(context: CallbackContext):
    chat_id = context.job.context['chat_id']
    daily_num_of_words = context.dispatcher.chat_data[chat_id]['settings']['num_of_words']
    words = context.dispatcher.chat_data[chat_id]['words']

    unknown_word_prob = len(words['unknown']) / (len(words['unknown']) + daily_num_of_words)
    random_prob = random()
    if len(words['unknown']) > 3 * daily_num_of_words and random_prob < unknown_word_prob:
        all_unknown_words = list(words['unknown'].items())
        first_part_words = all_unknown_words[:daily_num_of_words]
        eng_word, ru_word = choice(first_part_words)
        words['unknown'].pop(eng_word, None)
    else:
        eng_word = get_random_word()
        while eng_word in words['sent'] or eng_word in words['known'] or eng_word in words['well-known']:
            eng_word = get_random_word()
        ru_word = translate_word(eng_word)

    words['sent'][eng_word] = ru_word

    message = f'ENG: {eng_word}\nRUS: {ru_word}'
    keyboard = [[InlineKeyboardButton('знаю', callback_data='known'),
                 InlineKeyboardButton('не знаю', callback_data='unknown')]]

    context.bot.send_message(chat_id, message, reply_markup=InlineKeyboardMarkup(keyboard))


def word_callback(update: Update, context: CallbackContext):
    update.callback_query.answer()

    message = update.effective_message.text
    eng_word, ru_word = [line.split(': ')[-1] for line in message.split('\n')]

    word_status = update.callback_query.data
    words = context.chat_data['words']
    words[word_status][eng_word] = ru_word
    words['sent'].pop(eng_word, None)

    new_message = message.replace('-', '\-')
    if word_status == 'known':
        new_message = f'~{new_message}~'

    update.callback_query.edit_message_text(new_message, parse_mode='MarkdownV2', reply_markup=None)

    return
