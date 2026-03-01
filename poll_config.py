"""
Central Polling Data for IL-09
Update this file ONCE to reflect all scripts.
"""

# Shared constants
house_effect = 2

# Central Poll List
POLLS = [
    {
        # =========================================================================
        # IDENTIFICATION
        # =========================================================================
        'name': 'PPP/RoundTable Feb 20-21 2026',
        'date': '2026-02-21',
        'pollster_id': 'PPP_Feb2026',
        'sample_size': 501,
        'pollster_quality': 4.5,
        'is_internal': False,
        'has_crosstabs': True,

        # =========================================================================
        # Q3 — TOPLINE VOTE SHARES
        # =========================================================================
        'results': {
            'Amiwala': 4,
            'Andrew': 5,
            'Huynh': 2,
            'Biss': 24,
            'Fine': 16,
            'Abughazaleh': 17,
            'Simmons': 6,
            'Others': 4,  # "Someone else"
        },
        'undecided': 22,  # "Not sure"

        # =========================================================================
        # Q4 — SECOND CHOICE TOPLINE
        # =========================================================================
        'second_choice': {
            'Amiwala': 7,
            'Andrew': 3,
            'Huynh': 6,
            'Biss': 15,
            'Fine': 13,
            'Abughazaleh': 10,
            'Simmons': 7,
            'Others': 2,
            'no_second': 38,
        },

        # =========================================================================
        # Q4 × Q3 — SECOND CHOICE MATRIX (by first choice)
        # =========================================================================
        'second_choice_matrix': {

            'Fine': {
                'Amiwala': 17,
                'Andrew': 12,
                'Huynh': 5,
                'Biss': 51,
                'Abughazaleh': 9,
                'Simmons': 3,
                'others': 0,
                'no_second': 2,
            },

            'Biss': {
                'Amiwala': 17,
                'Andrew': 5,
                'Huynh': 10,
                'Fine': 31,
                'Abughazaleh': 14,
                'Simmons': 11,
                'others': 0,
                'no_second': 18,
            },

            'Abughazaleh': {
                'Amiwala': 41,
                'Andrew': 13,
                'Huynh': 18,
                'Biss': 14,
                'Fine': 2,
                'Simmons': 21,
                'others': 1,
                'no_second': 17,
            },

            'Simmons': {
                'Amiwala': 5,
                'Andrew': 5,
                'Huynh': 16,
                'Biss': 8,
                'Fine': 6,
                'Abughazaleh': 50,
                'others': 0,
                'no_second': 12,
            },

            'Amiwala': {
                'Andrew': 0,
                'Huynh': 3,
                'Biss': 17,
                'Fine': 17,
                'Abughazaleh': 48,
                'Simmons': 11,
                'others': 0,
                'no_second': 16,
            },

            'Andrew': {
                'Amiwala': 5,
                'Huynh': 5,
                'Biss': 22,
                'Fine': 31,
                'Abughazaleh': 13,
                'Simmons': 2,
                'others': 3,
                'no_second': 20,
            },

            'Huynh': {
                'Amiwala': 3,
                'Andrew': 1,
                'Biss': 13,
                'Fine': 7,
                'Abughazaleh': 28,
                'Simmons': 14,
                'others': 0,
                'no_second': 43,
            },
        },

        # =========================================================================
        # Q6–Q12 — FAVORABILITY RATINGS
        # =========================================================================
        'favorability': {

            'Amiwala': {
                'overall': {'favorable': 28, 'unfavorable': 8, 'not_heard': 48, 'not_sure': 17},
                'by_gender': {
                    'woman': {'favorable': 25, 'unfavorable': 6, 'not_heard': 50, 'not_sure': 19},
                    'man': {'favorable': 31, 'unfavorable': 10, 'not_heard': 44, 'not_sure': 14},
                },
                'by_age': {
                    'age_18_45': {'favorable': 45, 'unfavorable': 12, 'not_heard': 31, 'not_sure': 13},
                    'age_46_65': {'favorable': 24, 'unfavorable': 8, 'not_heard': 51, 'not_sure': 17},
                    'age_65plus': {'favorable': 16, 'unfavorable': 3, 'not_heard': 60, 'not_sure': 20},
                },
                'by_race': {
                    'hispanic': {'favorable': 20, 'unfavorable': 20, 'not_heard': 54, 'not_sure': 6},
                    'white': {'favorable': 29, 'unfavorable': 5, 'not_heard': 49, 'not_sure': 17},
                    'asian': {'favorable': 27, 'unfavorable': 16, 'not_heard': 36, 'not_sure': 21},
                    'black': {'favorable': 33, 'unfavorable': 0, 'not_heard': 42, 'not_sure': 25},
                    'other': {'favorable': 18, 'unfavorable': 27, 'not_heard': 51, 'not_sure': 3},
                },
                'by_party': {
                    'democrat': {'favorable': 30, 'unfavorable': 6, 'not_heard': 47, 'not_sure': 18},
                    'independent': {'favorable': 23, 'unfavorable': 12, 'not_heard': 50, 'not_sure': 14},
                },
                'by_senate_district': {
                    'sd7': {'favorable': 33, 'unfavorable': 5, 'not_heard': 45, 'not_sure': 16},
                    'sd8': {'favorable': 32, 'unfavorable': 13, 'not_heard': 42, 'not_sure': 13},
                    'sd9': {'favorable': 29, 'unfavorable': 11, 'not_heard': 43, 'not_sure': 21},
                },
            },

            'Andrew': {
                'overall': {'favorable': 20, 'unfavorable': 12, 'not_heard': 45, 'not_sure': 23},
                'by_gender': {
                    'woman': {'favorable': 18, 'unfavorable': 10, 'not_heard': 50, 'not_sure': 22},
                    'man': {'favorable': 21, 'unfavorable': 13, 'not_heard': 40, 'not_sure': 26},
                },
                'by_age': {
                    'age_18_45': {'favorable': 9, 'unfavorable': 24, 'not_heard': 45, 'not_sure': 22},
                    'age_46_65': {'favorable': 25, 'unfavorable': 8, 'not_heard': 45, 'not_sure': 22},
                    'age_65plus': {'favorable': 23, 'unfavorable': 5, 'not_heard': 46, 'not_sure': 26},
                },
                'by_race': {
                    'hispanic': {'favorable': 27, 'unfavorable': 25, 'not_heard': 27, 'not_sure': 21},
                    'white': {'favorable': 24, 'unfavorable': 9, 'not_heard': 43, 'not_sure': 24},
                    'asian': {'favorable': 5, 'unfavorable': 22, 'not_heard': 52, 'not_sure': 21},
                    'black': {'favorable': 0, 'unfavorable': 14, 'not_heard': 63, 'not_sure': 23},
                    'other': {'favorable': 9, 'unfavorable': 11, 'not_heard': 57, 'not_sure': 24},
                },
                'by_party': {
                    'democrat': {'favorable': 21, 'unfavorable': 10, 'not_heard': 46, 'not_sure': 23},
                    'independent': {'favorable': 15, 'unfavorable': 16, 'not_heard': 42, 'not_sure': 26},
                },
                'by_senate_district': {
                    'sd7': {'favorable': 14, 'unfavorable': 14, 'not_heard': 50, 'not_sure': 22},
                    'sd8': {'favorable': 23, 'unfavorable': 7, 'not_heard': 44, 'not_sure': 27},
                    'sd9': {'favorable': 29, 'unfavorable': 18, 'not_heard': 32, 'not_sure': 21},
                },
            },

            'Huynh': {
                'overall': {'favorable': 23, 'unfavorable': 9, 'not_heard': 47, 'not_sure': 21},
                'by_gender': {
                    'woman': {'favorable': 17, 'unfavorable': 9, 'not_heard': 54, 'not_sure': 20},
                    'man': {'favorable': 32, 'unfavorable': 9, 'not_heard': 37, 'not_sure': 22},
                },
                'by_age': {
                    'age_18_45': {'favorable': 31, 'unfavorable': 14, 'not_heard': 37, 'not_sure': 18},
                    'age_46_65': {'favorable': 20, 'unfavorable': 9, 'not_heard': 51, 'not_sure': 20},
                    'age_65plus': {'favorable': 20, 'unfavorable': 6, 'not_heard': 51, 'not_sure': 23},
                },
                'by_race': {
                    'hispanic': {'favorable': 34, 'unfavorable': 18, 'not_heard': 33, 'not_sure': 14},
                    'white': {'favorable': 24, 'unfavorable': 7, 'not_heard': 47, 'not_sure': 21},
                    'asian': {'favorable': 28, 'unfavorable': 20, 'not_heard': 35, 'not_sure': 17},
                    'black': {'favorable': 0, 'unfavorable': 10, 'not_heard': 68, 'not_sure': 23},
                    'other': {'favorable': 33, 'unfavorable': 6, 'not_heard': 39, 'not_sure': 22},
                },
                'by_party': {
                    'democrat': {'favorable': 25, 'unfavorable': 9, 'not_heard': 46, 'not_sure': 20},
                    'independent': {'favorable': 20, 'unfavorable': 10, 'not_heard': 48, 'not_sure': 23},
                },
                'by_senate_district': {
                    'sd7': {'favorable': 36, 'unfavorable': 12, 'not_heard': 34, 'not_sure': 18},
                    'sd8': {'favorable': 26, 'unfavorable': 10, 'not_heard': 43, 'not_sure': 21},
                    'sd9': {'favorable': 19, 'unfavorable': 10, 'not_heard': 48, 'not_sure': 23},
                },
            },

            'Biss': {
                'overall': {'favorable': 51, 'unfavorable': 23, 'not_heard': 13, 'not_sure': 14},
                'by_gender': {
                    'woman': {'favorable': 54, 'unfavorable': 20, 'not_heard': 14, 'not_sure': 12},
                    'man': {'favorable': 46, 'unfavorable': 27, 'not_heard': 12, 'not_sure': 15},
                },
                'by_age': {
                    'age_18_45': {'favorable': 45, 'unfavorable': 25, 'not_heard': 15, 'not_sure': 15},
                    'age_46_65': {'favorable': 45, 'unfavorable': 30, 'not_heard': 15, 'not_sure': 9},
                    'age_65plus': {'favorable': 63, 'unfavorable': 13, 'not_heard': 8, 'not_sure': 16},
                },
                'by_race': {
                    'hispanic': {'favorable': 57, 'unfavorable': 20, 'not_heard': 14, 'not_sure': 9},
                    'white': {'favorable': 57, 'unfavorable': 20, 'not_heard': 10, 'not_sure': 13},
                    'asian': {'favorable': 20, 'unfavorable': 39, 'not_heard': 30, 'not_sure': 10},
                    'black': {'favorable': 27, 'unfavorable': 21, 'not_heard': 23, 'not_sure': 28},
                    'other': {'favorable': 44, 'unfavorable': 40, 'not_heard': 8, 'not_sure': 7},
                },
                'by_party': {
                    'democrat': {'favorable': 58, 'unfavorable': 18, 'not_heard': 11, 'not_sure': 13},
                    'independent': {'favorable': 30, 'unfavorable': 34, 'not_heard': 19, 'not_sure': 17},
                },
                'by_senate_district': {
                    'sd7': {'favorable': 50, 'unfavorable': 21, 'not_heard': 11, 'not_sure': 17},
                    'sd8': {'favorable': 59, 'unfavorable': 20, 'not_heard': 10, 'not_sure': 11},
                    'sd9': {'favorable': 49, 'unfavorable': 30, 'not_heard': 11, 'not_sure': 10},
                },
            },

            'Fine': {
                'overall': {'favorable': 36, 'unfavorable': 35, 'not_heard': 14, 'not_sure': 14},
                'by_gender': {
                    'woman': {'favorable': 41, 'unfavorable': 33, 'not_heard': 13, 'not_sure': 13},
                    'man': {'favorable': 34, 'unfavorable': 34, 'not_heard': 15, 'not_sure': 18},
                },
                'by_age': {
                    'age_18_45': {'favorable': 14, 'unfavorable': 54, 'not_heard': 18, 'not_sure': 14},
                    'age_46_65': {'favorable': 36, 'unfavorable': 33, 'not_heard': 13, 'not_sure': 18},
                    'age_65plus': {'favorable': 58, 'unfavorable': 20, 'not_heard': 11, 'not_sure': 10},
                },
                'by_race': {
                    'hispanic': {'favorable': 28, 'unfavorable': 39, 'not_heard': 28, 'not_sure': 6},
                    'white': {'favorable': 41, 'unfavorable': 33, 'not_heard': 10, 'not_sure': 16},
                    'asian': {'favorable': 10, 'unfavorable': 49, 'not_heard': 30, 'not_sure': 10},
                    'black': {'favorable': 24, 'unfavorable': 36, 'not_heard': 26, 'not_sure': 14},
                    'other': {'favorable': 44, 'unfavorable': 36, 'not_heard': 6, 'not_sure': 14},
                },
                'by_party': {
                    'democrat': {'favorable': 39, 'unfavorable': 33, 'not_heard': 13, 'not_sure': 15},
                    'independent': {'favorable': 30, 'unfavorable': 40, 'not_heard': 18, 'not_sure': 12},
                },
                'by_senate_district': {
                    'sd7': {'favorable': 27, 'unfavorable': 43, 'not_heard': 15, 'not_sure': 15},
                    'sd8': {'favorable': 39, 'unfavorable': 33, 'not_heard': 11, 'not_sure': 17},
                    'sd9': {'favorable': 39, 'unfavorable': 38, 'not_heard': 13, 'not_sure': 11},
                },
                # Fine: high unfavorables among young voters (54% unfav 18-45)
                # vs. strong favorables among 65+ (58% fav).
            },

            'Abughazaleh': {
                'overall': {'favorable': 35, 'unfavorable': 27, 'not_heard': 24, 'not_sure': 14},
                'by_gender': {
                    'woman': {'favorable': 30, 'unfavorable': 24, 'not_heard': 30, 'not_sure': 16},
                    'man': {'favorable': 38, 'unfavorable': 31, 'not_heard': 16, 'not_sure': 15},
                },
                'by_age': {
                    'age_18_45': {'favorable': 49, 'unfavorable': 32, 'not_heard': 12, 'not_sure': 7},
                    'age_46_65': {'favorable': 30, 'unfavorable': 30, 'not_heard': 25, 'not_sure': 14},
                    'age_65plus': {'favorable': 25, 'unfavorable': 18, 'not_heard': 35, 'not_sure': 21},
                },
                'by_race': {
                    'hispanic': {'favorable': 21, 'unfavorable': 34, 'not_heard': 34, 'not_sure': 11},
                    'white': {'favorable': 35, 'unfavorable': 26, 'not_heard': 23, 'not_sure': 16},
                    'asian': {'favorable': 48, 'unfavorable': 23, 'not_heard': 19, 'not_sure': 10},
                    'black': {'favorable': 31, 'unfavorable': 24, 'not_heard': 32, 'not_sure': 12},
                    'other': {'favorable': 38, 'unfavorable': 38, 'not_heard': 23, 'not_sure': 2},
                },
                'by_party': {
                    'democrat': {'favorable': 36, 'unfavorable': 26, 'not_heard': 22, 'not_sure': 15},
                    'independent': {'favorable': 32, 'unfavorable': 22, 'not_heard': 32, 'not_sure': 14},
                },
                'by_senate_district': {
                    'sd7': {'favorable': 47, 'unfavorable': 24, 'not_heard': 14, 'not_sure': 16},
                    'sd8': {'favorable': 19, 'unfavorable': 43, 'not_heard': 28, 'not_sure': 9},
                    'sd9': {'favorable': 34, 'unfavorable': 28, 'not_heard': 24, 'not_sure': 15},
                },
            },

            'Simmons': {
                'overall': {'favorable': 28, 'unfavorable': 8, 'not_heard': 46, 'not_sure': 18},
                'by_gender': {
                    'woman': {'favorable': 24, 'unfavorable': 7, 'not_heard': 51, 'not_sure': 18},
                    'man': {'favorable': 33, 'unfavorable': 7, 'not_heard': 40, 'not_sure': 20},
                },
                'by_age': {
                    'age_18_45': {'favorable': 39, 'unfavorable': 11, 'not_heard': 33, 'not_sure': 18},
                    'age_46_65': {'favorable': 26, 'unfavorable': 6, 'not_heard': 49, 'not_sure': 18},
                    'age_65plus': {'favorable': 20, 'unfavorable': 6, 'not_heard': 55, 'not_sure': 19},
                },
                'by_race': {
                    'hispanic': {'favorable': 10, 'unfavorable': 26, 'not_heard': 56, 'not_sure': 8},
                    'white': {'favorable': 29, 'unfavorable': 6, 'not_heard': 43, 'not_sure': 22},
                    'asian': {'favorable': 25, 'unfavorable': 11, 'not_heard': 44, 'not_sure': 20},
                    'black': {'favorable': 35, 'unfavorable': 0, 'not_heard': 61, 'not_sure': 4},
                    'other': {'favorable': 37, 'unfavorable': 6, 'not_heard': 47, 'not_sure': 10},
                },
                'by_party': {
                    'democrat': {'favorable': 31, 'unfavorable': 8, 'not_heard': 43, 'not_sure': 18},
                    'independent': {'favorable': 21, 'unfavorable': 5, 'not_heard': 55, 'not_sure': 19},
                },
                'by_senate_district': {
                    'sd7': {'favorable': 53, 'unfavorable': 9, 'not_heard': 24, 'not_sure': 13},
                    'sd8': {'favorable': 21, 'unfavorable': 5, 'not_heard': 60, 'not_sure': 14},
                    'sd9': {'favorable': 20, 'unfavorable': 10, 'not_heard': 53, 'not_sure': 17},
                },
                # Best fav/unfav ratio (28/8 = +20 net) but 46% haven't heard of him.
                # SD7 outlier: 53% favorable — Rogers Park/Edgewater base.
            },
        },

        # =========================================================================
        # VOTE SHARE CROSSTABS  (Q3 by demographic subgroup)
        # =========================================================================
        'crosstab_sample_sizes': {
            'female': 261,
            'male': 195,
            'age_18-45': 150,
            'age_46-65': 165,
            'age_65+': 185,
            'hispanic': 50,
            'white': 346,
            'asian': 35,
            'black': 45,
            'democrat': 386,
            'independent': 105,
            'hs_or_less': 28,
            'some_college': 110,
            'college_2yr': 40,
            'college_4yr': 160,
            'postgrad': 160,
            'sd7': 145,
            'sd8': 85,
            'sd9': 150,
            'landline': 115,
            'text': 386,
        },

        'crosstabs': {

            'Amiwala': {
                'female': 3, 'male': 4,
                'age_18-29': 7, 'age_30-44': 7, 'age_45-65': 5, 'age_65+': 1,
                'hispanic': 0, 'white': 4, 'asian': 4, 'black': 14,
                'democrat': 4, 'independent': 4,
                'somewhat_liberal': 4, 'moderate': 4, 'very_liberal': 7,
                'no_college': 1, 'college': 4,
            },

            'Andrew': {
                'female': 4, 'male': 6,
                'age_18-29': 2, 'age_30-44': 2, 'age_45-65': 7, 'age_65+': 5,
                'hispanic': 2, 'white': 6, 'asian': 5, 'black': 0,
                'democrat': 5, 'independent': 6,
                'somewhat_liberal': 5, 'moderate': 6, 'very_liberal': 2,
                'no_college': 4, 'college': 6,
            },

            'Huynh': {
                'female': 1, 'male': 3,
                'age_18-29': 2, 'age_30-44': 2, 'age_45-65': 2, 'age_65+': 1,
                'hispanic': 4, 'white': 2, 'asian': 0, 'black': 0,
                'democrat': 2, 'independent': 1,
                'somewhat_liberal': 2, 'moderate': 1, 'very_liberal': 2,
                'no_college': 2, 'college': 2,
            },

            'Biss': {
                'female': 27, 'male': 19,
                'age_18-29': 18, 'age_30-44': 18, 'age_45-65': 19, 'age_65+': 34,
                'hispanic': 30, 'white': 26, 'asian': 11, 'black': 22,
                'democrat': 29, 'independent': 10,
                'somewhat_liberal': 29, 'moderate': 10, 'very_liberal': 18,
                'no_college': 26, 'college': 24,
            },

            'Fine': {
                'female': 17, 'male': 14,
                'age_18-29': 9, 'age_30-44': 9, 'age_45-65': 11, 'age_65+': 24,
                'hispanic': 24, 'white': 15, 'asian': 15, 'black': 7,
                'democrat': 15, 'independent': 18,
                'somewhat_liberal': 15, 'moderate': 18, 'very_liberal': 9,
                'no_college': 17, 'college': 15,
            },

            'Abughazaleh': {
                'female': 17, 'male': 19,
                'age_18-29': 30, 'age_30-44': 30, 'age_45-65': 14, 'age_65+': 9,
                'hispanic': 7, 'white': 16, 'asian': 37, 'black': 16,
                'democrat': 17, 'independent': 18,
                'somewhat_liberal': 17, 'moderate': 18, 'very_liberal': 30,
                'no_college': 11, 'college': 20,
            },

            'Simmons': {
                'female': 5, 'male': 7,
                'age_18-29': 11, 'age_30-44': 11, 'age_45-65': 6, 'age_65+': 3,
                'hispanic': 0, 'white': 7, 'asian': 0, 'black': 8,
                'democrat': 7, 'independent': 4,
                'somewhat_liberal': 7, 'moderate': 4, 'very_liberal': 11,
                'no_college': 6, 'college': 7,
            },
        },  # end crosstabs

        # =========================================================================
        # SENATE DISTRICT VOTE SHARE CROSSTABS (Q3 by SD)
        # Top-level key — separate from 'crosstabs'.
        # win_probability_simulator.py passes this through to poll_baseline.json
        # under ['current']['senate_district_crosstabs'].
        # win_probability_precinct.py reads it via get_senate_district_support().
        # =========================================================================
        'senate_district_crosstabs': {
            'sd_7': {'Amiwala': 4, 'Andrew': 1, 'Huynh': 5, 'Biss': 24, 'Fine': 6, 'Abughazaleh': 22, 'Simmons': 16,
                     'undecided': 21},
            'sd_8': {'Amiwala': 4, 'Andrew': 8, 'Huynh': 1, 'Biss': 27, 'Fine': 14, 'Abughazaleh': 15, 'Simmons': 4,
                     'undecided': 21},
            'sd_9': {'Amiwala': 7, 'Andrew': 6, 'Huynh': 0, 'Biss': 27, 'Fine': 24, 'Abughazaleh': 13, 'Simmons': 2,
                     'undecided': 17},
            'sd_other': {'Amiwala': 1, 'Andrew': 5, 'Huynh': 0, 'Biss': 19, 'Fine': 18, 'Abughazaleh': 18, 'Simmons': 2,
                         'undecided': 32},
        },

    },  # end PPP poll
{
        'name': 'Biss Internal (Nov 2025)',
        'date': '2026-02-11',
        'pollster_quality': 4,
        'sample_size': 500,
        'margin_of_error': 4.4,
        'is_internal': True,
        'internal_for': 'Biss',
        'house_effect_adjustment': house_effect,
        'pollster_id': 'Biss_Internal',
        'wave_id': 2,
        'results': {
            'Fine': 18, 'Biss': 31, 'Abughazaleh': 18,
            'Simmons': 7, 'Amiwala': 4, 'Andrew': 7, 'Huynh': 3
        },
        'undecided': 11
    },

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