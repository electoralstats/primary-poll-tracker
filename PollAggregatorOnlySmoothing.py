#!/usr/bin/python2
import PollFetcher
import sys
import KalmanFilter
import matplotlib
matplotlib.use('AGG')
import matplotlib.pyplot as plt
import numpy as np
import MySQLdb as mariadb
import datetime
import time
from statsmodels.nonparametric import smoothers_lowess as smooth
matplotlib.rcParams['font.family'] = ['Gentium Basic', 'Georgia', 'Times New Roman', 'Times', 'serif']
username = open('../.username').read().replace("\n", "")
passw = open('../.password').read().replace("\n", "")
dbName = open('../.database').read().replace("\n", "")
def smoothEstimates(points):
    #First we take the points that are passed and turn them into x and y
    [x, y] = points
    #Since our x's are dates, we turn them into Epoch timestamps
    x = [time.mktime(p.timetuple()) for p in x]
    y = [p/100.0 for p in y]
    #We want the lowess model to take into account the closest 10 points when smoothing, meaning we pass it frac.
    frac = 10.0/len(x)
    #We then pass the points to a lowess smoother, which considers frac% of points at a time.
    smoothed = smooth.lowess(y, x, frac=frac)
    #We change the epoch timestamps back into datetime objects and assign that to x
    x = [datetime.datetime.fromtimestamp(p[0]) for p in smoothed]
    #We then assign the smoothed estimates to y
    y = [p[1] for p in smoothed]
    #Now we recombine the x and y and pass it back as one list.
    smoothed = [x, y]
    return smoothed

def getEstimates():
    #This method goes through, grabs the polls and sends them through the Kalman fitler for each candidate and returns all the arrays of estimates as two dictionaries.
    #First, we initialize our MySQL connection
    mariadb_conn = mariadb.connect(user = username, passwd = passw, db = dbName)
    cursor = mariadb_conn.cursor()
    #Next, we make sure that our polls are all up-to-date, and this also gives us a list of candidates for each party
    dems, repubs = PollFetcher.fetchPolls()
    demEstimates = {}
    demUncertainties = {}
    for d in dems:
        #We go through every candidate and first get the poll results from the database
        cursor.execute("SELECT EndDate, `%(cand)s` FROM DemPrimary;" %{"cand":d})
        polls = cursor.fetchall()
        #Next we send these polls through the KalmanFilter to get the estimates
        x = [p[0] for p in polls]
        y = [p[1] for p in polls]
        polls = [x, y]
        demEstimates[d] = smoothEstimates(polls)
    #We now repeat the process for the Republicans
    repubEstimates = {}
    repubUncertainties = {}
    for r in repubs:
        cursor.execute("SELECT EndDate, `%(cand)s`, Sample FROM RepubPrimary;" %{"cand": r})
        polls = cursor.fetchall()
        x = [p[0] for p in polls]
        y = [p[1] for p in polls]
        polls = [x, y]
        repubEstimates[r] = smoothEstimates(polls)
    #We now return our estimates and uncertainties
    return demEstimates, repubEstimates

def plotEstimates():
    #First we call getEstimates() to get our estimates
    demE, repubE = getEstimates()
    #Set up the figure for the Democratic plot
    plt.figure(figsize=(25,15))
    ax = plt.axes()
    ax.set_color_cycle([(.79, 0, 0), (.45, 0, .79),  (.79, 0, .78), (0, .74, .79), (0, .79, .2), (0, .04, .79),  (1, .42, 0), (.91, .44, .54), (.96, .78, .07), (.29, .62, 1)])
    #Because Hillary Clinton is polling at or around 60%, we need the y range to be fairly big
    ax.set_ylim([0,.8])
    #demFinalEstimates will be made of the most recent estimate for each candidate, in the order that they are called
    demFinalEstimates = []
    #demLines will take the line object produced by PyPlot for each candidate, in the order they are called
    demLines = []
    #demLabels will take what we want the label of each line to be for each candidate, in the order that they are called
    demLabels = []
    #Because demE is a dictionary, each d in demE will be an index, i.e. a candidate name
    for d in demE:
        #First, we take the date of the most recent estimate and put it into endDate
        endDate = demE[d][0][len(demE[d][0])-1]
        #We want the plot only to show the last estimate and the 30 days before that, which gives us beginDate
        beginDate = endDate - datetime.timedelta(30)
        ax.set_xlim([beginDate, endDate])
        #demErr = smoothEstimates(demU[d])
        #demErr = [demErr[0], 1.96*np.sqrt(demErr[1])]
        #We pass our estimates to smoothEstimates to get back a lowess-smoothed version
        demSmooth = demE[d]
        print demSmooth
        #We now append the most recent estimate to demFinalestimates, taking the absolute value so it we don't get -0.0
        demFinalEstimates.append(abs(demSmooth[1][len(demSmooth[1])-1]))
        #We construct the label to look like "Candidate: x.x%" with the percent being the most recent estimate
        label = d + ": " + "{:.1f}".format(abs(demSmooth[1][len(demSmooth[1])-1]*100)) + "%"  #Need abs() so that you don't get -0.0
        #And append that label to demLabels
        demLabels.append(label)
        #We then take the line object from plotting the smoothed estimates and put it into demLines
        line, = plt.plot(demSmooth[0], demSmooth[1], linewidth=1.75)
        demLines.append(line)
        #ax.fill_between(demErr[0], np.add(demSmooth[1], demErr[1]), np.subtract(demSmooth[1], demErr[1]), facecolor='grey', alpha=.25)
    #Now we make demFinalEstimates a Numpy array
    demFinalEstimates = np.array(demFinalEstimates)
    #And we arrange the lines so that they are in descending order of the most recent estimates
    demLinesSorted = [demLines[x] for x in np.argsort(demFinalEstimates)[::-1]]
    #Do the same for the labels
    demLabelsSorted = [demLabels[x] for x in np.argsort(demFinalEstimates)[::-1]]
    #Put the lines and labels into a legend, which will appear below the graph in the center with four columns
    plt.legend(demLinesSorted, demLabelsSorted, bbox_to_anchor=(.5,-.08), borderaxespad=0.5, loc='center', ncol=4)
    #Make the title of the plot look like "The Democratic Primary Field: May 03-Jun 02"
    plt.title('The Democratic Primary Field: %(begindate)s-%(enddate)s' %{"begindate":beginDate.strftime('%b %d'), "enddate":endDate.strftime('%b %d')}, fontsize=20)
    #Save the chart in Charts with a filename that includes the timestamp of the latest estimate.
    plt.savefig('Charts/DemS_%(date)s.png' %{"date":str(endDate)}, bbox_inches='tight')
    
    #Now repeat the same process as above, but for the Republicans.
    plt.figure(figsize=(25,15))
    ax = plt.axes()
    ax.set_color_cycle([(.79, 0, 0), (.79, 0, .78), (.45, 0, .79), (0, .04, .79), (0, .74, .79), (0, .79, .2), (.96, .78, .07), (1, .42, 0), (.91, .44, .54), (.29, .62, 1), (.54, .6, 0), (0, .86, .62), (1, 0, .7), (1, .65, .47), (.6, 0, .39), (.6, .23, 0)])
    ax.set_ylim([0,.25])
    repubFinalEstimates = []
    repubLines = []
    repubLabels = []
    for r in repubE:
        endDate = repubE[r][0][len(repubE[r][0])-1]
        beginDate = endDate - datetime.timedelta(30)
        ax.set_xlim([beginDate, endDate])
        #repubErr = smoothEstimates(repubU[r])
        #repubErr = [repubErr[0], 1.96*np.sqrt(repubErr[1])]
        repubSmooth = repubE[r]
        repubFinalEstimates.append(abs(repubSmooth[1][len(repubSmooth[1])-1]))
        label = r + ": " + "{:.1f}".format(abs(repubSmooth[1][len(repubSmooth[1])-1]*100)) + "%"  #Need abs() so that you don't get -0.0
        repubLabels.append(label)
        line, = plt.plot(repubSmooth[0], repubSmooth[1], linewidth=1.5)
        repubLines.append(line)
        #ax.fill_between(repubU[r][0], np.add(repubE[r][1], repubErr), np.subtract(repubE[r][1], repubErr), facecolor='grey', alpha=.25)
    repubFinalEstimates = np.array(repubFinalEstimates)
    repubLinesSorted = [repubLines[x] for x in np.argsort(repubFinalEstimates)[::-1]]
    repubLabelsSorted = [repubLabels[x] for x in np.argsort(repubFinalEstimates)[::-1]]
    plt.legend(repubLinesSorted, repubLabelsSorted, bbox_to_anchor=(.5,-.08), borderaxespad=0.5, loc='center', ncol=4)
    plt.title('The Republican Primary Field: %(begindate)s-%(enddate)s' %{"begindate":beginDate.strftime('%b %d'), "enddate":endDate.strftime('%b %d')}, fontsize=20)
    plt.savefig('Charts/RepubS_%(date)s.png' %{"date":str(endDate)}, bbox_inches='tight')

#This is here so that the file can be directly executed rather than have to call the main method plotEstimates()
plotEstimates()
