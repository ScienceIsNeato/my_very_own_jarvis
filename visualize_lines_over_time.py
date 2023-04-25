import sys
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import datetime

dates = []
line_counts = []

for line in sys.stdin:
    values = line.strip().split()
    if len(values) != 3:
        continue

    commit_hash, date_str, count_str = values
    date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    count = int(count_str)

    dates.append(date)
    line_counts.append(count)

fig, ax = plt.subplots()
ax.plot(dates, line_counts)

ax.set(xlabel='Date', ylabel='Lines',
       title='Lines in Repo Over Time')
ax.grid()

fig.autofmt_xdate()
ax.fmt_xdata = mdates.DateFormatter('%Y-%m-%d')

plt.show()

