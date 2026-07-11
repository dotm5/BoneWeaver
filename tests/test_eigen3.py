from __future__ import annotations

import unittest

from ue_chain_prep.core.eigen3 import jacobi_eigen_symmetric_3x3


class Eigen3Tests(unittest.TestCase):
    def test_diagonal_matrix_is_sorted_descending(self) -> None:
        values, vectors = jacobi_eigen_symmetric_3x3(((1.0, 0.0, 0.0), (0.0, 3.0, 0.0), (0.0, 0.0, 2.0)))
        self.assertEqual(values, (3.0, 2.0, 1.0))
        self.assertEqual(vectors[0], (0.0, 1.0, 0.0))

    def test_vectors_satisfy_eigen_equation_and_are_orthogonal(self) -> None:
        matrix = ((4.0, 1.0, 2.0), (1.0, 3.0, 0.5), (2.0, 0.5, 2.0))
        values, vectors = jacobi_eigen_symmetric_3x3(matrix)
        for value, vector in zip(values, vectors):
            product = tuple(sum(matrix[row][column] * vector[column] for column in range(3)) for row in range(3))
            residual = max(abs(product[index] - value * vector[index]) for index in range(3))
            self.assertLessEqual(residual, 1.0e-6)
        for first in range(3):
            for second in range(first + 1, 3):
                self.assertLessEqual(abs(sum(vectors[first][i] * vectors[second][i] for i in range(3))), 1.0e-6)

    def test_zero_and_repeated_matrices_are_deterministic(self) -> None:
        matrix = ((2.0, 0.0, 0.0), (0.0, 2.0, 0.0), (0.0, 0.0, 0.0))
        first = jacobi_eigen_symmetric_3x3(matrix)
        self.assertEqual(first, jacobi_eigen_symmetric_3x3(matrix))
        self.assertEqual(jacobi_eigen_symmetric_3x3(((0.0, 0.0, 0.0),) * 3)[0], (0.0, 0.0, 0.0))


if __name__ == "__main__":
    unittest.main()
