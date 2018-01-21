#
#

OUTPUTS := members.csv mailinglist.csv door.csv

all: $(OUTPUTS)

clean:
	rm -f $(OUTPUTS)

members.csv:
	./from_accounts >$@

mailinglist.csv:
	./from_mailinglist >$@

door.csv:
	./from_door >$@
