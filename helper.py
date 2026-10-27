# -*- coding: utf-8 -*-
"""
LEGACY MODULE — not used anywhere in the application.

This module previously contained a duplicate, ad-hoc implementation of the AHP
priority-vector and consistency-ratio calculations. All CR calculations in the
application now go through `ahp.py::Compare`, which uses the Donegan & Dodd (1991)
random-index table with linear interpolation — the same table and formula used
by the questionnaire's in-browser CR preview (see smtQuestionnaire.py).

The old `consistency_check()` function used Saaty's classic random-index table
(constants.py::random_index), which only covers n=1..12 and raised an
UnboundLocalError for n>12. It is removed here to avoid that latent bug being
reactivated by accident.

If a reference to the original cyclic-coordinates total/normalization/weight
helpers is needed, see ahp.py::Compare._compute_priority_vector and
ahp.py::Compare._compute_consistency_ratio, which are the canonical
implementations used throughout SMART.
"""
