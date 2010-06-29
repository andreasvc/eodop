#!/bin/sh
python split.py
python morph.py
#fix lexicon
sh dotest.sh
sh doeval.sh
