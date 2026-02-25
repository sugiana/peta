import re
from sqlalchemy import engine_from_config
from sqlalchemy.orm import sessionmaker


def create_session(d: dict, prefix: str):
    engine = engine_from_config(d, prefix)
    factory = sessionmaker(bind=engine)
    return engine, factory()


def format_wilayah(name):
    words = name.split()
    formatted_words = []

    # Indonesian consonants and digraphs
    consonants = "bcdfghjklmnpqrstvwxyz"
    digraphs = ["ng", "ny", "sy", "kh"]

    for word in words:
        # Normalize for analysis
        clean_word = re.sub(r'[^a-zA-Z]', '', word).lower()

        # Check for 3 or more consecutive consonants
        # Treat digraphs as a single consonant unit
        temp = clean_word
        for d in digraphs:
            temp = temp.replace(d, 'Z')

        max_consecutive = 0
        current_consecutive = 0
        for char in temp:
            if char in consonants or char == 'Z':
                current_consecutive += 1
                max_consecutive = max(max_consecutive, current_consecutive)
            else:
                current_consecutive = 0

        if max_consecutive >= 3:
            formatted_words.append(word.upper())
        else:
            formatted_words.append(word.title())

    return " ".join(formatted_words)
