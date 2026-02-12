"""
Central Polling Data for IL-09
Update this file ONCE to reflect all scripts.
"""

# Shared constants
house_effect = 2

# Central Poll List
POLLS = [
    {
        'name': 'Fine Internal (Feb 2026)',
        'date': '2026-02-01',
        'pollster_quality': 4,
        'sample_size': 500,
        'margin_of_error': 4.4,
        'is_internal': True,
        'internal_for': 'Fine',
        'house_effect_adjustment': house_effect,
        'pollster_id': 'Fine_Internal',
        'wave_id': 2,
        'results': {
            'Fine': 21, 'Biss': 21, 'Abughazaleh': 14,
            'Simmons': 7, 'Amiwala': 4, 'Andrew': 4, 'Huynh': 2
        },
        'undecided': 23
    },
    {
        'name': 'Fine Internal (Nov 2024)',
        'date': '2025-11-01',
        'pollster_quality': 4,
        'sample_size': 600,
        'margin_of_error': 3.4,
        'is_internal': True,
        'internal_for': 'Fine',
        'house_effect_adjustment': house_effect,
        'pollster_id': 'Fine_Internal',
        'wave_id': 1,
        'results': {
            'Fine': 13, 'Biss': 20, 'Abughazaleh': 14,
            'Simmons': 10, 'Amiwala': 5, 'Andrew': 1, 'Huynh': 4
        },
        'undecided': 28
    },{
        'name': 'Data for Progress (Nov 2025)',
        'date': '2025-10-26',
        'pollster_quality': 3,
        'sample_size': 569,
        'margin_of_error': 4.4,
        'pollster_id': 'Data For Progress',
        'wave_id': 1,
        'results': {
            'Fine': 10, 'Biss': 18, 'Abughazaleh': 18,
            'Simmons': 6, 'Amiwala': 6, 'Huynh': 5
        },
        'undecided': 31,
        'has_crosstabs':True,
        'crosstabs':{
            'Fine':{
                'female':13, 'male':6, 'no_college': 9, 'college':11,
                'white':10, 'very_liberal':7, 'somewhat_liberal':9,
                'moderate': 14, 'age_18-29':0, 'age_30-44':11,
                'age_45-65': 11,'age_65+':16
            },'Biss':{
                'female':16, 'male':21, 'no_college': 13, 'college':22,
                'white':20, 'very_liberal':19, 'somewhat_liberal':25,
                'moderate': 14, 'age_18-29':8, 'age_30-44':19,
                'age_45-65': 18,'age_65+':21
            },'Abughazaleh':{
                'female':17, 'male':19, 'no_college': 17, 'college':19,
                'white':19, 'very_liberal':29, 'somewhat_liberal':16,
                'moderate': 8, 'age_18-29':30, 'age_30-44':24,
                'age_45-65': 18,'age_65+':12
            },'Simmons':{
                'female':6, 'male':6, 'no_college': 7, 'college':6,
                'white':7, 'very_liberal':9, 'somewhat_liberal':7,
                'moderate': 3, 'age_18-29':5, 'age_30-44':8,
                'age_45-65': 9,'age_65+':3
            },'Amiwala':{
                'female':7, 'male':5, 'no_college': 4, 'college':7,
                'white':4, 'very_liberal':8, 'somewhat_liberal':4,
                'moderate': 6, 'age_18-29':18, 'age_30-44':6,
                'age_45-65': 5,'age_65+':3
            },'Huyhn':{
                'female':3, 'male':8, 'no_college': 8, 'college':3,
                'white':3, 'very_liberal':6, 'somewhat_liberal':5,
                'moderate': 3, 'age_18-29':1, 'age_30-44':12,
                'age_45-65': 5,'age_65+':2
            }
        },
        'crosstab_sample_sizes':{
                'female':316, 'male':253, 'no_college': 237, 'college':332,
                'white':417, 'very_liberal':243, 'somewhat_liberal':138,
                'moderate': 155, 'age_18-29':60, 'age_30-44':113,
                'age_45-65': 193,'age_65+':203
        }
    },{
        'name': 'MDW (Nov 2025)',
        'date': '2025-10-20',
        'pollster_quality': 3,
        'sample_size': 917,
        'margin_of_error': 3.4,
        'is_internal': True,
        'internal_for': 'Abughazaleh',
        'house_effect_adjustment': house_effect,
        'pollster_id': 'Abughazaleh_Internal',
        'wave_id': 1,
        'results': {
            'Fine': 9, 'Biss': 18, 'Abughazaleh': 13,
            'Simmons': 4, 'Amiwala': 2, 'Andrew': 2, 'Huynh': 3
        },
        'undecided': 46
    },{
        'name': 'Biss Internal (Nov 2025)',
        'date': '2025-10-25',
        'pollster_quality': 4,
        'sample_size': 500,
        'margin_of_error': 4.4,
        'is_internal': True,
        'internal_for': 'Biss',
        'house_effect_adjustment': house_effect,
        'pollster_id': 'Biss_Internal',
        'wave_id': 1,
        'results': {
            'Fine': 10, 'Biss': 31, 'Abughazaleh': 17,
            'Simmons': 6, 'Amiwala': 3, 'Andrew': 3, 'Huynh': 4
        },
        'undecided': 21
    }
    # ... Copy all other poll dicts here ...
]

# Shared simulation settings
UNDECIDED_ALLOCATION = {
    'proportional': 0.2,
    'top_candidates': 0.4,
    'random': 0.2,
    'stay_home': 0.2
}

CANDIDATES = ['Fine', 'Biss', 'Abughazaleh', 'Simmons', 'Amiwala', 'Andrew', 'Huynh']