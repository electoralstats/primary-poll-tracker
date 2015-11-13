#!/usr/bin/python2
from pollster import Pollster
import sqlite3
import sys
import datetime
import csv
conn = sqlite3.connect('Polls.db', detect_types=sqlite3.PARSE_DECLTYPES)
normalColumns = ['Pollster', 'StartDate', 'EndDate', 'Partisan', 'Affiliation', 'Method', 'Sample', 'SampleType']

def updateTableStructure():
    #This method can be called to update the structure of the SQLite database for the DemPrimary and RepubPrimary
    cursor = conn.cursor()
    #First we make sure that the base tables are created, with all the essential columns, for both parties
    try:
        cursor.execute("CREATE TABLE DemPrimary (Pollster varchar(255), StartDate date, EndDate date, Partisan varchar(255), Affiliation varchar(255), Method varchar(255), Sample int, SampleType varchar(255));")
    except sqlite3.Error as err:
        #If the error is as below, this means that the table already exists, which is fine, just move on. Otherwise, quit the program and display the error.
        if str(err) == 'table DemPrimary already exists':
            pass
        else:
            return err
            sys.exit()
    try:
        cursor.execute("CREATE TABLE RepubPrimary (Pollster varchar(255), StartDate date, EndDate date, Partisan varchar(255), Affiliation varchar(255), Method varchar(255), Sample int, SampleType varchar(255));")
    except sqlite3.Error as err:
        if str(err) == 'table RepubPrimary already exists':
            pass
        else:
            print err
            sys.exit()
    conn.commit()
    #Here, we get a list of the Democratic candidates from a text file called 'dem-candidates.txt'
    demCandidates = [x.replace("\n", "") for x in open('dem-candidates.txt').readlines()]
    cursor.execute("PRAGMA table_info(DemPrimary)")
    #Now we get the names of all columns currently in the table
    demColumns = [x[1] for x in cursor.fetchall()]
    for d in demCandidates:
        #We check to see if the candidate does not have a column, and if this is the case, we make one.
        if d not in demColumns:
            cursor.execute("ALTER TABLE DemPrimary ADD `%(cand)s` float;" %{"cand":d})
    for d2 in demColumns:
        #Here we are removing any candidates that we are no longer tracking (ie any candidate that has dropped out or announced they will not run)
        if d2 not in normalColumns and d2 not in demCandidates:
            cursor.execute("ALTER TABLE DemPrimary DROP `%(cand)s`;" %{"cand":d2})
    #Follow the same procedure as above, but for the republican candidates
    repubCandidates = [x.replace("\n", "") for x in open('repub-candidates.txt').readlines()]
    cursor.execute("PRAGMA table_info(RepubPrimary)")
    repubColumns = [x[1] for x in cursor.fetchall()]
    for r in repubCandidates:
        if r not in repubColumns:
            cursor.execute("ALTER TABLE RepubPrimary ADD `%(cand)s` float;" %{"cand":r})
    for r2 in repubColumns:
        if r2 not in normalColumns and r2 not in repubCandidates:
            cursor.execute("ALTER TABLE RepubPrimary DROP `%(cand)s`;" %{"cand":r2})
    conn.commit()
    #Finally, we return the list of candidates for each party so that when we fetch the polls, we know which candidates we are concerned with.
    return demCandidates, repubCandidates


def fetchPolls():
    #This function will fetch all new polls from Pollster and injects them into the SQLite database
    #First, we call updateTableStructure() to make sure that the SQLite table has the right structure and so we can get the list of candidates that we are concerned with
    dems, repubs = updateTableStructure()
    demString = str(dems).replace('[', '').replace(']', '').replace('\'', '`').replace('"', '`').replace('O`M', 'O\'M')
    repubString = str(repubs).replace('[', '').replace(']', '').replace('\'', '`').replace('"', '`')
    #Now we initialize everything for the SQLite database
    cursor = conn.cursor()
    #Now we initialize the pollster object
    pollster = Pollster()
    #Now we query the DemPrimary table to find the most recent poll that was inserted
    cursor.execute("SELECT EndDate FROM DemPrimary ORDER BY EndDate DESC;")
    testDemDates = cursor.fetchall()
    if testDemDates:
        #We need to make sure that there testDemDates has some entry, otherwise that means absolutely no polls have been injected, so we set the date to 2012-11-06, the day of the 2012 presidential election
        latestDemDate = testDemDates[0][0] + datetime.timedelta(1)
    else:
        latestDemDate = datetime.date(2012, 11, 06)
    #The next step is to get all the new polls. In order to do this, we need to first get the first page of polls and then every subsequent page of polls after.
    demPolls = []
    newDemPolls = pollster.polls(chart = '2016-national-democratic-primary', page=1, after=str(latestDemDate))
    i = 2
    while newDemPolls:
        demPolls.extend(newDemPolls)
        newDemPolls = pollster.polls(chart = '2016-national-democratic-primary', page=i, after=str(latestDemDate))
        i += 1
    #Now we loop through every poll and inject it into the database.
    for p in demPolls:
        #pollProps are true of all subpopulations
        pollProps = [str(p.pollster), str(p.start_date), str(p.end_date), str(p.partisan), str(p.affiliation), str(p.method)]
        relevantQuestion = [x for x in p.questions if x['topic'] == '2016-president-dem-primary'][0]
        #Loop through subpopulations and inject each separately (treat each as its own poll)
        for s in relevantQuestion['subpopulations']:
            values = pollProps + [s['observations'] if s['observations'] else 0, str(s['name'])]
            resp = s['responses']
            for c in dems:
                relevantResp = [x for x in resp if x['last_name']==c]
                val = relevantResp[0]['value'] if relevantResp else 0
                values.append(val)
            cursor.execute("INSERT INTO DemPrimary (Pollster, StartDate, EndDate, Partisan, Affiliation, Method, Sample, SampleType, %(cands)s) VALUES (%(val)s);" %{"val": str(values).replace('[', '').replace(']', ''), "cands":demString})
    #We now follow the same process for the Republicans
    cursor.execute("SELECT EndDate FROM RepubPrimary ORDER BY EndDate DESC;")
    testRepubDates = cursor.fetchall()
    if testRepubDates:
        latestRepubDate = testRepubDates[0][0] + datetime.timedelta(1)
    else:
        latestRepubDate = datetime.date(2012, 11, 06)
    repubPolls = []
    newRepubPolls = pollster.polls(chart = '2016-national-gop-primary', page=1, after=str(latestRepubDate))
    i = 2
    while newRepubPolls:
        repubPolls.extend(newRepubPolls)
        newRepubPolls = pollster.polls(chart = '2016-national-gop-primary', page=i, after=str(latestRepubDate))
        i += 1
    for p in repubPolls:
        pollProps = [str(p.pollster), str(p.start_date), str(p.end_date), str(p.partisan), str(p.affiliation), str(p.method)]
        relevantQuestion = [x for x in p.questions if x['topic'] == '2016-president-gop-primary'][0]
        for s in relevantQuestion['subpopulations']:
            values = pollProps + [s['observations'] if s['observations'] else 0, str(s['name'])]
            resp = s['responses']
            for c in repubs:
                relevantResp = [x for x in resp if x['last_name']==c]
                val = relevantResp[0]['value'] if relevantResp else 0
                values.append(val)
            cursor.execute("INSERT INTO RepubPrimary (Pollster, StartDate, EndDate, Partisan, Affiliation, Method, Sample, SampleType, %(cands)s) VALUES (%(val)s);" %{"val": str(values).replace('[', '').replace(']', ''), "cands":repubString})
    conn.commit()
    return dems, repubs
    
