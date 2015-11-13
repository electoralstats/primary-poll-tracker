primary-poll-tracker is the Electoral Statistics tool to track national standing in the 2016 Presidential primaries.

PollFetcher.py fetches the polls from [Pollster](http://elections.huffingtonpost.com/pollster) and puts them in a MySQL database. The script first adjusts the MySQL database according to the candidate lists dem-candidates.txt and repub-candidates.txt and then fetches polling for all of those candidates

PollAggregator.py then goes through candidate-by-candidate and runs them through a Kalman filter (which resides in KalmanFilter.py), as described [here](http://citeseerx.ist.psu.edu/viewdoc/download?doi=10.1.1.397.6111&rep=rep1&type=pdf) and then outputs charts such as those titled Dem.png and Repub.png.
