import unittest

from build import bid_table


class PublicBidText(unittest.TestCase):
    def test_zero_city_keeps_state_and_real_city_stays_visible(self):
        notice = dict(city='0', state='NE', title='Synthetic notice', link='https://sam.gov/opp/example/view', agency='Sample buyer', sol='', due='2099-12-01', type='Solicitation', set_aside='')
        self.assertIn('data-label="Work site">Nebraska</td>', bid_table([notice], 'Examples'))
        self.assertIn('data-label="Work site">Omaha, Nebraska</td>', bid_table([dict(notice, city='Omaha')], 'Examples'))
