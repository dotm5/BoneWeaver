"""Dependency-free deterministic Jacobi eigensolver for symmetric 3x3 matrices."""

from __future__ import annotations

import math


def _stable_unit(vector):
    length = math.sqrt(sum(value * value for value in vector))
    if length <= 1.0e-30:
        return (1.0, 0.0, 0.0)
    result = tuple(value / length for value in vector)
    pivot = max(range(3), key=lambda index: (abs(result[index]), -index))
    return tuple(-value for value in result) if result[pivot] < 0.0 else result


def jacobi_eigen_symmetric_3x3(matrix, *, max_iterations=32, tolerance=1.0e-14):
    a = [[float(matrix[row][column]) for column in range(3)] for row in range(3)]
    for row in range(3):
        for column in range(3):
            if not math.isfinite(a[row][column]):
                raise ValueError("matrix must be finite")
            if abs(a[row][column] - a[column][row]) > 1.0e-12:
                raise ValueError("matrix must be symmetric")
    v = [[1.0 if row == column else 0.0 for column in range(3)] for row in range(3)]
    for _ in range(max_iterations):
        p, q = max(((0, 1), (0, 2), (1, 2)), key=lambda pair: abs(a[pair[0]][pair[1]]))
        apq = a[p][q]
        if abs(apq) <= tolerance:
            break
        tau = (a[q][q] - a[p][p]) / (2.0 * apq)
        t = (1.0 if tau >= 0.0 else -1.0) / (abs(tau) + math.sqrt(1.0 + tau * tau))
        c = 1.0 / math.sqrt(1.0 + t * t)
        s = t * c
        app, aqq = a[p][p], a[q][q]
        a[p][p] = app - t * apq
        a[q][q] = aqq + t * apq
        a[p][q] = a[q][p] = 0.0
        for r in range(3):
            if r in (p, q):
                continue
            arp, arq = a[r][p], a[r][q]
            a[r][p] = a[p][r] = c * arp - s * arq
            a[r][q] = a[q][r] = s * arp + c * arq
        for r in range(3):
            vrp, vrq = v[r][p], v[r][q]
            v[r][p] = c * vrp - s * vrq
            v[r][q] = s * vrp + c * vrq
    pairs = [(a[index][index], _stable_unit(tuple(v[row][index] for row in range(3)))) for index in range(3)]
    pairs.sort(key=lambda pair: (-pair[0], pair[1]))
    return tuple(pair[0] for pair in pairs), tuple(pair[1] for pair in pairs)
