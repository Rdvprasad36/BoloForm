# -*- coding: utf-8 -*-
"""Telugu lexicon: number words, yes/no, voice commands, system messages.

ALL Telugu in this file is a DRAFT. Have a native speaker review it before the demo.
"""

TELUGU_DIGITS = {"౦": "0", "౧": "1", "౨": "2", "౩": "3", "౪": "4",
                 "౫": "5", "౬": "6", "౭": "7", "౮": "8", "౯": "9"}

UNITS = {
    "సున్నా": 0, "జీరో": 0, "zero": 0,
    "ఒకటి": 1, "ఒక్కటి": 1, "ఒక్క": 1, "ఒక": 1, "one": 1,
    "రెండు": 2, "two": 2,
    "మూడు": 3, "three": 3,
    "నాలుగు": 4, "four": 4,
    "ఐదు": 5, "అయిదు": 5, "five": 5,
    "ఆరు": 6, "six": 6,
    "ఏడు": 7, "seven": 7,
    "ఎనిమిది": 8, "eight": 8,
    "తొమ్మిది": 9, "nine": 9,
}
TEENS = {
    "పది": 10, "ten": 10, "పదకొండు": 11, "eleven": 11, "పన్నెండు": 12, "twelve": 12,
    "పదమూడు": 13, "thirteen": 13, "పద్నాలుగు": 14, "పధ్నాలుగు": 14, "fourteen": 14,
    "పదిహేను": 15, "fifteen": 15, "పదహారు": 16, "sixteen": 16, "పదిహేడు": 17,
    "seventeen": 17, "పద్దెనిమిది": 18, "eighteen": 18, "పంతొమ్మిది": 19, "nineteen": 19,
}
TENS = {
    "ఇరవై": 20, "twenty": 20, "ముప్పై": 30, "thirty": 30, "నలభై": 40, "forty": 40,
    "యాభై": 50, "fifty": 50, "అరవై": 60, "sixty": 60, "డెబ్బై": 70, "seventy": 70,
    "ఎనభై": 80, "eighty": 80, "తొంభై": 90, "ninety": 90,
}
HUNDRED = {"వంద", "వందలు", "వందల", "నూరు", "నూట", "hundred"}
THOUSAND = {"వెయ్యి", "వేలు", "వేల", "thousand"}

# "X and a half" forms used for land area (2.5 acres etc.)
HALF_FORMS = {
    "ఒకటిన్నర": 1.5, "రెండున్నర": 2.5, "మూడున్నర": 3.5, "నాలుగున్నర": 4.5,
    "ఐదున్నర": 5.5, "అయిదున్నర": 5.5, "ఆరున్నర": 6.5, "ఏడున్నర": 7.5,
    "ఎనిమిదిన్నర": 8.5, "తొమ్మిదిన్నర": 9.5, "పదిన్నర": 10.5,
    "అర": 0.5, "పావు": 0.25, "అరెకరం": 0.5,
}
POINT_WORDS = {"పాయింట్", "point"}
DOUBLE_WORDS = {"డబుల్", "double"}
TRIPLE_WORDS = {"ట్రిపుల్", "triple"}

YES = {"అవును", "ఔను", "అవునండి", "సరే", "సరైనదే", "సరైనది", "ఉంది", "ఉన్నది", "ఉన్నాయి",
       "yes", "yeah", "haan", "correct", "ok", "okay"}
NO = {"కాదు", "కాదండి", "లేదు", "లేదండి", "తప్పు", "వద్దు", "no", "nahi", "nope", "wrong"}

# Commands are matched as whole words / word sequences.
REPEAT = [["మళ్ళీ", "చెప్పండి"], ["మళ్లీ", "చెప్పండి"], ["మళ్ళీ"], ["మళ్లీ"],
          ["repeat"], ["again"], ["replay"]]
BACK = [["వెనక్కి"], ["వెనుకకు"], ["back"], ["previous"]]
SKIP = [["దాటవేయి"], ["దాటవేయండి"], ["స్కిప్"], ["skip"]]

# Words stripped from free-text answers (names, villages)
FILLERS = {"నా", "పేరు", "నేను", "అండి", "ఇది", "మా", "ఊరు", "ఊరి", "my", "name", "is", "i", "am",
           "from", "village", "the", "it", "its"}

# Unit words stripped from numeric answers
UNIT_WORDS = {"ఎకరాలు", "ఎకరం", "ఎకరా", "ఎకరాల", "acres", "acre", "సంవత్సరాలు", "సంవత్సరాల",
              "ఏళ్ళు", "ఏళ్లు", "years", "year", "old"}

# (telugu, english)
MSG = {
    "greeting": ("నమస్కారం! నేను మీ ఫారం నింపడంలో సహాయం చేస్తాను. మైక్ బటన్ నొక్కి చెప్పండి.",
                 "Hello! I will help fill your form. Tap the mic and speak."),
    "not_heard": ("క్షమించండి, నాకు వినిపించలేదు. మళ్ళీ చెప్పండి.",
                  "Sorry, I did not hear that. Please say it again."),
    "not_number": ("నాకు సంఖ్య అర్థం కాలేదు. మళ్ళీ చెప్పండి.",
                   "I did not understand the number. Please say it again."),
    "out_of_range": ("ఆ విలువ సరిగా లేదు. మళ్ళీ చెప్పండి.",
                     "That value is not valid. Please say it again."),
    "not_10_digits": ("ఫోన్ నంబర్ పది అంకెలు ఉండాలి. మళ్ళీ చెప్పండి.",
                      "A phone number must have ten digits. Please say it again."),
    "bad_start": ("ఫోన్ నంబర్ 6, 7, 8 లేదా 9 తో మొదలవ్వాలి. మళ్ళీ చెప్పండి.",
                  "A phone number must start with 6, 7, 8 or 9. Please say it again."),
    "no_match": ("నాకు అర్థం కాలేదు. మళ్ళీ చెప్పండి.", "I did not understand. Please say it again."),
    "empty": ("క్షమించండి, నాకు వినిపించలేదు. మళ్ళీ చెప్పండి.",
              "Sorry, I did not hear that. Please say it again."),
    "yes_no_unclear": ("అవును లేదా కాదు అని చెప్పండి.", "Please say yes or no."),
    "after_no": ("సరే, మళ్ళీ చెప్పండి.", "Okay, please say it again."),
    "fallback": ("వాయిస్ సరిగా పని చేయడం లేదు. దయచేసి టైప్ చేయండి.",
                 "Voice is not working well. Please type your answer."),
    "review": ("దయచేసి ఒకసారి చూసి సరిచూడండి.", "Please check your form once."),
    "done": ("మీ ఫారం సిద్ధంగా ఉంది.", "Your form is ready."),
    "confirm_q": ("సరైనదేనా?", "Is that correct?"),
    "skipped": ("సరే, దాటవేశాను.", "Okay, skipped."),
}

YES_TE, NO_TE = "అవును", "కాదు"
