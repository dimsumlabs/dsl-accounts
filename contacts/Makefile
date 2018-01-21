#
#

OUTPUTS := members.csv mailinglist.csv

all: $(OUTPUTS)

clean:
	rm -f $(OUTPUTS)

members.csv:
	./from_accounts >$@

mailinglist.csv:
	./from_mailinglist >$@

