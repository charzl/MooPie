"""Per-stock bounded heaps must agree exactly with the full-sort reference."""
import copy
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('bounded_rules',ROOT/'put_rules.py')
rules=importlib.util.module_from_spec(spec);spec.loader.exec_module(rules)


class BoundedRankingTests(unittest.TestCase):
    def setUp(self):
        base=json.loads((ROOT/'example.json').read_text())
        self.dataset=copy.deepcopy(base)
        self.dataset.update(symbols=[],contracts=[],daily_series=[])
        for stock_index,symbol in enumerate(('AAA','BBB','CCC','DDD')):
            stock=json.loads(json.dumps(base).replace('TEST',symbol))
            self.dataset['symbols'].append('US.'+symbol)
            self.dataset['daily_series'].extend(stock['daily_series'])
            for index in range(55):
                row=copy.deepcopy(stock['contracts'][0])
                strike=90-index*.1
                bid=1+(index%17)*.03+stock_index*.1
                row.update(code=f'US.{symbol}-{index:03d}',strike=strike,snapshot_strike=strike,bid=bid,ask=bid*1.05)
                if index%9==0: row['earnings']=None
                self.dataset['contracts'].append(row)

    def test_top_twenty_matches_full_sort_for_all_presets_and_custom_ties_and_nulls(self):
        orders=list(rules.RANKING_SORT_ORDERS.values())+[
            [['strike','asc'],['symbol','desc']], [['earnings_date','asc']], [['earnings_date','desc']]]
        for order in orders:
            with self.subTest(order=order):
                config=dict(sort_order=order)
                full=rules.recommend(self.dataset,configuration=config,top_n=20)
                bounded=rules.recommend(self.dataset,configuration=config,top_n=20,per_symbol_limit=20)
                self.assertEqual(bounded['ranked_codes'],full['ranked_codes'][:20])
                self.assertEqual(bounded['ranking_views'],full['ranking_views'])
                self.assertEqual(bounded['qualified_count'],full['qualified_count'])
                self.assertLessEqual(bounded['ranking_reduction']['merge_pool_size'],4*20)
                self.assertTrue(bounded['ranked_truncated'])

    def test_bounded_mode_never_calls_full_sort_and_all_top_counts_share_exact_prefix(self):
        expected=rules.recommend(self.dataset,top_n=20)['ranked_codes'][:20]
        with patch.object(rules,'sorted_candidates',side_effect=AssertionError('No full sort in bounded mode')):
            for count in (5,10,20):
                result=rules.recommend(self.dataset,top_n=count,per_symbol_limit=20)
                self.assertEqual([row['code'] for row in result['recommendations']],expected[:count])
                self.assertEqual(len(result['ranked']),20)
                self.assertEqual(result['total_contracts'],220)

    def test_changed_filter_and_sort_reselect_from_full_original_contracts(self):
        config=dict(sort_order=[['strike','asc']],filters={'max-cost':dict(enabled=True,threshold=8800)})
        full=rules.recommend(self.dataset,configuration=config,top_n=20)
        bounded=rules.recommend(self.dataset,configuration=config,top_n=20,per_symbol_limit=20)
        self.assertEqual(bounded['ranked_codes'],full['ranked_codes'][:20])
        self.assertTrue(all(row['cash_collateral']<8800 for row in bounded['recommendations']))
