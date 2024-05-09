"""
Various utility functions for string manipulation.

"""


def generate_trigrams(word):
    return [word[i : i + 3] for i in range(len(word) - 2)]


def share_tri_gram(str1, str2):
    tri_grams1 = set(generate_trigrams(str1))
    tri_grams2 = set(generate_trigrams(str2))

    return bool(tri_grams1.intersection(tri_grams2))
