from datetime import date,timedelta
import unittest

from moopython.position_efficiency import put_efficiency


class EfficiencyTests(unittest.TestCase):
    def calculate(self,**changes):
        values=dict(opening_premium=10,buyback_price=2,strike=100,
                    opened_on='2026-09-17',expires_on='2026-12-16',as_of='2026-10-17',
                    exit_threshold_pct=80)
        values.update(changes)
        return put_efficiency(**values)

    def test_eighty_percent_in_thirty_of_ninety_days_retains_thirty_percent(self):
        r=self.calculate()
        self.assertAlmostEqual(r['profit_capture_pct'],80)
        self.assertAlmostEqual(r['time_elapsed_pct'],100/3)
        self.assertAlmostEqual(r['retention_pct'],30)
        self.assertAlmostEqual(r['opening_daily_return_pct'],1000/10000/90*100)
        self.assertAlmostEqual(r['remaining_daily_return_pct'],200/10000/60*100)
        self.assertEqual(r['signal'],'review_close')
        self.assertFalse(r['assumptions']['risk_included'])

    def test_same_profit_with_five_days_remaining_has_higher_efficiency(self):
        r=self.calculate(as_of='2026-12-11')
        self.assertEqual(r['remaining_days'],5)
        self.assertAlmostEqual(r['retention_pct'],360)
        self.assertAlmostEqual(r['remaining_daily_return_pct'],.4)
        self.assertEqual(r['signal'],'hold')

    def test_configured_eighty_percent_boundary_is_strict_and_separate_from_benchmark(self):
        exact=self.calculate(buyback_price=4,as_of='2026-11-01')
        self.assertAlmostEqual(exact['retention_pct'],80)
        self.assertEqual(exact['benchmark_pct'],100)
        self.assertEqual(exact['signal'],'hold')
        self.assertFalse(exact['exit_triggered'])
        self.assertEqual(self.calculate(buyback_price=3.99,as_of='2026-11-01')['suggested_action'],'buy_to_close')
        self.assertEqual(self.calculate(buyback_price=4.01,as_of='2026-11-01')['signal'],'hold')
        self.assertEqual(self.calculate(buyback_price=4,as_of='2026-11-01',exit_threshold_pct=90)['signal'],'review_close')
        self.assertEqual(self.calculate(buyback_price=4,as_of='2026-11-01',exit_threshold_pct=60)['signal'],'hold')

    def test_unconfigured_indicator_gives_no_trading_direction(self):
        r=self.calculate(exit_threshold_pct=None)
        self.assertAlmostEqual(r['retention_pct'],30)
        self.assertEqual(r['signal'],'observe')
        self.assertIsNone(r['configuration']['exit_threshold_pct'])
        self.assertIsNone(r['exit_triggered'])
        self.assertIsNone(r['suggested_action'])

    def test_efficiency_matches_the_profit_and_time_fraction_identity(self):
        start=date(2026,1,1)
        for original in (30,90,180):
            for elapsed in (1,10,29):
                for premium_left in (.05,.2,.8):
                    r=self.calculate(opened_on=start,expires_on=start+timedelta(days=original),
                        as_of=start+timedelta(days=elapsed),buyback_price=10*premium_left)
                    expected=(1-r['profit_capture_pct']/100)/(1-r['time_elapsed_pct']/100)*100
                    self.assertAlmostEqual(r['retention_pct'],expected)

    def test_not_profitable_or_same_day_cannot_generate_a_hold_recommendation(self):
        for price in (10,12):
            r=self.calculate(buyback_price=price)
            self.assertGreater(r['retention_pct'],100)
            self.assertEqual(r['signal'],'not_profitable')
        self.assertEqual(self.calculate(as_of='2026-09-17')['signal'],'same_day')

    def test_expiry_and_post_expiry_do_not_divide_by_zero_or_suggest_holding(self):
        for day in ('2026-12-16','2026-12-17'):
            r=self.calculate(as_of=day)
            self.assertEqual(r['signal'],'expired')
            self.assertEqual(r['remaining_days'],0)
            self.assertIsNone(r['retention_pct'])
            self.assertIsNone(r['remaining_daily_return_pct'])

    def test_zero_buyback_price_and_scaling_preserve_the_financial_units(self):
        r=self.calculate(buyback_price=0)
        self.assertEqual(r['retention_pct'],0)
        self.assertEqual(r['profit_capture_pct'],100)
        self.assertEqual(r['signal'],'review_close')
        scaled=self.calculate(strike=1000,opening_premium=100,buyback_price=20)
        original=self.calculate()
        for key in ('remaining_daily_return_pct','opening_daily_return_pct','retention_pct'):
            self.assertAlmostEqual(original[key],scaled[key])

    def test_invalid_money_dates_and_overflow_are_rejected(self):
        invalid=[dict(opening_premium=0),dict(strike=0),dict(buyback_price=-1),
                 dict(opening_premium=True),dict(buyback_price=float('nan')),
                 dict(strike=float('inf')),dict(opening_premium=None),
                 dict(opened_on='2026-12-16'),dict(as_of='2026-09-16'),
                 dict(as_of='20261017'),dict(expires_on='not a date'),
                 dict(exit_threshold_pct=0),dict(exit_threshold_pct=-1),
                 dict(exit_threshold_pct=True),dict(exit_threshold_pct=float('inf')),
                 dict(opening_premium=1e308,strike=1e-300)]
        for values in invalid:
            with self.subTest(values=values),self.assertRaises(ValueError): self.calculate(**values)


if __name__=='__main__': unittest.main()
