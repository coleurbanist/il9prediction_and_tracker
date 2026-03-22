"""
Central Polling Data for IL-09
Update this file ONCE to reflect all scripts.
"""

# Shared constants
house_effect = 2

# Central Poll List
POLLS = [
    {# =========================================================================
        # IDENTIFICATION
        # =========================================================================
        'name': 'PPP/RoundTable March 9-10 2026',
        'date': '2026-03-10',
        'pollster_id': 'PPP',
        'sample_size': 741,
        'wave_id': 2,
        'pollster_quality': 4.5,
        'is_internal': False,
        'has_crosstabs': True,

        # =========================================================================
        # Q3 — TOPLINE VOTE SHARES
        # =========================================================================
        'results': {
            'Amiwala': 6,
            'Andrew': 7,
            'Huynh': 1,
            'Biss': 24,
            'Fine': 14,
            'Abughazaleh': 20,
            'Simmons': 10,
            'Others': 4,   # Cohen 1, Justin Ford 1, Sam Polan 0, Nick Pyati 0 → rounded ~2; report kept at 4 to match wave 1 "Others" bucket
        },
        'undecided': 17,   # "Not sure"

        # =========================================================================
        # Q4 — SECOND CHOICE TOPLINE
        # =========================================================================
        'second_choice': {
            'Amiwala': 10,
            'Andrew': 5,
            'Huynh': 2,
            'Biss': 15,
            'Fine': 8,
            'Abughazaleh': 10,
            'Simmons': 10,
            'Others': 4,   # Cohen 1, Ford 1, Polan 0, Pyati 0, Brown 0, Fredrickson 0
            'no_second': 38,
        },

        # =========================================================================
        # Q4 × Q3 — SECOND CHOICE MATRIX (by first choice)
        # Source: page 61 crosstab "Democratic Congressional Vote Second Choice"
        # Read as: row = first choice, columns = second choice
        # =========================================================================
        'second_choice_matrix': {

            'Biss': {
                'Amiwala': 10,
                'Andrew': 8,
                'Huynh': 2,
                'Fine': 23,
                'Abughazaleh': 21,
                'Simmons': 13,
                'others': 0,
                'no_second': 23,
            },

            'Abughazaleh': {
                'Amiwala': 22,
                'Andrew': 4,
                'Huynh': 5,
                'Biss': 24,
                'Fine': 6,
                'Simmons': 20,
                'others': 0,
                'no_second': 21,
            },

            'Fine': {
                'Amiwala': 5,
                'Andrew': 11,
                'Huynh': 2,
                'Biss': 39,
                'Abughazaleh': 14,
                'Simmons': 6,
                'others': 0,
                'no_second': 29,
            },

            'Simmons': {
                'Amiwala': 21,
                'Andrew': 10,
                'Huynh': 7,
                'Biss': 24,
                'Fine': 7,
                'Abughazaleh': 5,
                'others': 0,
                'no_second': 25,
            },

            'Amiwala': {
                'Andrew': 15,
                'Huynh': 3,
                'Biss': 17,
                'Fine': 2,
                'Abughazaleh': 37,
                'Simmons': 17,
                'others': 0,
                'no_second': 30,
            },

            'Andrew': {
                'Amiwala': 15,
                'Huynh': 3,
                'Biss': 17,
                'Fine': 16,
                'Abughazaleh': 10,
                'Simmons': 10,
                'others': 1,   # Phil Andrew voters' 2nd choice includes "Phil Andrew 30" which is self — likely a data artifact; using residual
                'no_second': 27,
            },

            'Huynh': {
                'Amiwala': 0,
                'Andrew': 0,
                'Biss': 29,
                'Fine': 26,
                'Abughazaleh': 14,
                'Simmons': 23,
                'others': 0,
                'no_second': 27,
            },
        },

        # =========================================================================
        # Q6–Q15 — FAVORABILITY RATINGS (topline only; full crosstabs below)
        # =========================================================================
        'favorability': {

            'Amiwala': {
                'overall': {'favorable': 35, 'unfavorable': 9, 'not_heard': 39, 'not_sure': 17},
                'by_gender': {
                    'woman': {'favorable': 36, 'unfavorable': 8, 'not_heard': 37, 'not_sure': 19},
                    'man':   {'favorable': 34, 'unfavorable': 8, 'not_heard': 41, 'not_sure': 16},
                },
                'by_age': {
                    'age_18_45': {'favorable': 55, 'unfavorable': 10, 'not_heard': 27, 'not_sure': 9},
                    'age_46_65': {'favorable': 37, 'unfavorable': 8,  'not_heard': 40, 'not_sure': 16},
                    'age_65plus': {'favorable': 18, 'unfavorable': 10, 'not_heard': 48, 'not_sure': 24},
                },
                'by_race': {
                    'hispanic': {'favorable': 35, 'unfavorable': 14, 'not_heard': 44, 'not_sure': 8},
                    'white':    {'favorable': 35, 'unfavorable': 8,  'not_heard': 40, 'not_sure': 17},
                    'asian':    {'favorable': 62, 'unfavorable': 13, 'not_heard': 20, 'not_sure': 4},
                    'black':    {'favorable': 25, 'unfavorable': 10, 'not_heard': 33, 'not_sure': 33},
                    'other':    {'favorable': 30, 'unfavorable': 15, 'not_heard': 47, 'not_sure': 8},
                },
                'by_party': {
                    'democrat':    {'favorable': 38, 'unfavorable': 6,  'not_heard': 39, 'not_sure': 17},
                    'independent': {'favorable': 31, 'unfavorable': 15, 'not_heard': 39, 'not_sure': 14},
                },
                'by_senate_district': {
                    'sd7': {'favorable': 45, 'unfavorable': 4,  'not_heard': 38, 'not_sure': 13},
                    'sd8': {'favorable': 42, 'unfavorable': 12, 'not_heard': 32, 'not_sure': 14},
                    'sd9': {'favorable': 33, 'unfavorable': 13, 'not_heard': 36, 'not_sure': 19},
                },
            },

            'Biss': {
                'overall': {'favorable': 50, 'unfavorable': 31, 'not_heard': 7, 'not_sure': 13},
                'by_gender': {
                    'woman': {'favorable': 54, 'unfavorable': 27, 'not_heard': 7,  'not_sure': 12},
                    'man':   {'favorable': 46, 'unfavorable': 33, 'not_heard': 6,  'not_sure': 14},
                },
                'by_age': {
                    'age_18_45':  {'favorable': 47, 'unfavorable': 36, 'not_heard': 5,  'not_sure': 12},
                    'age_46_65':  {'favorable': 46, 'unfavorable': 35, 'not_heard': 9,  'not_sure': 10},
                    'age_65plus': {'favorable': 56, 'unfavorable': 21, 'not_heard': 7,  'not_sure': 16},
                },
                'by_race': {
                    'hispanic': {'favorable': 49, 'unfavorable': 44, 'not_heard': 5,  'not_sure': 2},
                    'white':    {'favorable': 53, 'unfavorable': 27, 'not_heard': 6,  'not_sure': 14},
                    'asian':    {'favorable': 36, 'unfavorable': 50, 'not_heard': 14, 'not_sure': 0},
                    'black':    {'favorable': 44, 'unfavorable': 23, 'not_heard': 10, 'not_sure': 23},
                    'other':    {'favorable': 29, 'unfavorable': 45, 'not_heard': 11, 'not_sure': 15},
                },
                'by_party': {
                    'democrat':    {'favorable': 55, 'unfavorable': 26, 'not_heard': 5,  'not_sure': 13},
                    'independent': {'favorable': 33, 'unfavorable': 41, 'not_heard': 15, 'not_sure': 11},
                },
                'by_senate_district': {
                    'sd7': {'favorable': 51, 'unfavorable': 32, 'not_heard': 7,  'not_sure': 10},
                    'sd8': {'favorable': 47, 'unfavorable': 31, 'not_heard': 9,  'not_sure': 13},
                    'sd9': {'favorable': 49, 'unfavorable': 36, 'not_heard': 7,  'not_sure': 8},
                },
            },

            'Fine': {
                # Wave 2 major shift: unfavorable surges to 50% (was 35% in wave 1)
                'overall': {'favorable': 28, 'unfavorable': 50, 'not_heard': 6, 'not_sure': 16},
                'by_gender': {
                    'woman': {'favorable': 31, 'unfavorable': 47, 'not_heard': 4,  'not_sure': 19},
                    'man':   {'favorable': 26, 'unfavorable': 53, 'not_heard': 7,  'not_sure': 14},
                },
                'by_age': {
                    'age_18_45':  {'favorable': 18, 'unfavorable': 66, 'not_heard': 5,  'not_sure': 11},
                    'age_46_65':  {'favorable': 27, 'unfavorable': 50, 'not_heard': 7,  'not_sure': 16},
                    'age_65plus': {'favorable': 38, 'unfavorable': 36, 'not_heard': 4,  'not_sure': 22},
                },
                'by_race': {
                    'hispanic': {'favorable': 17, 'unfavorable': 61, 'not_heard': 8,  'not_sure': 14},
                    'white':    {'favorable': 30, 'unfavorable': 48, 'not_heard': 5,  'not_sure': 17},
                    'asian':    {'favorable': 15, 'unfavorable': 61, 'not_heard': 14, 'not_sure': 10},
                    'black':    {'favorable': 31, 'unfavorable': 47, 'not_heard': 3,  'not_sure': 19},
                    'other':    {'favorable': 26, 'unfavorable': 49, 'not_heard': 9,  'not_sure': 16},
                },
                'by_party': {
                    'democrat':    {'favorable': 29, 'unfavorable': 49, 'not_heard': 5,  'not_sure': 18},
                    'independent': {'favorable': 26, 'unfavorable': 52, 'not_heard': 9,  'not_sure': 13},
                },
                'by_senate_district': {
                    'sd7': {'favorable': 20, 'unfavorable': 61, 'not_heard': 6,  'not_sure': 13},
                    'sd8': {'favorable': 29, 'unfavorable': 47, 'not_heard': 6,  'not_sure': 18},
                    'sd9': {'favorable': 37, 'unfavorable': 44, 'not_heard': 4,  'not_sure': 15},
                },
                # Fine: unfavorable nearly doubled wave-over-wave (35%→50%).
                # Young voters (18-45) now 66% unfavorable. Broadly negative across all subgroups.
            },

            'Abughazaleh': {
                'overall': {'favorable': 39, 'unfavorable': 34, 'not_heard': 10, 'not_sure': 17},
                'by_gender': {
                    'woman': {'favorable': 34, 'unfavorable': 36, 'not_heard': 12, 'not_sure': 18},
                    'man':   {'favorable': 47, 'unfavorable': 31, 'not_heard': 8,  'not_sure': 14},
                },
                'by_age': {
                    'age_18_45':  {'favorable': 47, 'unfavorable': 39, 'not_heard': 5,  'not_sure': 10},
                    'age_46_65':  {'favorable': 40, 'unfavorable': 37, 'not_heard': 11, 'not_sure': 12},
                    'age_65plus': {'favorable': 33, 'unfavorable': 26, 'not_heard': 14, 'not_sure': 27},
                },
                'by_race': {
                    'hispanic': {'favorable': 44, 'unfavorable': 40, 'not_heard': 10, 'not_sure': 6},
                    'white':    {'favorable': 41, 'unfavorable': 34, 'not_heard': 10, 'not_sure': 15},
                    'asian':    {'favorable': 32, 'unfavorable': 34, 'not_heard': 9,  'not_sure': 25},
                    'black':    {'favorable': 27, 'unfavorable': 24, 'not_heard': 14, 'not_sure': 35},
                    'other':    {'favorable': 45, 'unfavorable': 38, 'not_heard': 5,  'not_sure': 11},
                },
                'by_party': {
                    'democrat':    {'favorable': 41, 'unfavorable': 32, 'not_heard': 9,  'not_sure': 18},
                    'independent': {'favorable': 37, 'unfavorable': 39, 'not_heard': 14, 'not_sure': 10},
                },
                'by_senate_district': {
                    'sd7': {'favorable': 43, 'unfavorable': 33, 'not_heard': 10, 'not_sure': 15},
                    'sd8': {'favorable': 44, 'unfavorable': 37, 'not_heard': 5,  'not_sure': 14},
                    'sd9': {'favorable': 33, 'unfavorable': 37, 'not_heard': 9,  'not_sure': 21},
                },
            },

            'Simmons': {
                'overall': {'favorable': 35, 'unfavorable': 6, 'not_heard': 40, 'not_sure': 18},
                'by_gender': {
                    'woman': {'favorable': 36, 'unfavorable': 6, 'not_heard': 38, 'not_sure': 20},
                    'man':   {'favorable': 35, 'unfavorable': 6, 'not_heard': 45, 'not_sure': 15},
                },
                'by_age': {
                    'age_18_45':  {'favorable': 49, 'unfavorable': 8,  'not_heard': 29, 'not_sure': 14},
                    'age_46_65':  {'favorable': 33, 'unfavorable': 8,  'not_heard': 43, 'not_sure': 16},
                    'age_65plus': {'favorable': 26, 'unfavorable': 4,  'not_heard': 48, 'not_sure': 23},
                },
                'by_race': {
                    'hispanic': {'favorable': 38, 'unfavorable': 18, 'not_heard': 34, 'not_sure': 10},
                    'white':    {'favorable': 37, 'unfavorable': 5,  'not_heard': 41, 'not_sure': 16},
                    'asian':    {'favorable': 33, 'unfavorable': 9,  'not_heard': 26, 'not_sure': 33},
                    'black':    {'favorable': 25, 'unfavorable': 3,  'not_heard': 47, 'not_sure': 25},
                    'other':    {'favorable': 27, 'unfavorable': 7,  'not_heard': 43, 'not_sure': 23},
                },
                'by_party': {
                    'democrat':    {'favorable': 38, 'unfavorable': 4,  'not_heard': 40, 'not_sure': 18},
                    'independent': {'favorable': 26, 'unfavorable': 13, 'not_heard': 47, 'not_sure': 14},
                },
                'by_senate_district': {
                    'sd7': {'favorable': 61, 'unfavorable': 9,  'not_heard': 19, 'not_sure': 10},
                    'sd8': {'favorable': 35, 'unfavorable': 1,  'not_heard': 43, 'not_sure': 20},
                    'sd9': {'favorable': 31, 'unfavorable': 4,  'not_heard': 46, 'not_sure': 19},
                },
                # Simmons: very clean fav/unfav (35/6 = +29 net). SD7 outlier at 61% favorable.
                # Jumped from 6% to 10% vote share wave-over-wave.
            },

            'Andrew': {
                'overall': {'favorable': 24, 'unfavorable': 15, 'not_heard': 39, 'not_sure': 22},
                'by_gender': {
                    'woman': {'favorable': 23, 'unfavorable': 15, 'not_heard': 37, 'not_sure': 24},
                    'man':   {'favorable': 26, 'unfavorable': 12, 'not_heard': 42, 'not_sure': 19},
                },
                'by_age': {
                    'age_18_45':  {'favorable': 16, 'unfavorable': 25, 'not_heard': 41, 'not_sure': 19},
                    'age_46_65':  {'favorable': 31, 'unfavorable': 12, 'not_heard': 37, 'not_sure': 21},
                    'age_65plus': {'favorable': 26, 'unfavorable': 8,  'not_heard': 41, 'not_sure': 25},
                },
                'by_race': {
                    'hispanic': {'favorable': 11, 'unfavorable': 17, 'not_heard': 49, 'not_sure': 23},
                    'white':    {'favorable': 27, 'unfavorable': 12, 'not_heard': 37, 'not_sure': 24},
                    'asian':    {'favorable': 25, 'unfavorable': 25, 'not_heard': 31, 'not_sure': 19},
                    'black':    {'favorable': 9,  'unfavorable': 29, 'not_heard': 56, 'not_sure': 6},
                    'other':    {'favorable': 35, 'unfavorable': 7,  'not_heard': 34, 'not_sure': 24},
                },
                'by_party': {
                    'democrat':    {'favorable': 25, 'unfavorable': 14, 'not_heard': 38, 'not_sure': 23},
                    'independent': {'favorable': 20, 'unfavorable': 13, 'not_heard': 49, 'not_sure': 18},
                },
                'by_senate_district': {
                    'sd7': {'favorable': 15, 'unfavorable': 16, 'not_heard': 49, 'not_sure': 20},
                    'sd8': {'favorable': 29, 'unfavorable': 16, 'not_heard': 29, 'not_sure': 25},
                    'sd9': {'favorable': 34, 'unfavorable': 16, 'not_heard': 29, 'not_sure': 22},
                },
            },

            'Huynh': {
                'overall': {'favorable': 21, 'unfavorable': 10, 'not_heard': 45, 'not_sure': 24},
                'by_gender': {
                    'woman': {'favorable': 20, 'unfavorable': 8,  'not_heard': 44, 'not_sure': 28},
                    'man':   {'favorable': 24, 'unfavorable': 10, 'not_heard': 46, 'not_sure': 21},
                },
                'by_age': {
                    'age_18_45':  {'favorable': 32, 'unfavorable': 14, 'not_heard': 35, 'not_sure': 19},
                    'age_46_65':  {'favorable': 18, 'unfavorable': 9,  'not_heard': 53, 'not_sure': 19},
                    'age_65plus': {'favorable': 15, 'unfavorable': 6,  'not_heard': 47, 'not_sure': 32},
                },
                'by_race': {
                    'hispanic': {'favorable': 23, 'unfavorable': 6,  'not_heard': 51, 'not_sure': 20},
                    'white':    {'favorable': 22, 'unfavorable': 7,  'not_heard': 42, 'not_sure': 29},
                    'asian':    {'favorable': 29, 'unfavorable': 24, 'not_heard': 41, 'not_sure': 6},
                    'black':    {'favorable': 9,  'unfavorable': 19, 'not_heard': 66, 'not_sure': 5},
                    'other':    {'favorable': 21, 'unfavorable': 12, 'not_heard': 50, 'not_sure': 18},
                },
                'by_party': {
                    'democrat':    {'favorable': 23, 'unfavorable': 8,  'not_heard': 43, 'not_sure': 26},
                    'independent': {'favorable': 14, 'unfavorable': 10, 'not_heard': 58, 'not_sure': 18},
                },
                'by_senate_district': {
                    'sd7': {'favorable': 35, 'unfavorable': 9,  'not_heard': 34, 'not_sure': 22},
                    'sd8': {'favorable': 24, 'unfavorable': 12, 'not_heard': 45, 'not_sure': 19},
                    'sd9': {'favorable': 10, 'unfavorable': 11, 'not_heard': 49, 'not_sure': 29},
                },
            },
        },

        # =========================================================================
        # VOTE SHARE CROSSTABS  (Q3 by demographic subgroup)
        # =========================================================================
        'crosstab_sample_sizes': {
            'female': 385,       # 52% of 741
            'male': 289,         # 39% of 741
            'gender_nonbinary': 15,
            'age_18-45': 222,    # 30% of 741
            'age_46-65': 245,    # 33% of 741
            'age_65+': 274,      # 37% of 741
            'hispanic': 67,      # 9%
            'white': 526,        # 71%
            'asian': 44,         # 6%
            'black': 67,         # 9%
            'other': 37,         # 5%
            'democrat': 578,     # 78%
            'independent': 133,  # 18%
            'hs_or_less': 30,    # 4%
            'some_college': 141, # 19%
            'college_2yr': 52,   # 7%
            'college_4yr': 259,  # 35%
            'postgrad': 259,     # 35%
            'sd7': 215,          # 29%
            'sd8': 126,          # 17%
            'sd9': 222,          # 30%
            'landline': 44,      # 6%
            'text': 697,         # 94%
        },

        'crosstabs': {

            'Amiwala': {
                'female': 6, 'male': 8,
                'age_18-45': 13, 'age_45-65': 6, 'age_65+': 1,
                'hispanic': 7, 'white': 4, 'asian': 39, 'black': 0,
                'democrat': 7, 'independent': 5,
                'very_liberal': None, 'somewhat_liberal': None, 'moderate': None,  # not broken out in wave 2
                'no_college': None, 'college': None,
            },

            'Andrew': {
                'female': 6, 'male': 8,
                'age_18-45': 5, 'age_45-65': 10, 'age_65+': 6,
                'hispanic': 0, 'white': 7, 'asian': 12, 'black': 3,
                'democrat': 6, 'independent': 8,
                'no_college': None, 'college': None,
            },

            'Huynh': {
                'female': 1, 'male': 2,
                'age_18-45': 1, 'age_45-65': 1, 'age_65+': 1,
                'hispanic': 2, 'white': 1, 'asian': 0, 'black': 0,
                'democrat': 2, 'independent': 0,
                'no_college': None, 'college': None,
            },

            'Biss': {
                'female': 28, 'male': 21,
                'age_18-45': 18, 'age_45-65': 23, 'age_65+': 30,
                'hispanic': 19, 'white': 27, 'asian': 9, 'black': 22,
                'democrat': 28, 'independent': 10,
                'no_college': None, 'college': None,
            },

            'Fine': {
                'female': 15, 'male': 12,
                'age_18-45': 8, 'age_45-65': 11, 'age_65+': 21,
                'hispanic': 9, 'white': 15, 'asian': 5, 'black': 14,
                'democrat': 14, 'independent': 12,
                'no_college': None, 'college': None,
            },

            'Abughazaleh': {
                'female': 12, 'male': 29,
                'age_18-45': 34, 'age_45-65': 17, 'age_65+': 11,
                'hispanic': 18, 'white': 21, 'asian': 21, 'black': 11,
                'democrat': 19, 'independent': 26,
                'no_college': None, 'college': None,
            },

            'Simmons': {
                'female': 12, 'male': 7,
                'age_18-45': 13, 'age_45-65': 8, 'age_65+': 9,
                'hispanic': 8, 'white': 10, 'asian': 4, 'black': 20,
                'democrat': 10, 'independent': 7,
                'no_college': None, 'college': None,
            },
        },  # end crosstabs

        # =========================================================================
        # ISSUE PRIORITY (Q5) — new in wave 2
        # =========================================================================
        'issue_priority': {
            'inflation_cost_of_living': 17,
            'healthcare': 10,
            'education': 1,
            'jobs_economy': 8,
            'affordable_housing': 2,
            'immigration_ice': 6,
            'threats_to_democracy': 46,
            'israel_palestine': 6,
            'something_else_not_sure': 4,
        },

        # =========================================================================
        # TRUMP APPROVAL (Q1) — new in wave 2
        # =========================================================================
        'trump_approval': {
            'approve': 7,
            'disapprove': 91,
            'not_sure': 2,
        },
        'senate_district_crosstabs': {
            'sd_7': {'Amiwala': 7, 'Andrew': 1, 'Huynh': 3, 'Biss': 19, 'Fine': 9, 'Abughazaleh': 24, 'Simmons': 19,
                     'undecided': 15},
            'sd_8': {'Amiwala': 13, 'Andrew': 10, 'Huynh': 0, 'Biss': 21, 'Fine': 12, 'Abughazaleh': 22, 'Simmons': 10,
                     'undecided': 11},
            'sd_9': {'Amiwala': 3, 'Andrew': 11, 'Huynh': 0, 'Biss': 31, 'Fine': 17, 'Abughazaleh': 13, 'Simmons': 6,
                     'undecided': 16},
            'sd_other': {'Amiwala': 5, 'Andrew': 6, 'Huynh': 2, 'Biss': 20, 'Fine': 17, 'Abughazaleh': 22, 'Simmons': 2,
                         'undecided': 24},
        },},
    {
        # =========================================================================
        # IDENTIFICATION
        # =========================================================================
        'name': 'PPP/RoundTable Feb 20-21 2026',
        'date': '2026-02-21',
        'pollster_id': 'PPP',
        'sample_size': 501,
        'wave_id': 1,
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