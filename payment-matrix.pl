#!/usr/bin/perl

use Mojo::UserAgent;
use Data::Dumper;
my $ua = new Mojo::UserAgent;
my $dom = $ua->get("http://door/active.php")->res->dom;

my @users;
$dom->find("tr")->each(sub {
    my $e = $_;
    my $name = $e->find('td:nth-of-type(1)')->map('all_text')->join('')->to_string;
    my $ping = $e->find('td:nth-of-type(4)')->map('all_text')->join('')->to_string;
    my ($month) = $ping =~ m/^(\d{4}-\d{2})/;
    push @users, {
	name  => "$name",
	ping  => "$ping",
	month => $month
    } if length($ping) > 0;
});

@users = sort { $b->{month} cmp $a->{month} or $b->{name} cmp $a->{name}}  @users;

print Dumper @users;

