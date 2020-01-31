#
#

OUTPUTS := members.csv mailinglist.csv door.csv merged_contactlist.csv

all: $(OUTPUTS)

clean:
	rm -f $(OUTPUTS)

members.csv:
	./from_accounts >$@

mailinglist.csv:
	./from_mailinglist >$@

door.csv:
	./from_door >$@

merged_contactlist.csv: door.csv mailinglist.csv members.csv
	./merged_contactlist $^ >$@
