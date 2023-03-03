import math


def edit_dist(
        observed: str,
        expected: str,
        GAP='~',
        MATCH=1,
        SUB=-1,
        GAP_OPEN=-3,
        GAP_EXTEND=-1
):
    """
    Align seq1 against seq2 using Needleman-Wunsch
    Put seq1 on left (j) and seq2 on top (i)
    => matrix[i][j]
    """

    def get_i_j(len_i, len_j):
        for ii in range(len_i):
            for jj in range(len_j):
                yield ii, jj

    len1 = len(observed)
    len2 = len(expected)

    score_matrix = {}
    path_matrix = {}

    # Initialize base cases
    score_matrix[0, 0] = 0
    path_matrix[0, 0] = (-1, -1)

    score_matrix[0, 1] = GAP_OPEN + GAP_EXTEND
    path_matrix[0, 1] = (0, 0)

    score_matrix[1, 0] = GAP_OPEN + GAP_EXTEND
    path_matrix[1, 0] = (0, 0)

    for i in range(2, len2 + 1):
        score_matrix[i, 0] = score_matrix[i - 1, 0] + GAP_EXTEND
        path_matrix[i, 0] = (i - 1, 0)

    for j in range(2, len1 + 1):
        score_matrix[0, j] = score_matrix[0, j - 1] + GAP_EXTEND
        path_matrix[0, j] = (0, j - 1)

    # Fill in!
    ij = get_i_j(len2, len1)
    for i, j in ij:
        si = i
        i += 1  # adjust for extra row at beginning of matrix
        sj = j
        j += 1  # adjust for extra column at beginning of matrix
        # Which of the three paths is best?
        match = score_matrix[i - 1, j - 1] \
                + (MATCH if observed[sj] == expected[si] else SUB)
        gap_i = score_matrix.get((i - 1, j), math.inf) \
                + GAP_EXTEND \
                + (GAP_OPEN if path_matrix[(i - 1, j)] != (i - 2, j) else 0)
        gap_j = score_matrix.get((i, j - 1), math.inf) \
                + GAP_EXTEND \
                + (GAP_OPEN if path_matrix[(i, j - 1)] != (i, j - 2) else 0)

        # Break ties using left (gap in i), top (gap in j), and diagonal
        if gap_i >= match and gap_i >= gap_j:
            score = gap_i
            path = (i - 1, j)
        elif gap_j >= match:
            score = gap_j
            path = (i, j - 1)
        else:
            score = match
            path = (i - 1, j - 1)

        score_matrix[i, j] = score
        path_matrix[i, j] = path

    # Extract path
    align_path = [(len2, len1)]
    while align_path[-1] != (0, 0):
        prev = align_path[-1]
        align_path.append(path_matrix[prev])
    align_path = list(reversed(align_path))

    # Interpret alignment
    align1 = ''
    align2 = ''
    a1 = 0
    a2 = 0
    for (pi, pj), (ci, cj) in zip(align_path[:-1], align_path[1:]):
        # Is the move a match, gap1, or gap2?
        di = ci - pi
        dj = cj - pj
        if di == 1 and dj == 1:  # match
            align1 += observed[a1]
            a1 += 1
            align2 += expected[a2]
            a2 += 1
        elif di == 1:  # gap1 -> took from seq2, but not seq1
            align1 += GAP
            align2 += expected[a2]
            a2 += 1
        else:  # gap2 -> took from seq1, but not seq2
            align1 += observed[a1]
            a1 += 1
            align2 += GAP

    return score_matrix[len2, len1], align1, align2
