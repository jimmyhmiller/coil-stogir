"""Independent diagnostic solve of expected visits from native static odds.

Dense partial-pivot elimination serves as an oracle for the library's sparse
M-matrix elimination. Neither implementation consumes measured profile data.
"""
from collections import defaultdict


def read_probabilities(path):
    result = {}
    for line in path.read_text().splitlines():
        row = line.split()
        if row[:2] == ['frequency', 'edge']:
            a, b, weight = map(int, row[2:])
            assert (a, b) not in result, 'diagnostic trace needs unique source/target pairs'
            result[a, b] = weight
    assert result, 'missing native branch probabilities'
    totals = defaultdict(int)
    for (a, b), weight in result.items():
        totals[a] += weight
    return {edge: weight/totals[edge[0]] for edge, weight in result.items()}


def expected_visits(refs, edges, entry):
    count = len(refs)
    index = {ref: i for i, ref in enumerate(refs)}
    matrix = [[float(i == j) for j in range(count)]+[float(refs[i] == entry)]
              for i in range(count)]
    for (source, target), probability in edges.items():
        matrix[index[target]][index[source]] -= probability
    original = [row[:] for row in matrix]
    for col in range(count):
        pivot = max(range(col, count), key=lambda row: abs(matrix[row][col]))
        matrix[col], matrix[pivot] = matrix[pivot], matrix[col]
        assert abs(matrix[col][col]) > 1e-12, 'non-finite or ill-conditioned flow system'
        divisor = matrix[col][col]
        matrix[col] = [value/divisor for value in matrix[col]]
        for row in range(count):
            if row == col:
                continue
            factor = matrix[row][col]
            if factor:
                matrix[row] = [x-factor*y for x, y in zip(matrix[row], matrix[col])]
    values = [row[-1] for row in matrix]
    assert min(values) >= -1e-9
    residual = max(abs(sum(x*y for x, y in zip(row, values))-row[-1]) for row in original)
    assert residual < 1e-8, residual
    return dict(zip(refs, values)), residual


def apply_weights(model, probabilities, scale=10000):
    refs = [model.nodes[block[0]][0] for block in model.blocks]
    frequencies, residual = expected_visits(refs, probabilities, refs[0])
    result = []
    for a, b, weight, kind, site in model.transfers:
        if kind == 'edge':
            source, target = model.edges[site]
            weight = frequencies[source]*probabilities[source, target]
        else:
            weight = frequencies[refs[model.parts[b].block]]
        result.append((a, b, max(1, round(weight*scale)), kind, site))
    model.transfers = result
    return frequencies, residual
