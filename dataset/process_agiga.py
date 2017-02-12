#
#  Copyright (c) 2015, Facebook, Inc.
#  All rights reserved.
#
#  This source code is licensed under the BSD-style license found in the
#  LICENSE file in the root directory of this source tree. An additional grant
#  of patent rights can be found in the PATENTS file in the same directory.
#
#  Author: Alexander M Rush <srush@seas.harvard.edu>
#          Sumit Chopra <spchopra@fb.com>
#          Jason Weston <jase@fb.com>

#/usr/bin/env python

import sys
import os
import re
import gzip
from bs4 import BeautifulSoup
from nltk import Tree
from collections import Counter
from pdb import set_trace as bp
#@lint-avoid-python-3-compatibility-imports

# Make directory for output if it doesn't exist

try:
    os.mkdir(sys.argv[2] + "/" + sys.argv[1].split("/")[-2])
except OSError:
    pass

# Strip off .gz ending
end = "/".join(sys.argv[1].split("/")[-2:])[:-len(".xml.gz")] + ".txt"

out = open(sys.argv[2] + end, "w")

# Parse and print titles and articles
NONE, HEAD, NEXT, TEXT, SENT = 0, 1, 2, 3, 4
MODE = NONE
title_parse = ""
headline = ""
article_parse = []
words = []
lemmas = []
ners = []
num_sent = 0

# FIX: Some parses are mis-parenthesized.
def fix_paren(parse):
    if len(parse) < 2:
        return parse
    if parse[0] == "(" and parse[1] == " ":
        return parse[2:-1]
    return parse

def get_words(parse):
    words = []
    for w in parse.split():
        if w[-1] == ')':
            words.append(w.strip(")"))
            if words[-1] == ".":
                break
    return words

def remove_digits(parse):
    return re.sub(r'\d', '#', parse)

def add_ner_order(ners):
    c = Counter()
    prev_n = ""
    for idx in range(len(ners)):
        n = ners[idx][:4]

        if prev_n == n:
            ners[idx] = "%s_%d" % (prev_n, c[prev_n])
        else:
            ners[idx] = "%s_%d" % (n, c[n])
            c[prev_n] += 1
        prev_n = n
    return ners

def replace_headline(headline, words, ners):
    ret_hl = []
    for h in headline:
        if h in words:
            idx = words.index(h)
            if ners[idx][:1] != "O":
                ret_hl.append(ners[idx])
                continue
        ret_hl.append(h)
    return ret_hl

def replace_lemma(lemmas, ners):
    for idx in range(len(ners)):
        if ners[idx][:1] != "O":
            lemmas[idx] = ners[idx]
    return lemmas

tags = ['MISC', 'LOCA', 'PERS', 'DATA', 'ORGA', 'MONE', 'PERC', 'TIME']

def trim(target):
    prev_t = ""
    ret = []
    for t in target:
        if t == prev_t and t[:4] in tags:
            continue
        else:
            ret.append(t)
        prev_t = t
    return ret

with gzip.open(sys.argv[1]) as f:
    while 1:
        line = f.readline()
        if not line:
            break
        line = line.strip()

        if MODE == HEAD:
            hl = remove_digits(fix_paren(line))
            headline = Tree.fromstring(hl).leaves()
            MODE = NEXT

        if MODE == TEXT:
            article_parse.append(remove_digits(fix_paren(line)))

        if MODE == SENT and re.match(r'<token id=\"[\d]+\">', line):
            words.append(f.readline().strip().replace("<word>", "").replace("</word>", ""))
            lemmas.append(f.readline().strip().replace("<lemma>", "").replace("</lemma>", ""))
            for _ in range(3):
                f.readline()
            ners.append(f.readline().strip().replace("<NER>", "").replace("</NER>", ""))

        if MODE == NONE and line == "<HEADLINE>":
            MODE = HEAD

        if MODE == NEXT and len(article_parse) == 0 and line == "<P>":
            MODE = TEXT

        if MODE == TEXT and line == "</P>":
            MODE = NEXT
            
        #if re.match(r'<sentence id=\"\d\">', line):
        #if re.match(r'<token id=\"\d\">', line):
            #print("123")

        if MODE == NEXT and re.match(r'<sentence id=\"[\d]+\">', line):
            if len(article_parse) > num_sent:
                MODE = SENT
                num_sent += 1
            else:
                MODE = NEXT

        if MODE == SENT and line == "</sentence>":
            MODE = NEXT

        if MODE == NEXT and len(article_parse) != 0 and len(article_parse) == num_sent:
            assert(len(lemmas) == len(words))
            assert(len(ners) == len(words))

            ners = add_ner_order(ners)
            title_parse = trim(replace_headline(headline, words, ners))
            article_parse = trim(replace_lemma(lemmas, ners))
            print >>out, "\t".join([" ".join(title_parse), " ".join(article_parse)])
            
            words = []
            lemmas = []
            ners = []
            article_parse = []
            num_sent = 0
            MODE = NONE
