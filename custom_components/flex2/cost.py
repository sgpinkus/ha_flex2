"""
cost.py — HLQuadraticCost and closed-form solver.
No HA dependency; importable and testable standalone.
"""
from __future__ import annotations
import numpy as np


class HLQuadraticCost:
    """
    Quadratic cost over r ∈ [0, 1], parameterised by derivative values
    at the bounds:

        cost'(0) = p_l
        cost'(1) = p_h

    Convex when p_h > p_l.
    Load-device convention: p_l < p_h < 0.
    """

    def __init__(self, p_l: float, p_h: float) -> None:
        self.p_l = p_l
        self.p_h = p_h
        self.x_l = 0.0
        self.x_h = 1.0
        self._cost_fn = lambda x: np.vectorize(
            HLQuadraticCost._cost, otypes=[float]
        )(x, self.p_l, self.p_h, self.x_l, self.x_h)
        self._deriv_fn = lambda x: np.vectorize(
            HLQuadraticCost._deriv, otypes=[float]
        )(np.array(x).reshape(-1), self.p_l, self.p_h, self.x_l, self.x_h)
        self._hess_fn = lambda x: np.diag(np.vectorize(
            HLQuadraticCost._hess, otypes=[float]
        )(np.array(x).reshape(-1), self.p_l, self.p_h, self.x_l, self.x_h))

    def __call__(self, r: float) -> float:
        return float(self._cost_fn(r).sum())

    def __repr__(self) -> str:
        return f"HLQuadraticCost(p_l={self.p_l}, p_h={self.p_h})"

    def deriv(self, x):
        return self._deriv_fn(x)

    def hess(self, x):
        return self._hess_fn(x)

    @staticmethod
    def _cost(x, p_l, p_h, x_l, x_h):
        if x_l == x_h:
            return 0.0
        b = p_l
        a = (p_h - p_l) / 2
        c = a * (-b / (2 * a)) ** 2 + b * (-b / (2 * a))
        return (x_h - x_l) * np.poly1d([a, b, 0])((x - x_l) / (x_h - x_l)) - c * (x_h - x_l)

    @staticmethod
    def _deriv(x, p_l, p_h, x_l, x_h):
        if x_l == x_h:
            return 0.0
        return (p_h - p_l) * ((x - x_l) / (x_h - x_l)) + p_l

    @staticmethod
    def _hess(x, p_l, p_h, x_l, x_h):
        if x_l == x_h:
            return 0.0
        return (p_h - p_l) / (x_h - x_l)


def solve(lam: float, cost_fn: HLQuadraticCost, n_curve: int = 51) -> dict:
    """
    Closed-form solution for r* = argmin_r { λ·r + cost(r) }, r ∈ [0, 1].

    KKT stationarity:  λ + cost'(r*) = 0
    With cost'(r) = (p_h - p_l)·r + p_l:
        r* = -(λ + p_l) / (p_h - p_l)   [clipped to [0, 1]]
    """
    p_l, p_h = cost_fn.p_l, cost_fn.p_h

    if p_h == p_l:
        r_opt = 0.0 if lam >= -p_l else 1.0
        regime = "degenerate"
    else:
        r_unc = -(lam + p_l) / (p_h - p_l)
        r_opt = float(np.clip(r_unc, 0.0, 1.0))
        regime = "at_min" if r_unc <= 0 else "at_max" if r_unc >= 1 else "interior"

    xs = np.linspace(0.0, 1.0, n_curve)
    cost_vals   = [float(cost_fn(float(r))) for r in xs]
    energy_vals = [lam * float(r) for r in xs]
    total_vals  = [c + e for c, e in zip(cost_vals, energy_vals)]

    return {
        "r_opt":        round(r_opt, 4),
        "regime":       regime,
        "lambda":       round(lam, 4),
        "p_l":          p_l,
        "p_h":          p_h,
        "curve_xs":     [round(float(v), 4) for v in xs],
        "curve_cost":   [round(v, 4) for v in cost_vals],
        "curve_energy": [round(v, 4) for v in energy_vals],
        "curve_total":  [round(v, 4) for v in total_vals],
    }