use strict;
use warnings;

use Domain::PublicSuffix;
my $ps = Domain::PublicSuffix->new({'data_file' => '/var/lib/mailrobots/publicsuffix/public_suffix_list.dat'});
sub public_suffix {
        my $domain = shift // die 'Missing domain';
        my $result = $ps->get_root_domain ($domain);
        return $result // '';
}

use Geo::IP;
my $g4 = Geo::IP->open_type(Geo::IP::GEOIP_ASNUM_EDITION, Geo::IP::GEOIP_CHECK_CACHE | Geo::IP::GEOIP_MEMORY_CACHE) || die;
sub asnum_v4 {
    my $addr = shift // die 'Missing address';
    return $g4->name_by_addr($addr) // '';
}
#my $g6 = Geo::IP->open_type (Geo::IP::GEOIP_ASNUM_EDITION_V6, Geo::IP::GEOIP_CHECK_CACHE | Geo::IP::GEOIP_MEMORY_CACHE) || die;
#sub asnum_v6 {
#       my $addr = shift // die 'Missing address';
#       return $g6->name_by_addr ($addr) // '';
#}
