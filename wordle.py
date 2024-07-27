#!/usr/bin/python
from functools import partial
import math
import os
import itertools
import random
import pickle
import multiprocessing
from tqdm import tqdm
from scipy.stats import entropy
from collections import defaultdict, Counter

N_GUESSES = 10
DICT_FILE_available = 'all_words.txt'
DICT_FILE_answer = 'words.txt'
SAVE_TIME = False

def calculate_pattern(guess, true):
    """Generate a pattern list that Wordle would return if you guessed
    `guess` and the true word is `true`
    Thanks to MarkCBell, Jeroen van der Hooft and gbotev1
    >>> calculate_pattern('weary', 'crane')
    (0, 1, 2, 1, 0)
    >>> calculate_pattern('meets', 'weary')
    (0, 2, 0, 0, 0)
    >>> calculate_pattern('rower', 'goner')
    (0, 2, 0, 2, 2)
    """
    wrong = [i for i, v in enumerate(guess) if v != true[i]]
    counts = Counter(true[i] for i in wrong)
    pattern = [2] * 5
    for i in wrong:
        v = guess[i]
        if counts[v] > 0:
            pattern[i] = 1
            counts[v] -= 1
        else:
            pattern[i] = 0
    return tuple(pattern)


def generate_sub_pattern_dict(dictionary_all, dic):
    pattern_dict = defaultdict(lambda: defaultdict(set))
    dictionary = dic["d"]
    id = dic["i"]

    for word in tqdm(dictionary, desc=f"worker {id}"):
        for word2 in dictionary_all:
            pattern = calculate_pattern(word, word2)
            pattern_dict[word][pattern].add(word2)

    return dict(pattern_dict)

def generate_pattern_dict(dictionary):
    """For each word and possible information returned, store a list
    of candidate words
    >>> pattern_dict = generate_pattern_dict(['weary', 'bears', 'crane'])
    >>> pattern_dict['crane'][(2, 2, 2, 2, 2)]
    {'crane'}
    >>> sorted(pattern_dict['crane'][(0, 1, 2, 0, 1)])
    ['bears', 'weary']
    """
    print("Generating pattern dict...")
    pattern_dict = defaultdict(lambda: defaultdict(set))
    pool = multiprocessing.Pool()
    process_num = multiprocessing.cpu_count()
    g_func = partial(generate_sub_pattern_dict, dictionary)
    sub_l = []

    for i in range(process_num):
        l = math.floor(i / process_num * len(dictionary))
        r = math.floor((i + 1) / process_num * len(dictionary))
        sub_l.append({
            "d": dictionary[l : r],
            "i": i
        })

    results = pool.map(g_func, sub_l)
    pool.close()
    pool.join()

    for i in results:
        pattern_dict.update(i)

    return dict(pattern_dict)

    # for word in tqdm(dictionary):
    #     for word2 in dictionary:
    #         pattern = calculate_pattern(word, word2)
    #         pattern_dict[word][pattern].add(word2)
    # return dict(pattern_dict)


def calculate_entropies(words, possible_words, pattern_dict, all_patterns):
    """Calculate the entropy for every word in `words`, taking into account
    the remaining `possible_words`"""
    print("Calculating entropies...")
    entropies = {}
    for word in tqdm(words):
        counts = []
        for pattern in all_patterns:
            matches = pattern_dict[word][pattern]
            matches = matches.intersection(possible_words)
            counts.append(len(matches))
        entropies[word] = entropy(counts)
    return entropies

def print_cdds(cdds):
    print("*---*")
    for cdd in cdds:
        print(cdd[0] + " " + str(cdd[1]))
    print("*---*")

def main():
    ## init
    # load all 5-letter-words for making patterns 
    with open(DICT_FILE_available) as ifp:
        all_dictionary = list(map(lambda x: x.strip(), ifp.readlines()))

    # Load 2315 words for solutions
    with open(DICT_FILE_answer) as ifp:
        dictionary = list(map(lambda x: x.strip(), ifp.readlines()))

    error_msg = 'Dictionary contains different length words.'
    assert len({len(x) for x in all_dictionary}) == 1, error_msg
    print(f'Loaded dictionary with {len(all_dictionary)} words...')
    WORD_LEN = len(all_dictionary[0]) # 5-letters 

    # Generate the possible patterns of information we can get
    all_patterns = list(itertools.product([0, 1, 2], repeat=WORD_LEN))

    # Calculate the pattern_dict and cache it, or load the cache.
    if 'pattern_dict.p' in os.listdir('.'):
        pattern_dict = pickle.load(open('pattern_dict.p', 'rb'))
    else:
        pattern_dict = generate_pattern_dict(all_dictionary)
        pickle.dump(pattern_dict, open('pattern_dict.p', 'wb+'))

    ##--##

    ## main loop

    init_flag = False
    input_c = ""
    available_words = set()
    candidates = []
    while True:
        if init_flag:
            input_c = input()
            if input_c == "exit":
                break

            input_sp = input_c.split()
            if (len(input_sp) != 2) or (not input_sp[0] in available_words) or (len(input_sp[1]) != 5):
                print("Bad input")
                continue

            p_l = []
            bad_flag = False
            for c in input_sp[1]:
                if int(c) < 0 or int(c) > 2:
                    print("Bad input")
                    bad_flag = True
                    break
                p_l.append(int(c))
            if bad_flag:
                continue
                
            pattern = tuple(p_l)
            available_words = available_words.intersection(pattern_dict[input_sp[0]][pattern])
            if len(available_words) < 100:
                candidates = available_words.intersection(dictionary)
            else:
                candidates = available_words
            candidates = available_words
        else:
            init_flag = True
            available_words = set(all_dictionary)
            candidates = all_dictionary

        entropies = calculate_entropies(candidates, available_words, pattern_dict, all_patterns)
        top_10_cdds = sorted(entropies.items(), key=lambda x: x[1], reverse=True)[:10]
        print_cdds(top_10_cdds)

if __name__ == "__main__":
    main()
