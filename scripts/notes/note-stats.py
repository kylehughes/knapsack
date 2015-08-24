#!/usr/bin/env python

import glob

countLetters = 0
countNotes = 0
countWords = 0

notesPath = "/Users/kylehugh/Library/Application Support/Notational Data/*"
notesList = glob.glob(notesPath)
countNotes = len(notesList)

for note in notesList:
    noteFile = open(note)

    noteWords = noteFile.read().split() 
    countWords += len(noteWords)

    for word in noteWords:
        countLetters += len(word)

print "---- Notes Statistics ----"
print "Notes:\t%d" % countNotes
print "Words:\t%d" % countWords
print "Chars:\t%d" % countLetters
