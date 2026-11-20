"""Bank fixed effects, pooled OLS, and leave-one-bank-out sensitivity."""

import math

import numpy as np
import statsmodels.formula.api as smf

from .model import select_basis

REGRESSORS = ["writeoff_ratio", "delta_g2_ratio", "loan_growth", "lagged_coverage"]


def _finite(value):
    return float(value) if math.isfinite(value) else None


def _fit(data, *, fixed_effects):
    n_banks = data["bank"].nunique()
    result = dict(n=len(data), n_banks=n_banks, covariance="cluster_bank", r2=None, coefficients={})
    terms = REGRESSORS + (["C(bank)"] if fixed_effects else [])
    if n_banks < 2 or len(data) <= len(REGRESSORS) + (n_banks if fixed_effects else 1):
        return dict(result, status="insufficient_data")
    model = smf.ols("delta_npl_ratio_pp ~ " + " + ".join(terms), data=data)
    if np.linalg.matrix_rank(model.exog) < model.exog.shape[1]:
        return dict(result, status="rank_deficient")
    fit = model.fit(cov_type="cluster", cov_kwds={"groups": data["bank"]}, use_t=True)
    intervals = fit.conf_int(alpha=.05)
    return dict(
        result, status="ok", r2=_finite(fit.rsquared),
        coefficients={
            term: {
                "estimate": _finite(estimate),
                "std_error": _finite(fit.bse[term]),
                "ci_95": [_finite(bound) for bound in intervals.loc[term]],
            }
            for term, estimate in fit.params.items()
        },
    )


def run_regressions(credit, *, basis="consolidated"):
    """Use the same complete cases for pooled and fixed-effects models."""
    selected = select_basis(credit, basis)
    fields = ["bank_code", "delta_npl_ratio"] + REGRESSORS
    panel = selected[fields].replace([np.inf, -np.inf], np.nan).dropna().rename(columns={"bank_code": "bank"})
    panel["bank"] = panel["bank"].astype(str)
    panel["delta_npl_ratio_pp"] = 100 * panel.pop("delta_npl_ratio")
    return {
        "basis": basis,
        "excluded_incomplete": len(selected) - len(panel),
        "sample_note": {
            "vi": "Ngay cả với mẫu dự kiến gồm 8 ngân hàng × 5 thay đổi theo quý (n = 40), "
                  "kết quả chỉ gợi ý xu hướng.",
            "en": "Even with the planned 8 banks × 5 quarterly changes (n = 40), "
                  "the results only suggest a trend.",
        },
        "fixed_effects": _fit(panel, fixed_effects=True),
        "pooled": _fit(panel, fixed_effects=False),
        "leave_one_bank_out": {
            bank: _fit(panel.loc[panel["bank"].ne(bank)], fixed_effects=True)
            for bank in sorted(panel["bank"].unique())
        },
    }
