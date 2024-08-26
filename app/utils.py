from praatio import textgrid

from collections import defaultdict


def get_word2phones_from_textgrid(file_path):
    tg = textgrid.openTextgrid(file_path, includeEmptyIntervals=False)

    # TODO: ask a user for a tier name?
    word_tier = tg.getTier('words')
    phone_tier = tg.getTier('phones')

    word2phones = defaultdict(list)
    phone_entries = phone_tier.entries
    start = 0
    for entry in word_tier:
        word = entry.label
        word_end = entry.end
        phones = []
        curr_phone = phone_entries[start]
        while curr_phone.end < word_end and start < len(phone_entries):
            curr_phone = phone_entries[start]
            phones.append(curr_phone.label)
            start += 1
        joined_phones = ''.join(phones)
        if joined_phones not in word2phones[word]:
            word2phones[word].append(joined_phones)
    return word2phones
