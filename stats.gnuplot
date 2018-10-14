set timestamp 'generated at %F %T'
set xlabel 'Time (GMT)'

set xtics out rotate by -15
set grid ytics mytics lw 2, lw 1
set grid xtics
set autoscale fix

set key left top Left title 'Legend' box 3

set timefmt '%s'
set xdata time
set format x '%Y-%m-%d %H:%M'
set mouse mouseformat 5
set style data lines
set terminal pdf size 11,8


set output 'pages/stats.pdf'


set title 'Cash on hand'
set ylabel 'HKD'
plot \
    'pages/stats.tsv' using 1:4  title 'month subtotal', \
    'pages/stats.tsv' using 1:3  title 'balance',

set title 'Cashflow'
set ylabel 'HKD'
plot \
    'pages/stats.tsv' using 1:6  title 'incoming', \
    'pages/stats.tsv' using 1:5  title 'outgoing', \
    'pages/stats.tsv' using 1:7  title 'dues', \
    'pages/stats.tsv' using 1:8  title 'other',

set title 'Members'
set ylabel 'number of members'
plot \
    'pages/stats.tsv' using 1:9  title 'members',

set title 'Average Revenue per Member'
set ylabel 'ARPM'
plot \
    'pages/stats.tsv' using 1:10  title 'ARPM',

