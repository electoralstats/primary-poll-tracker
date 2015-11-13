import numpy as np
#The kalman method takes a numpy array called "polls" which has n rows, each with 3 columns. The 1st column is the date of the poll, given as a date object, the 2nd column is the poll value, given as an integer, the 3rd column is the sample size.
def kalman(polls):
    #The first step is to sort the polls so the 1st row is the oldest poll, the n-th row is the newest poll
    #polls = sorted(polls, key=lambda x: x[0])
    #In order to make sure we don't get any divide by zero problems, we need to take out any polls with a zero sample size
    polls = [x for x in polls if x[2]>0]
    dates = [x[0] for x in polls]
    datesNoRepeat = sorted(list(set(dates)))
    #Next, we initialize the values of the Kalman filter for the first date
    d = datesNoRepeat[0]
    relevantPolls = [x for x in polls if x[0]==d]
    phat = [p[1]/100.0 for p in relevantPolls]
    shat = [(phat[p])*(1-phat[p])/relevantPolls[p][2] if phat[p]!=0 else (0.03*0.97/relevantPolls[p][2]) for p in range(0,len(phat))]
    #shat = [(phat[p])*(1-phat[p])/relevantPolls[p][2] for p in range(0,len(phat))]
    val = sum(np.multiply(phat, np.divide(1,shat)))/sum(np.divide(1,shat))
    variance = (1/sum(np.divide(1,shat)))
    estimates = [val]
    uncerts = [variance]
    for p in range(1,len(datesNoRepeat)):
        d = datesNoRepeat[p]
        relevantPolls = [x for x in polls if x[0]==d]
        phat = [l[1]/100.0 for l in relevantPolls]
       # if 0 in phat:
        #    val = 0
         #   variance = 0.03/sum([x[2] for x in relevantPolls])
        #else:
         #   shat = [(phat[l])*(1-phat[l])/relevantPolls[l][2] for l in range(0,len(phat))]
          #  val = sum(np.multiply(phat, np.divide(1,shat)))/sum(np.divide(1,shat))
           # variance = (1/sum(np.divide(1,shat)))
        shat = [(phat[p])*(1-phat[p])/relevantPolls[p][2] if phat[p]!=0 else (0.03*0.97/relevantPolls[p][2]) for p in range(0,len(phat))]
        val = sum(np.multiply(phat, np.divide(1,shat)))/sum(np.divide(1,shat))
        variance = (1/sum(np.divide(1,shat)))
        estimates.append(val)
        uncerts.append(variance)
    changes = [estimates[p]-estimates[p-1] for p in range(1, len(estimates))]
    meanChange = sum(changes)/len(changes)
    changeVar = sum([(x-meanChange)**2 for x in changes])/len(changes)
    filteredEst = [estimates[0]]
    filteredUncert = [uncerts[0]]
    for p in range(1, len(datesNoRepeat)):
        weight = filteredUncert[p-1]/(filteredUncert[p-1]+uncerts[p])
        newEst = weight*estimates[p] + (1-weight)*estimates[p-1]
        newUncert = filteredUncert[p-1]*(1-weight) + changeVar
        filteredEst.append(newEst)
        filteredUncert.append(newUncert)
    smoothEst = [0] * len(filteredEst)
    smoothEst[len(smoothEst)-1] = filteredEst[len(filteredEst)-1]
    for p in range(len(smoothEst)-2, -1, -1):
        smoothEst[p] = filteredEst[p] + (smoothEst[p+1] - filteredEst[p])*(1-(changeVar/filteredUncert[p+1]))
    return datesNoRepeat, filteredEst, filteredUncert
