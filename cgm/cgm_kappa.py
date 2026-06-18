"""Linear-weighted Cohen's kappa for 1-5 rubric scores, with the explicit
degeneracy rule from the design spec: zero expected disagreement (both raters
constant at the same category) makes kappa undefined -> return None; the caller
treats None + 100% raw agreement as a gate PASS reported 'N/A (degenerate)'."""

CATEGORIES = (1, 2, 3, 4, 5)


def linear_weighted_kappa(a, b, categories=CATEGORIES):
    if len(a) != len(b):
        raise ValueError(f"rater score lists differ in length: {len(a)} vs {len(b)}")
    n = len(a)
    k = len(categories)
    idx = {c: i for i, c in enumerate(categories)}
    span = k - 1

    obs_dis = sum(abs(idx[x] - idx[y]) / span for x, y in zip(a, b)) / n

    count_a = {c: 0 for c in categories}
    count_b = {c: 0 for c in categories}
    for x in a:
        count_a[x] += 1
    for y in b:
        count_b[y] += 1
    exp_dis = sum(
        (abs(idx[ca] - idx[cb]) / span) * count_a[ca] * count_b[cb]
        for ca in categories for cb in categories
    ) / (n * n)

    if exp_dis == 0:
        return None  # degenerate: both raters constant at the same category
    return 1 - obs_dis / exp_dis


def _linear_weight(i, j, span):
    return 1 - abs(i - j) / span


def gwet_ac1(a, b, categories=CATEGORIES):
    """Gwet's AC1 (unweighted). Chance-corrected agreement that does NOT suffer
    the kappa paradox (high observed agreement -> low coefficient when ratings
    cluster in few categories). Special case of AC2 with identity weights."""
    return gwet_ac2(a, b, categories=categories, weighted=False)


def gwet_ac2(a, b, categories=CATEGORIES, weighted=True):
    """Gwet's AC2 (linear-weighted by default). Like a weighted kappa but the
    chance-agreement term uses pi_k(1-pi_k), so it is stable when scores cluster
    in a narrow band (low variance) - the situation where Cohen's kappa collapses
    despite near-perfect rater agreement. With weighted=False this reduces to
    AC1, which we assert in tests as a correctness check."""
    if len(a) != len(b):
        raise ValueError(f"rater score lists differ in length: {len(a)} vs {len(b)}")
    n = len(a)
    k = len(categories)
    idx = {c: i for i, c in enumerate(categories)}
    span = k - 1

    if weighted:
        def w(x, y):
            return _linear_weight(idx[x], idx[y], span)
        t_w = sum(_linear_weight(i, j, span) for i in range(k) for j in range(k))
    else:
        def w(x, y):
            return 1.0 if x == y else 0.0
        t_w = float(k)  # diagonal of identity weight matrix

    p_a = sum(w(x, y) for x, y in zip(a, b)) / n

    count = {c: 0 for c in categories}
    for x in a:
        count[x] += 1
    for y in b:
        count[y] += 1
    pi = {c: count[c] / (2 * n) for c in categories}
    p_e = (t_w / (k * (k - 1))) * sum(pi[c] * (1 - pi[c]) for c in categories)

    if p_e == 1:
        return None  # undefined (cannot happen for k>1 with real data)
    return (p_a - p_e) / (1 - p_e)


def agreement_stats(a, b):
    if len(a) != len(b):
        raise ValueError(f"rater score lists differ in length: {len(a)} vs {len(b)}")
    n = len(a)
    return {
        "raw_agreement": sum(x == y for x, y in zip(a, b)) / n,
        "adjacent_agreement": sum(abs(x - y) <= 1 for x, y in zip(a, b)) / n,
        "n": n,
    }
